"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiFetch } from "@/app/summarize/lib/api";

function MeetingSummariesSection({ meetingId }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!meetingId) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    const url = `/api/summaries?meetingId=${encodeURIComponent(meetingId)}`;
    apiFetch(url)
      .then((data) => {
        if (!cancelled && data?.items) {
          setItems(data.items);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err.message || "Failed to load summaries");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });
    return () => { cancelled = true; };
  }, [meetingId]);

  if (loading) {
    return (
      <section className="rounded-xl border border-slate-700/60 bg-slate-800/40 px-4 py-4 sm:px-5 sm:py-4">
        <h2 className="mb-1 text-xs font-medium uppercase tracking-wider text-slate-500">
          Summaries
        </h2>
        <p className="text-sm text-slate-400">Loading summaries…</p>
      </section>
    );
  }

  if (error) {
    return (
      <section className="rounded-xl border border-slate-700/60 bg-slate-800/40 px-4 py-4 sm:px-5 sm:py-4">
        <h2 className="mb-1 text-xs font-medium uppercase tracking-wider text-slate-500">
          Summaries
        </h2>
        <p className="text-sm text-slate-500">{error}</p>
      </section>
    );
  }

  if (!Array.isArray(items) || items.length === 0) {
    return (
      <section className="rounded-xl border border-slate-700/60 bg-slate-800/40 px-4 py-4 sm:px-5 sm:py-4">
        <h2 className="mb-1 text-xs font-medium uppercase tracking-wider text-slate-500">
          Summaries
        </h2>
        <p className="mb-3 text-slate-100">Summaries for this meeting</p>
        <p className="text-sm text-slate-500">No summaries yet.</p>
      </section>
    );
  }

  return (
    <section className="rounded-xl border border-slate-700/60 bg-slate-800/40 px-4 py-4 sm:px-5 sm:py-4">
      <h2 className="mb-1 text-xs font-medium uppercase tracking-wider text-slate-500">
        Summaries
      </h2>
      <p className="mb-3 text-slate-100">Summaries for this meeting</p>
      <ul className="space-y-3">
        {items.map((item) => (
          <li key={item.id}>
            <Link
              href={`/summarize?id=${item.id}`}
              className="block rounded-lg border border-slate-600/60 bg-slate-800/60 px-3 py-2.5 text-sm text-slate-200 transition hover:border-emerald-500/50 hover:bg-slate-700/60"
            >
              <span className="font-medium text-slate-100">
                {item.title || item.meeting_title || "Summary"}
              </span>
              {item.meeting_date ? (
                <span className="ml-2 text-xs text-slate-500">
                  {new Date(item.meeting_date).toLocaleDateString()}
                </span>
              ) : null}
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}

export default MeetingSummariesSection;
