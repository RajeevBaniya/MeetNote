/* eslint-disable react-hooks/set-state-in-effect */
"use client";

import { useEffect, useState, useCallback, useRef, Suspense } from "react";
import { useSearchParams, useRouter, useParams } from "next/navigation";
import StreamProvider from "@/app/components/stream-provider";
import MeetingRoom from "@/app/components/meeting-room/meeting-room";
import { StreamTheme } from "@stream-io/video-react-sdk";
import { useAuth } from "@/app/lib/use-auth";
import { useStreamTokenFromBackend } from "@/app/lib/use-stream-token";
import { checkLeavingForSummarizeAndRedirect } from "@/app/lib/use-leave-and-summarize";

const REDIRECT_DELAY_MS = 2500;
const REFRESH_SAFETY_SECONDS = 300;
const REFRESH_FLOOR_SECONDS = 120;
const RETRY_DELAYS_MS = [2000, 5000, 10000];

const LOADING_MESSAGE_AUTH = "Restoring session…";
const LOADING_MESSAGE_REDIRECT = "Redirecting…";
const LOADING_MESSAGE_CHECKING_MEETING = "Checking meeting…";
const LOADING_MESSAGE_VIDEO_ACCESS = "Getting video access…";
const LOADING_MESSAGE_REDIRECT_SUMMARY = "Meeting has ended. Redirecting to summary…";

function MeetingEndedOverlay({ removedByHost, onRedirect }) {
  useEffect(() => {
    const t = setTimeout(onRedirect, REDIRECT_DELAY_MS);
    return () => clearTimeout(t);
  }, [onRedirect]);

  const message = removedByHost
    ? "You were removed by the host."
    : "This meeting has ended.";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#020617] text-slate-100">
      <p className="text-lg text-slate-300">{message}</p>
    </div>
  );
}

function LoadingScreen({ message }) {
  return (
    <div className="fixed inset-0 flex items-center justify-center bg-[#020617] text-slate-100">
      <div className="text-center">
        <div className="animate-spin rounded-full h-16 w-16 border-t-4 border-emerald-500 mx-auto" />
        <p className="mt-4 text-lg text-slate-300">{message}</p>
      </div>
    </div>
  );
}

function ErrorCard({ title, message, onBack }) {
  return (
    <div className="fixed inset-0 flex items-center justify-center bg-[#020617] text-slate-100">
      <div className="p-6 bg-red-900/20 border border-red-500 rounded-lg max-w-md">
        <p className="text-red-500 font-bold text-lg mb-2">{title}</p>
        <p className="text-slate-300">{message}</p>
        <button
          type="button"
          onClick={onBack}
          className="mt-4 px-4 py-2 bg-red-500 rounded-lg hover:bg-red-600 text-white font-medium"
        >
          Back to home
        </button>
      </div>
    </div>
  );
}

function MeetingPageContent() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user: authUser, jwt, loading: authLoading, restoringAuth, isAuthenticated } = useAuth();
  const [meetingEnded, setMeetingEnded] = useState(false);
  const [removedByHost, setRemovedByHost] = useState(false);
  const [meetingFetchStatus, setMeetingFetchStatus] = useState("loading");
  const [scheduledStartAt, setScheduledStartAt] = useState(null);
  const [meetingLoaded, setMeetingLoaded] = useState(false);

  const callId = params.id;
  const queryName = searchParams.get("name");
  const displayName =
    (queryName && queryName.trim()) ||
    (authUser && authUser.name) ||
    "Guest";

  useEffect(() => {
    if (authLoading || restoringAuth) return;
    
    if (!jwt || !isAuthenticated) {
      const currentPath = `/meeting/${callId}`;
      const queryString = searchParams.toString();
      const fullPath = queryString ? `${currentPath}?${queryString}` : currentPath;
      sessionStorage.setItem("redirectAfterAuth", fullPath);
      
      const timer = setTimeout(() => {
        router.replace("/?auth=login&reason=meeting");
      }, 800);
      
      return () => clearTimeout(timer);
    }
  }, [jwt, authLoading, restoringAuth, isAuthenticated, callId, searchParams, router]);

  const passcode = (searchParams.get("code") || "").trim() || null;

  const earlyJoinAllowed =
    !scheduledStartAt ||
    (new Date(scheduledStartAt).getTime() - Date.now()) / 1000 <= 60;

  const { token, user, error, status, expiresInSeconds } = useStreamTokenFromBackend(
    meetingLoaded ? callId : null,
    jwt,
    displayName,
    passcode,
    earlyJoinAllowed
  );

  const tokenRef = useRef(null);
  const refreshTimerRef = useRef(null);
  if (token != null) tokenRef.current = token;

  const getToken = useCallback(() => tokenRef.current, []);

  useEffect(() => {
    if (status !== "ready" || !token || typeof expiresInSeconds !== "number") return;
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    if (!apiUrl) return;

    const base = apiUrl.replace(/\/$/, "");
    const url = `${base}/meetings/${callId}/stream-token`;
    const body = {
      display_name: displayName != null ? String(displayName).trim() : "",
      passcode: passcode != null ? String(passcode).trim() : undefined,
    };
    const getHeaders = () => ({
      "Content-Type": "application/json",
      Authorization: `Bearer ${jwt}`,
    });

    let cancelled = false;
    let retryIndex = 0;

    const scheduleNext = (nextExpiresSec) => {
      if (cancelled) return;
      const delaySec = Math.max(REFRESH_FLOOR_SECONDS, nextExpiresSec - REFRESH_SAFETY_SECONDS);
      refreshTimerRef.current = setTimeout(doRefresh, delaySec * 1000);
    };

    const doRefresh = async () => {
      if (cancelled) return;
      try {
        const res = await fetch(url, {
          method: "POST",
          headers: getHeaders(),
          body: JSON.stringify(body),
        });
        if (cancelled) return;
        if (res.status === 200) {
          const data = await res.json();
          tokenRef.current = data.token;
          const next = typeof data.expires_in_seconds === "number" ? data.expires_in_seconds : 3600;
          retryIndex = 0;
          scheduleNext(next);
          return;
        }
      } catch {
        if (cancelled) return;
      }
      const delay = RETRY_DELAYS_MS[Math.min(retryIndex, RETRY_DELAYS_MS.length - 1)];
      retryIndex += 1;
      if (cancelled) return;
      refreshTimerRef.current = setTimeout(doRefresh, delay);
    };

    const delaySec = Math.max(REFRESH_FLOOR_SECONDS, expiresInSeconds - REFRESH_SAFETY_SECONDS);
    refreshTimerRef.current = setTimeout(doRefresh, delaySec * 1000);

    return () => {
      cancelled = true;
      if (refreshTimerRef.current) {
        clearTimeout(refreshTimerRef.current);
        refreshTimerRef.current = null;
      }
    };
  }, [status, token, expiresInSeconds, callId, jwt, displayName, passcode]);

  const [hostId, setHostId] = useState(null);

  useEffect(() => {
    if (!callId || !jwt) return;
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    if (!apiUrl) return;
    let cancelled = false;
    setMeetingFetchStatus("loading");
    fetch(`${apiUrl}/meetings/${callId}`, {
      headers: { Authorization: `Bearer ${jwt}` },
    })
      .then((r) => {
        if (cancelled) return null;
        if (r.status === 404) return "not_found";
        if (!r.ok) return null;
        return r.json();
      })
      .then((data) => {
        if (cancelled) return;
        if (data === "not_found") {
          setMeetingFetchStatus("not_found");
          return;
        }
        if (data === null) {
          setMeetingFetchStatus("found");
          return;
        }
        if (data.is_active === false) {
          setMeetingFetchStatus("ended");
          return;
        }
        setHostId(data.current_host_id || data.host_id);
        setScheduledStartAt(data.scheduled_start_at || null);
        setMeetingLoaded(true);
        setMeetingFetchStatus("found");
      })
      .catch(() => {
        if (!cancelled) setMeetingFetchStatus("found");
      });
    return () => { cancelled = true; };
  }, [callId, jwt]);

  useEffect(() => {
    if (meetingFetchStatus !== "ended" || !callId) return;
    const t = setTimeout(() => {
      router.replace(`/meeting/${callId}/summary?ended=1`);
    }, 1500);
    return () => clearTimeout(t);
  }, [meetingFetchStatus, callId, router]);

  const handleLeave = useCallback(() => {
    router.push("/");
  }, [router]);

  const handleSessionEnded = useCallback(async () => {
    if (checkLeavingForSummarizeAndRedirect(router, callId)) return;

    let removed = false;
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    if (apiUrl && callId && jwt) {
      try {
        const r = await fetch(`${apiUrl}/meetings/${callId}/check-removed`, {
          headers: { Authorization: `Bearer ${jwt}` },
        });
        if (r.ok) {
          const d = await r.json();
          removed = d.removed === true;
        }
      } catch {
        // ignore
      }
    }
    if (removed) {
      setRemovedByHost(true);
      setMeetingEnded(true);
    } else {
      router.replace(`/meeting/${callId}/summary`);
    }
  }, [callId, jwt, router]);

  if (authLoading || restoringAuth) {
    return (
      <LoadingScreen
        message={restoringAuth ? LOADING_MESSAGE_AUTH : "Loading…"}
      />
    );
  }

  if (!jwt || !isAuthenticated) {
    return <LoadingScreen message={LOADING_MESSAGE_REDIRECT} />;
  }

  if (meetingFetchStatus === "loading") {
    return (
      <LoadingScreen message={LOADING_MESSAGE_CHECKING_MEETING} />
    );
  }

  if (meetingFetchStatus === "not_found") {
    return (
      <ErrorCard
        title="Meeting not found"
        message="This meeting does not exist or the link is incorrect."
        onBack={() => router.push("/")}
      />
    );
  }

  if (meetingFetchStatus === "ended") {
    return (
      <LoadingScreen message={LOADING_MESSAGE_REDIRECT_SUMMARY} />
    );
  }

  const scheduledFuture =
    scheduledStartAt &&
    (new Date(scheduledStartAt).getTime() - Date.now()) / 1000 > 60;

  if (scheduledFuture) {
    const localTime = new Date(scheduledStartAt).toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
    return (
      <ErrorCard
        title="Meeting not started yet"
        message={`This meeting is scheduled for ${localTime}. You can join when it starts.`}
        onBack={() => router.push("/")}
      />
    );
  }

  if (status === "scheduled") {
    const message = error || "This meeting is scheduled and has not started yet.";
    return (
      <ErrorCard
        title="Meeting not started yet"
        message={message}
        onBack={() => router.push("/")}
      />
    );
  }

  if (status === "host_not_started") {
    const message =
      error ||
      "This meeting has not been started by the host yet. Please wait for the host to join and try again.";
    return (
      <ErrorCard
        title="Waiting for host"
        message={message}
        onBack={() => router.push("/")}
      />
    );
  }

  if (error && status === "error") {
    const text = typeof error === "string" ? error : String(error);
    const lower = text.toLowerCase();
    const isNotFound = lower.includes("not found") || lower.includes("404");
    const isRemoved = lower.includes("removed");
    const isInactive = lower.includes("inactive") || lower.includes("ended");
    const isPasscodeRequired = lower.includes("passcode required");
    const isPasscodeIncorrect = lower.includes("incorrect passcode");

    if (isNotFound) {
      return (
        <ErrorCard
          title="Meeting not found"
          message="This meeting does not exist or the link is incorrect."
          onBack={() => router.push("/")}
        />
      );
    }

    if (isInactive) {
      router.replace(`/meeting/${callId}/summary?ended=1`);
      return (
        <LoadingScreen message={LOADING_MESSAGE_REDIRECT_SUMMARY} />
      );
    }

    let title = "Error";
    let message = text;
    if (isRemoved) {
      title = "Removed from meeting";
      message = "You were removed from this meeting.";
    } else if (isPasscodeRequired) {
      title = "Passcode required";
      message = "A passcode is required to join this meeting.";
    } else if (isPasscodeIncorrect) {
      title = "Incorrect passcode";
      message = "The passcode you entered is incorrect.";
    }

    return (
      <ErrorCard
        title={title}
        message={message}
        onBack={() => router.push("/")}
      />
    );
  }

  if (status !== "ready" || !token || !user) {
    return (
      <LoadingScreen message={LOADING_MESSAGE_VIDEO_ACCESS} />
    );
  }

  return (
    <>
      {meetingEnded ? (
        <MeetingEndedOverlay removedByHost={removedByHost} onRedirect={handleLeave} />
      ) : null}
      <StreamProvider user={user} getToken={getToken}>
        <StreamTheme>
          <MeetingRoom
            callId={callId}
            onLeave={handleLeave}
            onSessionEnded={handleSessionEnded}
            userId={user.id}
            hostId={hostId}
            jwt={jwt}
          />
        </StreamTheme>
      </StreamProvider>
    </>
  );
}

function MeetingPage() {
  return (
    <Suspense
      fallback={
        <div className="fixed inset-0 flex items-center justify-center bg-[#020617] text-slate-100">
          <div className="animate-spin rounded-full h-16 w-16 border-t-4 border-emerald-500" />
        </div>
      }
    >
      <MeetingPageContent />
    </Suspense>
  );
}

export default MeetingPage;
