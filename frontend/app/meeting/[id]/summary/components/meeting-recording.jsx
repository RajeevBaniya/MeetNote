"use client";

import { useEffect, useState } from "react";
import { Video, Loader2 } from "lucide-react";

const MeetingRecording = ({ meetingId, jwt }) => {
  const [recordings, setRecordings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!meetingId || !jwt) return;
    let cancelled = false;
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    if (!apiUrl) return;

    setLoading(true);
    setError(null);
    fetch(`${apiUrl}/meetings/${meetingId}/recordings`, {
      headers: { Authorization: `Bearer ${jwt}` },
    })
      .then((r) => (r.ok ? r.json() : { recordings: [] }))
      .then((data) => {
        if (cancelled) return;
        if (data && Array.isArray(data.recordings)) {
          setRecordings(data.recordings);
        }
      })
      .catch((err) => {
        if (!cancelled) setError("Failed to load recordings");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [meetingId, jwt]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-10">
        <Loader2 className="w-6 h-6 animate-spin text-emerald-500" />
        <p className="mt-2 text-sm text-slate-400">Loading recordings…</p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-slate-700/60 bg-slate-800/40 px-5 py-5">
      <h2 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
        <Video className="w-3.5 h-3.5" />
        <span>Recording</span>
      </h2>
      <p className="mb-3 text-sm text-slate-300">Play or download the meeting recording</p>
      
      {recordings.length === 0 ? (
        <p className="text-slate-500 text-sm">
          No recordings saved for this meeting.
        </p>
      ) : (
        <div className="space-y-2">
          <p className="text-slate-400 text-xs">
            Recordings are saved on the device that recorded them.
          </p>
          <ul className="space-y-1.5">
            {recordings.map((r) => {
              const name = r?.file_name ? String(r.file_name) : "Recording";
              const duration =
                typeof r?.duration_seconds === "number"
                  ? `${Math.max(0, r.duration_seconds)}s`
                  : "";
              const started = r?.started_at ? String(r.started_at) : "";
              return (
                <li
                  key={r?.id || `${name}-${started}`}
                  className="rounded-lg border border-slate-700/60 bg-slate-900/30 px-3 py-2 text-sm text-slate-200"
                >
                  <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                    <span className="font-medium text-white">{name}</span>
                    {duration ? <span className="text-slate-400">{duration}</span> : null}
                  </div>
                  {started ? (
                    <div className="mt-1 text-xs text-slate-500">Started: {started}</div>
                  ) : null}
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
};

export default MeetingRecording;
