/* eslint-disable react-hooks/set-state-in-effect */
"use client";

import { useEffect, useState, useCallback } from "react";
import { useSearchParams, useRouter, useParams } from "next/navigation";
import StreamProvider from "@/app/components/stream-provider";
import MeetingRoom from "@/app/components/meeting-room/meeting-room";
import { StreamTheme } from "@stream-io/video-react-sdk";
import { useAuth } from "@/app/hooks/use-auth";
import { useStreamTokenFromBackend } from "@/app/hooks/use-stream-token";

const REDIRECT_DELAY_MS = 2500;

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

const MeetingPage = () => {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user: authUser, jwt, loading: authLoading, restoringAuth, isAuthenticated } = useAuth();
  const [meetingEnded, setMeetingEnded] = useState(false);
  const [removedByHost, setRemovedByHost] = useState(false);

  const callId = params.id;
  const queryName = searchParams.get("name");
  const displayName =
    (queryName && queryName.trim()) ||
    (authUser && (authUser.name || authUser.email || authUser.id)) ||
    "anonymous";

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

  const { token, user, error, status } = useStreamTokenFromBackend(
    callId,
    jwt,
    displayName
  );

  const handleLeave = useCallback(() => {
    router.push("/");
  }, [router]);

  const handleSessionEnded = useCallback(async () => {
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
    setRemovedByHost(removed);
    setMeetingEnded(true);
  }, [callId, jwt]);

  if (authLoading || restoringAuth) {
    return (
      <div className="fixed inset-0 flex items-center justify-center bg-[#020617] text-slate-100">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-t-4 border-emerald-500 mx-auto" />
          <p className="mt-4 text-lg text-slate-300">
            {restoringAuth ? "Restoring session…" : "Loading…"}
          </p>
        </div>
      </div>
    );
  }

  if (!jwt || !isAuthenticated) {
    return (
      <div className="fixed inset-0 flex items-center justify-center bg-[#020617] text-slate-100">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-t-4 border-emerald-500 mx-auto" />
          <p className="mt-4 text-lg text-slate-300">Redirecting…</p>
        </div>
      </div>
    );
  }

  if (error && status === "error") {
    return (
      <div className="fixed inset-0 flex items-center justify-center bg-[#020617] text-slate-100">
        <div className="p-6 bg-red-900/20 border border-red-500 rounded-lg">
          <p className="text-red-500 font-bold text-lg mb-2">Error</p>
          <p>{error}</p>
          <button
            onClick={() => router.push("/")}
            className="mt-4 px-4 py-2 bg-red-500 rounded-lg hover:bg-red-600"
          >
            Back
          </button>
        </div>
      </div>
    );
  }

  if (status === "waiting_approval") {
    return (
      <div className="fixed inset-0 flex items-center justify-center bg-[#020617] text-slate-100">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-t-4 border-b-4 border-amber-500 mx-auto" />
          <p className="mt-4 text-lg text-slate-300">
            Waiting for host approval
          </p>
          <p className="mt-2 text-sm text-slate-500">
            Retrying in a few seconds…
          </p>
        </div>
      </div>
    );
  }

  if (status !== "ready" || !token || !user) {
    return (
      <div className="fixed inset-0 flex items-center justify-center bg-[#020617] text-slate-100">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-t-4 border-emerald-500 mx-auto" />
          <p className="mt-4 text-lg text-slate-300">Connecting to meeting…</p>
        </div>
      </div>
    );
  }

  return (
    <>
      {meetingEnded ? (
        <MeetingEndedOverlay removedByHost={removedByHost} onRedirect={handleLeave} />
      ) : null}
      <StreamProvider user={user} token={token}>
        <StreamTheme>
          <MeetingRoom
            callId={callId}
            onLeave={handleLeave}
            onSessionEnded={handleSessionEnded}
            userId={user.id}
            jwt={jwt}
          />
        </StreamTheme>
      </StreamProvider>
    </>
  );
};

export default MeetingPage;
