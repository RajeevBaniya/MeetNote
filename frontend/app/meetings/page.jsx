"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/app/lib/auth/use-auth";
import { buildShareMessage, copyMeetingShare } from "@/app/lib/meeting/share-utils";
import Navbar from "@/app/components/landing/navbar";
import MeetingsSection from "@/app/components/meetings-section";
import ShareMeetingModal from "@/app/components/meeting-room/modals/share-meeting-modal";

const MeetingCard = ({
  meeting,
  actionLabel,
  actionHref,
  isActive,
  onShare,
  onCopy,
  isCopied,
}) => {
  const timestamp = meeting.scheduled_start_at || meeting.created_at;
  const created = timestamp
    ? new Date(timestamp).toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      })
    : "";

  const handleShare = useCallback(() => {
    onShare?.(meeting.id);
  }, [meeting.id, onShare]);

  const handleCopy = useCallback(() => {
    onCopy?.(meeting.id);
  }, [meeting.id, onCopy]);

  return (
    <div
      className={`group flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 rounded-xl border px-4 py-4 sm:px-5 sm:py-4 transition ${
        isActive
          ? "border-emerald-500/30 bg-slate-800/60 hover:border-emerald-500/50"
          : "border-slate-700/60 bg-slate-800/40 hover:border-slate-600"
      }`}
    >
      <div className="min-w-0 flex-1">
        <p className="truncate font-medium text-slate-100">
          {meeting.title || "Untitled meeting"}
        </p>
        {created ? (
          <p className="mt-0.5 text-xs text-slate-500">{created}</p>
        ) : null}
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <Link
          href={actionHref}
          className={`inline-flex shrink-0 items-center justify-center rounded-lg px-4 py-2.5 text-sm font-semibold transition focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400 focus-visible:ring-offset-2 focus-visible:ring-offset-[#020617] ${
            isActive
              ? "bg-emerald-600 text-white hover:bg-emerald-500"
              : "bg-slate-600 text-slate-100 hover:bg-slate-500"
          }`}
        >
          {actionLabel}
        </Link>
        {onShare ? (
          <button
            type="button"
            onClick={handleShare}
            className="inline-flex shrink-0 items-center justify-center rounded-lg px-4 py-2.5 text-sm font-semibold bg-slate-600 text-slate-100 hover:bg-slate-500 transition"
          >
            Share
          </button>
        ) : null}
        {onCopy ? (
          <button
            type="button"
            onClick={handleCopy}
            className="inline-flex shrink-0 items-center justify-center rounded-lg px-4 py-2.5 text-sm font-semibold bg-slate-600 text-slate-100 hover:bg-slate-500 transition"
          >
            {isCopied ? "Copied to clipboard" : "Copy"}
          </button>
        ) : null}
      </div>
    </div>
  );
};

const EmptySection = ({ message, ctaLabel, ctaHref }) => {
  return (
    <div className="rounded-xl border border-slate-700/50 border-dashed bg-slate-800/30 px-5 py-8 text-center">
      <p className="text-sm text-slate-500">{message}</p>
      {ctaLabel && ctaHref ? (
        <Link
          href={ctaHref}
          className="mt-3 inline-block rounded-lg bg-emerald-600/80 px-4 py-2 text-sm font-medium text-white transition hover:bg-emerald-500"
        >
          {ctaLabel}
        </Link>
      ) : null}
    </div>
  );
};

const MyMeetingsPage = () => {
  const {
    jwt,
    loading: authLoading,
    restoringAuth,
    isAuthenticated,
  } = useAuth();
  const router = useRouter();
  const apiUrl = process.env.NEXT_PUBLIC_API_URL;
  const [loading, setLoading] = useState(() => Boolean(apiUrl));
  const [error, setError] = useState(() =>
    apiUrl ? null : "NEXT_PUBLIC_API_URL not set",
  );
  const [upcomingMeetings, setUpcomingMeetings] = useState([]);
  const [activeMeetings, setActiveMeetings] = useState([]);
  const [endedMeetings, setEndedMeetings] = useState([]);
  const [shareModalMeetingId, setShareModalMeetingId] = useState(null);
  const [lastCopiedId, setLastCopiedId] = useState(null);

  const openAuth = (mode) => {
    router.push(`/?auth=${mode}`);
  };

  useEffect(() => {
    if (authLoading || restoringAuth) return;
    if (!jwt || !isAuthenticated) {
      sessionStorage.setItem("redirectAfterAuth", "/meetings");
      router.replace("/?auth=login&reason=meetings");
    }
  }, [jwt, authLoading, restoringAuth, isAuthenticated, router]);

  useEffect(() => {
    if (!jwt || !isAuthenticated) return;
    if (!apiUrl) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetch(`${apiUrl}/meetings/mine`, {
      headers: { Authorization: `Bearer ${jwt}` },
    })
      .then((r) => {
        if (!r.ok) {
          return r.text().then((text) => {
            throw new Error(text || `Request failed (${r.status})`);
          });
        }
        return r.json();
      })
      .then((data) => {
        if (cancelled || !data) return;
        setUpcomingMeetings(Array.isArray(data.upcoming) ? data.upcoming : []);
        setActiveMeetings(Array.isArray(data.active) ? data.active : []);
        setEndedMeetings(Array.isArray(data.ended) ? data.ended : []);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || "Failed to load meetings");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [jwt, isAuthenticated, apiUrl]);

  const excludeFromMineIds = useMemo(() => {
    const ids = [];
    for (const m of upcomingMeetings) ids.push(String(m.id));
    for (const m of activeMeetings) ids.push(String(m.id));
    for (const m of endedMeetings) ids.push(String(m.id));
    return ids;
  }, [upcomingMeetings, activeMeetings, endedMeetings]);

  const handleShareMeeting = useCallback((meetingId) => {
    setShareModalMeetingId(meetingId);
  }, []);

  const handleCopyMeeting = useCallback(
    async (meetingId) => {
      if (!apiUrl || !jwt) return;
      const base = apiUrl.replace(/\/$/, "");
      try {
        const res = await fetch(`${base}/meetings/${meetingId}/share`, {
          headers: { Authorization: `Bearer ${jwt}` },
        });
        if (!res.ok) return;
        const data = await res.json();
        const text = buildShareMessage(data);
        await copyMeetingShare(text);
        setLastCopiedId(meetingId);
        setTimeout(() =>         setLastCopiedId(null), 2000);
      } catch (_) {}
    },
    [apiUrl, jwt],
  );

  const pageBackground = (
    <>
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(16,185,129,0.25),transparent_55%)]" />
    </>
  );

  if (authLoading || restoringAuth) {
    return (
      <div className="fixed inset-0 flex flex-col bg-[#0f1419] text-slate-100">
        {pageBackground}
        <Navbar onOpenAuth={openAuth} />
        <div className="relative flex flex-1 items-center justify-center">
          <div className="text-center">
            <div className="mx-auto h-14 w-14 animate-spin rounded-full border-2 border-slate-600 border-t-emerald-500" />
            <p className="mt-4 text-slate-400">Loading…</p>
          </div>
        </div>
      </div>
    );
  }

  if (!jwt || !isAuthenticated) {
    return (
      <div className="fixed inset-0 flex flex-col bg-[#0f1419] text-slate-100">
        {pageBackground}
        <Navbar onOpenAuth={openAuth} />
        <div className="relative flex flex-1 items-center justify-center">
          <div className="text-center">
            <div className="mx-auto h-14 w-14 animate-spin rounded-full border-2 border-slate-600 border-t-emerald-500" />
            <p className="mt-4 text-slate-400">Redirecting…</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="relative min-h-screen bg-[#0f1419] text-slate-100">
      {pageBackground}
      <Navbar onOpenAuth={openAuth} />
      {shareModalMeetingId && jwt ? (
        <ShareMeetingModal
          meetingId={shareModalMeetingId}
          jwt={jwt}
          onClose={() => setShareModalMeetingId(null)}
        />
      ) : null}

      <main className="relative mx-auto w-full max-w-3xl px-4 py-8 sm:px-6 sm:py-10 lg:px-8">
        <div className="mb-8">
          <h1 className="text-2xl font-semibold tracking-tight text-white sm:text-3xl">
            My meetings
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            Join active meetings or open summaries from past ones.
          </p>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="text-center">
              <div className="mx-auto h-12 w-12 animate-spin rounded-full border-2 border-slate-600 border-t-emerald-500" />
              <p className="mt-4 text-sm text-slate-500">
                Loading your meetings…
              </p>
            </div>
          </div>
        ) : error ? (
          <div className="rounded-xl border border-red-500/40 bg-red-900/20 px-4 py-4 text-sm text-red-200">
            {error}
          </div>
        ) : (
          <div className="space-y-10">
            <section>
              <h2 className="mb-1 text-xs font-medium uppercase tracking-wider text-slate-500">
                Upcoming
              </h2>
              <p className="mb-4 text-lg font-medium text-slate-100">
                Meetings scheduled for later
              </p>
              {upcomingMeetings.length === 0 ? (
                <EmptySection message="You don’t have any upcoming meetings." />
              ) : (
                <ul className="space-y-3">
                  {upcomingMeetings.map((meeting) => {
                    const scheduled = meeting.scheduled_start_at
                      ? new Date(meeting.scheduled_start_at).toLocaleString(
                          undefined,
                          {
                            month: "short",
                            day: "numeric",
                            year: "numeric",
                            hour: "2-digit",
                            minute: "2-digit",
                          },
                        )
                      : "";
                    const base = apiUrl ? apiUrl.replace(/\/$/, "") : "";
                    const icsHref = base
                      ? `${base}/meetings/${meeting.id}/ics`
                      : null;
                    return (
                      <li key={meeting.id}>
                        <div className="group flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 rounded-xl border px-4 py-4 sm:px-5 sm:py-4 border-slate-700/60 bg-slate-800/40 hover:border-slate-600">
                          <div className="min-w-0 flex-1">
                            <p className="truncate font-medium text-slate-100">
                              {meeting.title || "Untitled meeting"}
                            </p>
                            {scheduled ? (
                              <p className="mt-0.5 text-xs text-slate-500">
                                Scheduled for {scheduled}
                              </p>
                            ) : null}
                          </div>
                          <div className="flex flex-wrap items-center gap-2">
                            <Link
                              href={`/meeting/${meeting.id}`}
                              className="inline-flex shrink-0 items-center justify-center rounded-lg px-4 py-2.5 text-sm font-semibold bg-emerald-600 text-white hover:bg-emerald-500 transition"
                            >
                              Join
                            </Link>
                            <button
                              type="button"
                              onClick={() => handleShareMeeting(meeting.id)}
                              className="inline-flex shrink-0 items-center justify-center rounded-lg px-4 py-2.5 text-sm font-semibold bg-slate-600 text-slate-100 hover:bg-slate-500 transition"
                            >
                              Share
                            </button>
                            <button
                              type="button"
                              onClick={() => handleCopyMeeting(meeting.id)}
                              className="inline-flex shrink-0 items-center justify-center rounded-lg px-4 py-2.5 text-sm font-semibold bg-slate-600 text-slate-100 hover:bg-slate-500 transition"
                            >
                              {lastCopiedId === meeting.id
                                ? "Copied to clipboard"
                                : "Copy"}
                            </button>
                            {icsHref ? (
                              <a
                                href={icsHref}
                                className="inline-flex shrink-0 items-center justify-center rounded-lg px-4 py-2.5 text-sm font-semibold bg-slate-600 text-slate-100 hover:bg-slate-500"
                              >
                                Download ICS
                              </a>
                            ) : null}
                          </div>
                        </div>
                      </li>
                    );
                  })}
                </ul>
              )}
            </section>

            <section>
              <h2 className="mb-1 text-xs font-medium uppercase tracking-wider text-slate-500">
                Active
              </h2>
              <p className="mb-4 text-lg font-medium text-slate-100">
                Meetings you can join now
              </p>
              {activeMeetings.length === 0 ? (
                <EmptySection
                  message="You don’t have any active meetings right now."
                  ctaLabel="Host a meeting"
                  ctaHref="/meeting/join?mode=host"
                />
              ) : (
                <ul className="space-y-3">
                  {activeMeetings.map((meeting) => (
                    <li key={meeting.id}>
                      <MeetingCard
                        meeting={meeting}
                        actionLabel="Join"
                        actionHref={`/meeting/${meeting.id}`}
                        isActive={true}
                      />
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section>
              <h2 className="mb-1 text-xs font-medium uppercase tracking-wider text-slate-500">
                Ended
              </h2>
              <p className="mb-4 text-lg font-medium text-slate-100">
                Past meetings and summaries
              </p>
              {endedMeetings.length === 0 ? (
                <EmptySection message="No ended meetings yet. Summaries will appear here after you end a meeting." />
              ) : (
                <ul className="space-y-3">
                  {endedMeetings.map((meeting) => (
                    <li key={meeting.id}>
                      <MeetingCard
                        meeting={meeting}
                        actionLabel="View summary"
                        actionHref={`/summarize?meetingId=${encodeURIComponent(meeting.id)}`}
                        isActive={false}
                      />
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <MeetingsSection
              jwt={jwt}
              apiUrl={apiUrl}
              excludeMeetingIds={excludeFromMineIds}
              onShareMeeting={handleShareMeeting}
              onCopyMeeting={handleCopyMeeting}
              lastCopiedId={lastCopiedId}
            />
          </div>
        )}
      </main>
    </div>
  );
};

export default MyMeetingsPage;
