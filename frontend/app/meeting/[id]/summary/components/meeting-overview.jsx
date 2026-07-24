"use client";

import { useEffect, useState } from "react";
import { Clock, Calendar, FileText, ShieldAlert } from "lucide-react";

const formatDuration = (seconds) => {
  if (typeof seconds !== "number" || !Number.isFinite(seconds) || seconds < 0) {
    return "Unknown";
  }
  if (seconds < 60) {
    return `${seconds}s`;
  }
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  if (minutes < 60) {
    return remainingSeconds > 0 ? `${minutes}m ${remainingSeconds}s` : `${minutes}m`;
  }
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  if (remainingMinutes === 0 && remainingSeconds === 0) {
    return `${hours}h`;
  }
  if (remainingSeconds === 0) {
    return `${hours}h ${remainingMinutes}m`;
  }
  return `${hours}h ${remainingMinutes}m ${remainingSeconds}s`;
};

const TranscriptSection = ({ segments }) => {
  if (!Array.isArray(segments) || segments.length === 0) {
    return <p className="text-slate-500 text-sm">No transcript available.</p>;
  }

  return (
    <div className="max-h-96 space-y-3 overflow-y-auto pr-2 custom-scrollbar mt-3">
      {segments.map((seg, index) => {
        const time = seg.start_time || "";
        const speaker = seg.speaker_id || seg.speaker || "Speaker";
        return (
          <div key={`${time}-${index}`} className="text-sm text-slate-200 border-l-2 border-emerald-500/30 pl-3 py-0.5">
            <div className="flex items-center gap-2 mb-1">
              <span className="font-semibold text-emerald-400 text-xs">{speaker}</span>
              {time ? <span className="text-[10px] text-slate-500">{time}</span> : null}
            </div>
            <p className="text-slate-300 leading-relaxed">{seg.text}</p>
          </div>
        );
      })}
    </div>
  );
};

// chatStatus and chatStatusLoading are passed from the parent page.
// This component no longer fetches /chat-status independently.
const MeetingOverview = ({ meetingId, jwt, meeting, chatStatus, chatStatusLoading }) => {
  const [transcriptSegments, setTranscriptSegments] = useState([]);
  const [transcriptLoaded, setTranscriptLoaded] = useState(false);

  const transcriptReady = chatStatus?.transcript_ready === true;
  const isExpired = !chatStatusLoading && (!chatStatus || !transcriptReady);

  useEffect(() => {
    if (!meetingId || !jwt) return;
    if (chatStatusLoading) return;
    if (!transcriptReady) {
      setTranscriptLoaded(true);
      return;
    }

    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    if (!apiUrl) return;

    let cancelled = false;

    fetch(`${apiUrl}/meetings/${meetingId}/transcript`, {
      headers: { Authorization: `Bearer ${jwt}` },
    })
      .then((r) => (r.ok ? r.json() : { segments: [] }))
      .then((data) => {
        if (cancelled) return;
        if (data && Array.isArray(data.segments) && data.segments.length > 0) {
          setTranscriptSegments(data.segments);
        }
        setTranscriptLoaded(true);
      })
      .catch(() => {
        if (!cancelled) setTranscriptLoaded(true);
      });

    return () => {
      cancelled = true;
    };
  }, [meetingId, jwt, chatStatusLoading, transcriptReady]);

  const title = meeting?.title ? String(meeting.title).trim() : "Untitled Meeting";
  const createdDate = meeting?.created_at
    ? new Date(meeting.created_at).toLocaleDateString(undefined, {
        weekday: "long",
        year: "numeric",
        month: "long",
        day: "numeric",
      })
    : "";

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-slate-700/60 bg-slate-800/40 px-5 py-5">
        <h2 className="mb-4 text-xs font-semibold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
          <Calendar className="w-3.5 h-3.5" />
          <span>General Information</span>
        </h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <p className="text-xs text-slate-500">Meeting Title</p>
            <p className="mt-1 text-sm font-semibold text-slate-100">{title}</p>
          </div>
          <div>
            <p className="text-xs text-slate-500">Date & Time</p>
            <p className="mt-1 text-sm font-semibold text-slate-100">{createdDate || "Unknown"}</p>
          </div>
        </div>
      </div>

      <div className="rounded-xl border border-slate-700/60 bg-slate-800/40 px-5 py-5">
        <h2 className="mb-4 text-xs font-semibold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
          <FileText className="w-3.5 h-3.5" />
          <span>Transcript</span>
        </h2>

        {chatStatusLoading || !transcriptLoaded ? (
          <p className="text-sm text-slate-400">Loading transcript status…</p>
        ) : isExpired ? (
          <div className="flex items-start gap-3 rounded-lg border border-amber-500/40 bg-amber-950/20 px-4 py-3.5 text-sm text-amber-200">
            <ShieldAlert className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-amber-300">Transcript Expired</p>
              <p className="mt-0.5 text-xs text-slate-400">
                The raw transcript has been deleted after the 7-day retention period. AI Chat is still available using summary-based knowledge.
              </p>
            </div>
          </div>
        ) : (
          <div>
            <p className="text-xs text-slate-400 mb-2">
              Showing raw transcript lines. Note: this transcript will be deleted 7 days after the meeting.
            </p>
            <TranscriptSection segments={transcriptSegments} />
          </div>
        )}
      </div>
    </div>
  );
};

export default MeetingOverview;
