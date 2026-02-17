"use client";

import { useEffect, useState, Suspense } from "react";
import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/app/lib/use-auth";
import Navbar from "@/app/components/landing/navbar";
import MeetingInsights from "../meeting-insights";

function RecordingSection({ recordings }) {
  const first = Array.isArray(recordings) && recordings.length > 0 ? recordings[0] : null;
  const hasUrl = first && typeof first.url === "string" && first.url.trim() !== "";

  if (!hasUrl) {
    return <p className="text-slate-500 text-sm">Recording will be available soon.</p>;
  }

  return (
    <div className="flex flex-wrap gap-3">
      <a
        href={first.url}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-emerald-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400 focus-visible:ring-offset-2 focus-visible:ring-offset-[#0f1419]"
      >
        <span>Play recording</span>
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="h-4 w-4">
          <path strokeLinecap="round" strokeLinejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.348a1.125 1.125 0 010 1.971l-11.54 6.347a1.125 1.125 0 01-1.667-.985V5.653z" />
        </svg>
      </a>
      <a
        href={first.url}
        download={first.filename || "recording.mp4"}
        className="inline-flex items-center gap-2 rounded-lg bg-slate-600 px-4 py-2.5 text-sm font-semibold text-slate-100 transition hover:bg-slate-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400 focus-visible:ring-offset-2 focus-visible:ring-offset-[#0f1419]"
      >
        <span>Download</span>
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="h-4 w-4">
          <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
        </svg>
      </a>
    </div>
  );
}

function TranscriptSection({ segments }) {
  if (!Array.isArray(segments) || segments.length === 0) {
    return <p className="text-slate-500 text-sm">No transcript available.</p>;
  }

  return (
    <div className="max-h-64 space-y-2 overflow-y-auto pr-1 custom-scrollbar">
      {segments.map((seg, index) => {
        const time = seg.start_time || "";
        const speaker = seg.speaker_id || "";
        return (
          <div key={`${time}-${index}`} className="text-sm text-slate-200">
            <span className="mr-2 text-xs text-slate-500">{time}</span>
            {speaker ? (
              <span className="mr-2 text-xs text-emerald-400">{speaker}:</span>
            ) : null}
            <span className="text-slate-200">{seg.text}</span>
          </div>
        );
      })}
    </div>
  );
}

const pageBackground = (
  <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(16,185,129,0.25),transparent_55%)]" />
);

const ENDED_BANNER_MESSAGE = "This meeting has ended. You were redirected here from the call.";

function SummaryContent({ meeting, recordings, transcriptSegments, onBack, onOpenAuth, showEndedBanner, jwt }) {
  const title = meeting?.title ? String(meeting.title).trim() : "Meeting";

  return (
    <div className="relative min-h-screen bg-[#0f1419] text-slate-100">
      {pageBackground}
      <Navbar onOpenAuth={onOpenAuth} />

      {showEndedBanner ? (
        <div className="relative mx-auto w-full max-w-3xl px-4 pt-6 sm:px-6 lg:px-8">
          <div className="rounded-lg border border-amber-500/50 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
            {ENDED_BANNER_MESSAGE}
          </div>
        </div>
      ) : null}

      <main className="relative mx-auto w-full max-w-3xl px-4 py-8 sm:px-6 sm:py-10 lg:px-8">
        <div className="mb-8">
          <h1 className="text-2xl font-semibold tracking-tight text-white sm:text-3xl">
            Meeting ended
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            {title}
          </p>
        </div>

        <div className="space-y-6">
          <MeetingInsights meetingId={meeting.id} jwt={jwt} meeting={meeting} />
          <section className="rounded-xl border border-slate-700/60 bg-slate-800/40 px-4 py-4 sm:px-5 sm:py-4">
            <h2 className="mb-1 text-xs font-medium uppercase tracking-wider text-slate-500">
              Recording
            </h2>
            <p className="mb-3 text-slate-100">Play or download the meeting recording</p>
            <RecordingSection recordings={recordings} />
          </section>

          <section className="rounded-xl border border-slate-700/60 bg-slate-800/40 px-4 py-4 sm:px-5 sm:py-4">
            <h2 className="mb-1 text-xs font-medium uppercase tracking-wider text-slate-500">
              Transcript
            </h2>
            <p className="mb-3 text-slate-100">Meeting transcript</p>
            <TranscriptSection segments={transcriptSegments} />
          </section>
        </div>

        <div className="mt-8 flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={onBack}
            className="inline-flex items-center justify-center rounded-lg bg-emerald-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-emerald-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400 focus-visible:ring-offset-2 focus-visible:ring-offset-[#0f1419]"
          >
            Back to home
          </button>
          <Link
            href="/meetings"
            className="inline-flex items-center justify-center rounded-lg border border-slate-600 bg-slate-800/60 px-5 py-2.5 text-sm font-semibold text-slate-100 transition hover:border-slate-500 hover:bg-slate-700/60 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400 focus-visible:ring-offset-2 focus-visible:ring-offset-[#0f1419]"
          >
            My meetings
          </Link>
        </div>
      </main>
    </div>
  );
}

function SummaryPageContent() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const { jwt, loading: authLoading, restoringAuth, isAuthenticated } = useAuth();
  const showEndedBanner = searchParams.get("ended") === "1";
  const [meeting, setMeeting] = useState(null);
  const [recordings, setRecordings] = useState([]);
  const [transcriptSegments, setTranscriptSegments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  const meetingId = params.id;

  useEffect(() => {
    if (authLoading || restoringAuth) return;
    if (!jwt || !isAuthenticated) {
      const path = `/meeting/${meetingId}/summary`;
      sessionStorage.setItem("redirectAfterAuth", path);
      router.replace("/?auth=login&reason=meeting");
      return;
    }
  }, [jwt, authLoading, restoringAuth, isAuthenticated, meetingId, router]);

  useEffect(() => {
    if (!meetingId || !jwt) return;
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    if (!apiUrl) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setNotFound(false);
    fetch(`${apiUrl}/meetings/${meetingId}`, {
      headers: { Authorization: `Bearer ${jwt}` },
    })
      .then((r) => {
        if (r.status === 404) return null;
        if (!r.ok) throw new Error(r.statusText);
        return r.json();
      })
      .then((data) => {
        if (cancelled) return;
        if (data === null) {
          setNotFound(true);
          setMeeting(null);
        } else {
          setMeeting(data);
          setNotFound(false);
        }
      })
      .catch(() => {
        if (!cancelled) setNotFound(true);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [meetingId, jwt]);

  useEffect(() => {
    if (!meetingId || !jwt || !meeting || meeting.is_active) return;
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    if (!apiUrl) return;
    let cancelled = false;
    fetch(`${apiUrl}/meetings/${meetingId}/recordings`, {
      headers: { Authorization: `Bearer ${jwt}` },
    })
      .then((r) => (r.ok ? r.json() : { recordings: [] }))
      .then((data) => {
        if (!cancelled && data && Array.isArray(data.recordings)) {
          setRecordings(data.recordings);
        }
      })
      .catch(() => {});
    fetch(`${apiUrl}/meetings/${meetingId}/transcript`, {
      headers: { Authorization: `Bearer ${jwt}` },
    })
      .then((r) => (r.ok ? r.json() : { segments: [] }))
      .then((data) => {
        if (!cancelled && data && Array.isArray(data.segments)) {
          setTranscriptSegments(data.segments);
        }
      })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [meetingId, jwt, meeting]);

  useEffect(() => {
    if (meeting?.is_active && meetingId) {
      router.replace(`/meeting/${meetingId}`);
    }
  }, [meeting?.is_active, meetingId, router]);

  const handleBack = () => {
    router.push("/");
  };

  const openAuth = (mode) => {
    router.push(`/?auth=${mode}`);
  };

  const LayoutWithNav = ({ children }) => (
    <div className="relative min-h-screen bg-[#0f1419] text-slate-100">
      {pageBackground}
      <Navbar onOpenAuth={openAuth} />
      {children}
    </div>
  );

  if (authLoading || restoringAuth) {
    return (
      <LayoutWithNav>
        <div className="relative flex flex-1 items-center justify-center py-20">
          <div className="text-center">
            <div className="mx-auto h-14 w-14 animate-spin rounded-full border-2 border-slate-600 border-t-emerald-500" />
            <p className="mt-4 text-slate-400">Loading…</p>
          </div>
        </div>
      </LayoutWithNav>
    );
  }

  if (!jwt || !isAuthenticated) {
    return (
      <LayoutWithNav>
        <div className="relative flex flex-1 items-center justify-center py-20">
          <div className="text-center">
            <div className="mx-auto h-14 w-14 animate-spin rounded-full border-2 border-slate-600 border-t-emerald-500" />
            <p className="mt-4 text-slate-400">Redirecting…</p>
          </div>
        </div>
      </LayoutWithNav>
    );
  }

  if (loading) {
    return (
      <LayoutWithNav>
        <div className="relative flex flex-1 items-center justify-center py-20">
          <div className="text-center">
            <div className="mx-auto h-12 w-12 animate-spin rounded-full border-2 border-slate-600 border-t-emerald-500" />
            <p className="mt-4 text-sm text-slate-500">Loading meeting…</p>
          </div>
        </div>
      </LayoutWithNav>
    );
  }

  if (notFound || !meeting) {
    return (
      <LayoutWithNav>
        <main className="relative mx-auto w-full max-w-3xl px-4 py-8 sm:px-6 sm:py-10 lg:px-8">
          <div className="rounded-xl border border-slate-700/50 bg-slate-800/30 px-5 py-8 text-center">
            <p className="mb-4 text-sm text-slate-400">Meeting not found.</p>
            <button
              type="button"
              onClick={handleBack}
              className="inline-flex items-center justify-center rounded-lg bg-emerald-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-emerald-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400 focus-visible:ring-offset-2 focus-visible:ring-offset-[#0f1419]"
            >
              Back to home
            </button>
          </div>
        </main>
      </LayoutWithNav>
    );
  }

  if (meeting.is_active) {
    return (
      <LayoutWithNav>
        <div className="relative flex flex-1 items-center justify-center py-20">
          <div className="text-center">
            <div className="mx-auto h-14 w-14 animate-spin rounded-full border-2 border-slate-600 border-t-emerald-500" />
            <p className="mt-4 text-slate-400">Redirecting to meeting…</p>
          </div>
        </div>
      </LayoutWithNav>
    );
  }

  return (
    <SummaryContent
      meeting={meeting}
      recordings={recordings}
      transcriptSegments={transcriptSegments}
      onBack={handleBack}
      onOpenAuth={openAuth}
      showEndedBanner={showEndedBanner}
      jwt={jwt}
    />
  );
}

function SummaryPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-[#0f1419] text-slate-100 flex items-center justify-center" />
      }
    >
      <SummaryPageContent />
    </Suspense>
  );
}

export default SummaryPage;
