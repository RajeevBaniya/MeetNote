"use client";

import { useEffect, useState } from "react";

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

const MeetingInsights = ({ meetingId, jwt, meeting }) => {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!meetingId || !jwt || !meeting || meeting.is_active) return;
    if (!meeting.host_id) return;
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    if (!apiUrl) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetch(`${apiUrl}/meetings/${meetingId}/analytics`, {
      headers: { Authorization: `Bearer ${jwt}` },
    })
      .then((res) => {
        if (res.status === 404 || res.status === 400 || res.status === 403) {
          return res.json().then((body) => {
            const detail = typeof body?.detail === "string" ? body.detail : "";
            throw new Error(detail || "Analytics not available");
          });
        }
        if (!res.ok) {
          throw new Error("Failed to load analytics");
        }
        return res.json();
      })
      .then((body) => {
        if (!cancelled) {
          setData(body);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err.message || "Analytics not available");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [meetingId, jwt, meeting]);

  if (!meeting || meeting.is_active) {
    return null;
  }

  if (loading && !data) {
    return (
      <section className="mb-6 rounded-xl border border-slate-700/60 bg-slate-800/40 px-4 py-4 sm:px-5 sm:py-4">
        <h2 className="mb-1 text-xs font-medium uppercase tracking-wider text-slate-500">
          Meeting insights
        </h2>
        <p className="text-sm text-slate-400">Loading insights…</p>
      </section>
    );
  }

  if (!data && error) {
    return null;
  }

  if (!data) {
    return null;
  }

  const durationLabel = formatDuration(data.duration_seconds);
  const recordingLabel =
    data.recording_count > 0
      ? `Yes (${data.recording_count})`
      : "No recordings";

  return (
    <section className="mb-6 rounded-xl border border-slate-700/60 bg-slate-800/40 px-4 py-4 sm:px-5 sm:py-4">
      <h2 className="mb-1 text-xs font-medium uppercase tracking-wider text-slate-500">
        Meeting insights
      </h2>
      <div className="mt-2 grid grid-cols-1 gap-3 sm:grid-cols-3">
        <div>
          <p className="text-xs text-slate-500">Duration</p>
          <p className="mt-1 text-sm font-medium text-slate-100">
            {durationLabel}
          </p>
        </div>
        <div>
          <p className="text-xs text-slate-500">Participants (chat activity)</p>
          <p className="mt-1 text-sm font-medium text-slate-100">
            {data.participants_count}
          </p>
        </div>
        <div>
          <p className="text-xs text-slate-500">Chat messages</p>
          <p className="mt-1 text-sm font-medium text-slate-100">
            {data.chat_message_count}
          </p>
        </div>
      </div>
      <div className="mt-3 border-t border-slate-700/60 pt-3">
        <p className="text-xs text-slate-500">Recordings</p>
        <p className="mt-1 text-sm font-medium text-slate-100">
          {recordingLabel}
        </p>
      </div>
    </section>
  );
};

export default MeetingInsights;

