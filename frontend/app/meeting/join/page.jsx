"use client";

import Image from "next/image";
import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/app/lib/auth/use-auth";
import { getErrorMessage, isRateLimitError } from "@/app/lib/ui/error-messages";
import ErrorBanner from "@/app/lib/ui/error-banner";
import MeetingCreatedModal from "@/app/components/meeting-room/modals/meeting-info-modal";

const JoinMeetingContent = () => {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { jwt, loading: authLoading, restoringAuth } = useAuth();

  const [username, setUsername] = useState("");
  const [meetingTitle, setMeetingTitle] = useState("");
  const [meetingDescription, setMeetingDescription] = useState("");
  const [scheduledAtLocal, setScheduledAtLocal] = useState("");
  const [meetingId, setMeetingId] = useState("");
  const [meetingPasscode, setMeetingPasscode] = useState("");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState(null);
  const [createdMeeting, setCreatedMeeting] = useState(null);
  const [bannerError, setBannerError] = useState(null);

  const mode = searchParams.get("mode") || "join";
  const isHostMode = mode === "host";

  useEffect(() => {
    if (authLoading || restoringAuth) return;
    if (!jwt) {
      if (typeof sessionStorage !== "undefined") {
        sessionStorage.setItem("redirectAfterAuth", "/meeting/join");
      }
      router.replace("/?auth=login&reason=meeting");
    }
  }, [jwt, authLoading, restoringAuth, router]);

  const formatJoinCode = (value) => {
    const digits = value.replace(/\D/g, "").slice(0, 12);
    if (digits.length <= 4) return digits;
    if (digits.length <= 8) return `${digits.slice(0, 4)} ${digits.slice(4)}`;
    return `${digits.slice(0, 4)} ${digits.slice(4, 8)} ${digits.slice(8)}`;
  };

  const handleMeetingIdChange = (event) => {
    const formatted = formatJoinCode(event.target.value);
    setMeetingId(formatted);
  };

  const handleJoin = async () => {
    const name = username.trim() === "" ? "anonymous" : username.trim();

    setBannerError(null);

    if (isHostMode) {
      setCreating(true);
      setCreateError(null);
      const apiUrl = process.env.NEXT_PUBLIC_API_URL;
      if (!apiUrl) {
        setCreateError("API URL not configured");
        setCreating(false);
        return;
      }
      const base = apiUrl.replace(/\/$/, "");
      try {
        let scheduled_start_at = null;
        if (scheduledAtLocal) {
          const localDate = new Date(scheduledAtLocal);
          if (!Number.isNaN(localDate.getTime())) {
            scheduled_start_at = localDate.toISOString();
          }
        }
        const res = await fetch(`${base}/meetings`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${jwt}`,
          },
          body: JSON.stringify({
            title: meetingTitle.trim() || null,
            scheduled_start_at,
          }),
        });
        if (res.status === 429) {
          const structuredError = {
            status: 429,
            code: "rate_limit_exceeded",
          };
          if (isRateLimitError(structuredError)) {
            setBannerError(structuredError);
          }
          setCreating(false);
          return;
        }
        const data = await res.json();
        if (!res.ok) {
          setCreateError(data.detail || "Failed to create meeting");
          setCreating(false);
          return;
        }
        const { id, join_code, passcode } = data;
        setCreatedMeeting({ id, join_code, passcode, name });
        setCreating(false);
      } catch (err) {
        setCreateError(err.message || "Failed to create meeting");
        setCreating(false);
      }
      return;
    }

    const cleanedCode = meetingId.replace(/\D/g, "");
    if (!cleanedCode || cleanedCode.length !== 12) {
      setCreateError("Please enter a valid 12-digit meeting code.");
      return;
    }
    const passcode = meetingPasscode.trim();
    if (!passcode) {
      setCreateError("Please enter the passcode.");
      return;
    }
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    if (!apiUrl) {
      setCreateError("API URL not configured");
      return;
    }
    const base = apiUrl.replace(/\/$/, "");
    try {
      const res = await fetch(`${base}/meetings/join`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${jwt}`,
        },
        body: JSON.stringify({
          join_code: cleanedCode,
          passcode: passcode,
        }),
      });
      if (res.status === 429) {
        const structuredError = {
          status: 429,
          code: "rate_limit_exceeded",
          message: "Too many join attempts. Please wait a moment.",
        };
        if (isRateLimitError(structuredError)) {
          setBannerError(structuredError);
        } else {
          setCreateError("Too many join attempts. Please wait a moment.");
        }
        return;
      }
      const data = await res.json();
      if (!res.ok) {
        const detail = Array.isArray(data.detail)
          ? data.detail[0]?.msg ?? data.detail[0]
          : data.detail;
        setCreateError(
          typeof detail === "string" ? detail : "Failed to join meeting",
        );
        return;
      }
      const search = new URLSearchParams();
      search.set("name", name);
      search.set("code", passcode);
      router.push(`/meeting/${data.meeting_id}?${search.toString()}`);
    } catch (err) {
      setCreateError(err.message || "Failed to join meeting");
    }
  };

  const handleClose = () => {
    router.push("/");
  };

  const handleJoinCreatedMeeting = () => {
    if (createdMeeting) {
      router.push(`/meeting/${createdMeeting.id}?name=${encodeURIComponent(createdMeeting.name)}`);
    }
  };

  const formTitle = isHostMode ? "Meeting details" : "Enter meeting";
  const buttonText = isHostMode ? "Create meeting" : "Join meeting";

  if (authLoading || restoringAuth) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#0f1419] text-slate-100">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-t-4 border-emerald-500 mx-auto" />
          <p className="mt-4 text-lg text-slate-300">Checking sign-in…</p>
        </div>
      </div>
    );
  }

  if (!jwt) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#0f1419] text-slate-100">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-t-4 border-emerald-500 mx-auto" />
          <p className="mt-4 text-lg text-slate-300">Redirecting to sign-in…</p>
        </div>
      </div>
    );
  }

  return (
    <>
      {createdMeeting ? (
        <MeetingCreatedModal
          meetingId={createdMeeting.id}
          joinCode={createdMeeting.join_code}
          passcode={createdMeeting.passcode}
          onJoin={handleJoinCreatedMeeting}
          onClose={() => setCreatedMeeting(null)}
          jwt={jwt}
        />
      ) : null}
      <div className="relative flex min-h-screen items-center justify-center bg-[#0f1419] px-4 sm:px-6 lg:px-10 xl:px-16 text-slate-100">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(16,185,129,0.25),transparent_55%)]" />
      <button
        type="button"
        aria-label="Go back to home"
        onClick={handleClose}
        className="absolute right-4 top-4 flex h-9 w-9 items-center justify-center rounded-full border border-slate-700 bg-slate-900/80 text-slate-300 shadow-md transition hover:border-emerald-500 hover:text-emerald-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400 sm:right-6 sm:top-6"
      >
        ×
      </button>

      <div className="flex w-full max-w-4xl lg:max-w-5xl xl:max-w-6xl items-center justify-center gap-1.5 md:gap-3 lg:gap-4 xl:gap-5">
        <div className="hidden w-1/2 md:mt-4 lg:mt-6 xl:mt-8 md:flex md:justify-end lg:justify-center">
          <Image
            src="/images/meet.png"
            alt="MeetNote meeting with participants and notes"
            width={1200}
            height={800}
            className="h-auto w-full max-w-md sm:max-w-lg lg:max-w-xl object-contain md:scale-110 lg:scale-125 xl:scale-150 md:transform "
            sizes="(max-width: 767px) 0px, (min-width: 1280px) 520px, (min-width: 1024px) 460px, 380px"
            priority
          />
        </div>

        <div className="hidden h-48 sm:h-56 md:h-60 xl:h-72 w-px rounded-full bg-emerald-500/40 md:block md:-ml-20 lg:-ml-24 xl:-ml-26" />

        <div className="w-full md:w-1/2">
          <div className="mx-auto w-full max-w-sm rounded-2xl border border-emerald-500/40 bg-slate-900/80 p-6 sm:p-8 shadow-[0_0_30px_rgba(16,185,129,0.35)] backdrop-blur-sm">
            <h2 className="mb-4 text-lg sm:text-xl font-semibold text-center text-slate-50">
              {formTitle}
            </h2>

            {bannerError ? (
              <ErrorBanner
                message={getErrorMessage(bannerError)}
                onClose={() => setBannerError(null)}
              />
            ) : null}

            <div className="space-y-4">
              <input
                className="w-full rounded-lg border border-slate-700 bg-slate-900/70 px-4 py-3 text-sm text-slate-100 placeholder-slate-500 outline-none ring-1 ring-transparent transition focus:ring-emerald-500"
                placeholder="e.g. John (optional)"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
              />

              {isHostMode ? (
                <>
                  <input
                    className="w-full rounded-lg border border-slate-700 bg-slate-900/70 px-4 py-3 text-sm text-slate-100 placeholder-slate-500 outline-none ring-1 ring-transparent transition focus:ring-emerald-500"
                    placeholder="Meeting title"
                    value={meetingTitle}
                    onChange={(event) => setMeetingTitle(event.target.value)}
                  />
                  <input
                    className="w-full rounded-lg border border-slate-700 bg-slate-900/70 px-4 py-3 text-sm text-slate-100 placeholder-slate-500 outline-none ring-1 ring-transparent transition focus:ring-emerald-500"
                    placeholder="Description (optional)"
                    value={meetingDescription}
                    onChange={(event) =>
                      setMeetingDescription(event.target.value)
                    }
                  />
                  <input
                    type="datetime-local"
                    className="w-full rounded-lg border border-slate-700 bg-slate-900/70 px-4 py-3 text-sm text-slate-100 placeholder-slate-500 outline-none ring-1 ring-transparent transition focus:ring-emerald-500"
                    value={scheduledAtLocal}
                    onChange={(event) => setScheduledAtLocal(event.target.value)}
                  />
                </>
              ) : (
                <>
                  <input
                    type="text"
                    inputMode="numeric"
                    pattern="[0-9\s]*"
                    className="w-full rounded-lg border border-slate-700 bg-slate-900/70 px-4 py-3 text-sm text-slate-100 placeholder-slate-500 outline-none ring-1 ring-transparent transition focus:ring-emerald-500 font-mono"
                    placeholder="1234 5678 9012"
                    value={meetingId}
                    onChange={handleMeetingIdChange}
                  />
                  <input
                    className="w-full rounded-lg border border-slate-700 bg-slate-900/70 px-4 py-3 text-sm text-slate-100 placeholder-slate-500 outline-none ring-1 ring-transparent transition focus:ring-emerald-500"
                    placeholder="Meeting passcode"
                    value={meetingPasscode}
                    onChange={(event) =>
                      setMeetingPasscode(event.target.value)
                    }
                  />
                </>
              )}
            </div>

            {createError ? (
              <p className="text-sm text-red-400">{createError}</p>
            ) : null}
            <button
              onClick={handleJoin}
              disabled={creating}
              className="mt-5 w-full rounded-lg bg-emerald-600 py-3 text-sm font-semibold text-slate-50 shadow-lg transition hover:bg-emerald-500 disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400"
            >
              {creating ? "Creating…" : buttonText}
            </button>
          </div>
        </div>
      </div>
    </div>
    </>
  );
};

const JoinMeetingPage = () => {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-[#0f1419] text-slate-100 flex items-center justify-center" />
      }
    >
      <JoinMeetingContent />
    </Suspense>
  );
};

export default JoinMeetingPage;
