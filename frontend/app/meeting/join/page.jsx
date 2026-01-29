"use client";

import Image from "next/image";
import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

const JoinMeetingPage = () => {
  const router = useRouter();
  const searchParams = useSearchParams();
  const mode = searchParams.get("mode") || "join";
  const isHostMode = mode === "host";

  const [username, setUsername] = useState("");
  const [meetingTitle, setMeetingTitle] = useState("");
  const [meetingDescription, setMeetingDescription] = useState("");
  const [meetingId, setMeetingId] = useState("");
  const [meetingPasscode, setMeetingPasscode] = useState("");

  const handleJoin = () => {
    const name = username.trim() === "" ? "anonymous" : username.trim();
    const defaultCallId = process.env.NEXT_PUBLIC_CALL_ID || "demo-meeting-room";
    const meetingIdValue = isHostMode
      ? defaultCallId
      : (meetingId.trim() || defaultCallId);
    router.push(`/meeting/${meetingIdValue}?name=${encodeURIComponent(name)}`);
  };

  const handleClose = () => {
    router.push("/");
  };

  const formTitle = isHostMode ? "Meeting details" : "Enter meeting";
  const buttonText = isHostMode ? "Create meeting" : "Join meeting";

  return (
    <div className="relative flex min-h-screen items-center justify-center bg-gradient-to-br from-[#020617] via-[#020617] to-[#022c22] px-4 sm:px-6 lg:px-10 xl:px-16 text-slate-100">
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
                </>
              ) : (
                <>
                  <input
                    className="w-full rounded-lg border border-slate-700 bg-slate-900/70 px-4 py-3 text-sm text-slate-100 placeholder-slate-500 outline-none ring-1 ring-transparent transition focus:ring-emerald-500"
                    placeholder="Meeting ID"
                    value={meetingId}
                    onChange={(event) => setMeetingId(event.target.value)}
                  />
                  <input
                    className="w-full rounded-lg border border-slate-700 bg-slate-900/70 px-4 py-3 text-sm text-slate-100 placeholder-slate-500 outline-none ring-1 ring-transparent transition focus:ring-emerald-500"
                    placeholder="Meeting passcode (optional)"
                    value={meetingPasscode}
                    onChange={(event) =>
                      setMeetingPasscode(event.target.value)
                    }
                  />
                </>
              )}
            </div>

            <button
              onClick={handleJoin}
              className="mt-5 w-full rounded-lg bg-emerald-600 py-3 text-sm font-semibold text-slate-50 shadow-lg transition hover:bg-emerald-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400"
            >
              {buttonText}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default JoinMeetingPage;
