"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Loader2, Plus, ChevronRight, FileText, ExternalLink, Calendar, CheckSquare, MessageSquare } from "lucide-react";

import { apiFetch } from "@/app/summarize/lib/api";
import ExportButton from "@/app/summarize/components/summary/export-button";
import EmailSender from "@/app/summarize/components/email/email-sender";

const MeetingSummaries = ({ meetingId, meetingTitle }) => {
  const [items, setItems] = useState([]);
  const [activeSummary, setActiveSummary] = useState(null);
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
        if (cancelled) return;
        if (data?.items) {
          const list = data.items;
          setItems(list);
          if (list.length > 0) {
            setActiveSummary(list[0]);
          }
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
    return () => {
      cancelled = true;
    };
  }, [meetingId]);

  const handleUpdateSummaryText = async (newText) => {
    if (!activeSummary) return;
    try {
      const res = await apiFetch(`/api/summaries/${activeSummary.id}`, {
        method: "PUT",
        body: JSON.stringify({
          summary: newText,
        }),
      });
      if (res?.success && res?.item) {
        setItems((prev) =>
          prev.map((item) => (item.id === activeSummary.id ? res.item : item))
        );
        setActiveSummary(res.item);
      }
    } catch (err) {
      console.error("Failed to save summary text update:", err);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <Loader2 className="w-8 h-8 animate-spin text-emerald-500" />
        <p className="mt-3 text-sm text-slate-400">Loading summaries…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-red-500/40 bg-red-900/20 px-4 py-4 text-sm text-red-200">
        {error}
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 px-6 text-center bg-slate-900/10 rounded-xl border border-slate-800">
        <FileText className="w-12 h-12 text-slate-600 mb-4" />
        <p className="text-base font-semibold text-slate-300">No Summaries Yet</p>
        <p className="mt-1 text-sm text-slate-500 max-w-sm mb-6">
          Generate an AI summary to extract action items, key decisions, and clean notes.
        </p>
        <Link
          href={`/summarize?source=live&meetingId=${meetingId}`}
          className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-emerald-500"
        >
          <Plus className="w-4 h-4" />
          <span>Generate Summary</span>
        </Link>
      </div>
    );
  }

  const structured = activeSummary
    ? {
        actionItems: activeSummary.action_items || [],
        decisions: activeSummary.decisions || [],
        deadlines: activeSummary.deadlines || [],
        participants: activeSummary.extracted_participants || [],
      }
    : null;

  return (
    <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-start">
      {/* Sidebar - Summary List switcher */}
      <div className="md:col-span-4 rounded-xl border border-slate-700/60 bg-slate-800/40 p-4 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-400">Summary Versions</h3>
          <Link
            href={`/summarize?source=live&meetingId=${meetingId}`}
            className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-400 hover:text-emerald-300"
            title="Create another summary version"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>New Version</span>
          </Link>
        </div>

        <ul className="space-y-2">
          {items.map((item) => {
            const isActive = activeSummary?.id === item.id;
            return (
              <li key={item.id}>
                <button
                  type="button"
                  onClick={() => setActiveSummary(item)}
                  className={`w-full flex items-center justify-between px-3 py-2 rounded-lg border text-left text-xs transition ${
                    isActive
                      ? "border-emerald-500/50 bg-emerald-500/10 text-emerald-300 font-medium"
                      : "border-slate-700/60 bg-slate-800/20 text-slate-300 hover:border-slate-600 hover:bg-slate-700/30"
                  }`}
                >
                  <span className="truncate">{item.title || "Summary"}</span>
                  <ChevronRight className={`w-3.5 h-3.5 ${isActive ? "text-emerald-400" : "text-slate-500"}`} />
                </button>
              </li>
            );
          })}
        </ul>
      </div>

      {/* Main Workspace content */}
      <div className="md:col-span-8 space-y-6">
        {activeSummary && (
          <>
            {/* Lightweight Summary Dashboard Card */}
            <div className="rounded-xl border border-slate-700/60 bg-slate-800/40 p-6 space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-slate-700/60">
                <div>
                  <h3 className="text-lg font-bold text-slate-100">
                    {activeSummary.title || "Meeting Summary"}
                  </h3>
                  <div className="flex items-center gap-2 mt-1.5 text-xs text-slate-400">
                    <Calendar className="w-3.5 h-3.5 text-slate-500" />
                    <span>Created: {activeSummary.created_at ? new Date(activeSummary.created_at).toLocaleDateString() + " " + new Date(activeSummary.created_at).toLocaleTimeString() : "Unknown Date"}</span>
                  </div>
                </div>

                <Link
                  href={`/summarize?id=${activeSummary.id}`}
                  className="inline-flex items-center justify-center gap-1.5 rounded-lg bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-emerald-500 shadow-sm"
                >
                  <ExternalLink className="w-4 h-4" />
                  <span>Open Workspace & Edit</span>
                </Link>
              </div>

              {/* Statistics Grid */}
              <div className="grid grid-cols-3 gap-4">
                <div className="rounded-lg bg-slate-800/20 border border-slate-700/30 p-3.5 flex items-center gap-3">
                  <div className="p-2 rounded-md bg-sky-500/10 text-sky-400">
                    <FileText className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="text-xs text-slate-500 font-medium">Word Count</div>
                    <div className="text-base font-semibold text-slate-200 mt-0.5">
                      {activeSummary.summary ? activeSummary.summary.split(/\s+/).filter(Boolean).length : 0}
                    </div>
                  </div>
                </div>

                <div className="rounded-lg bg-slate-800/20 border border-slate-700/30 p-3.5 flex items-center gap-3">
                  <div className="p-2 rounded-md bg-amber-500/10 text-amber-400">
                    <CheckSquare className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="text-xs text-slate-500 font-medium">Action Items</div>
                    <div className="text-base font-semibold text-slate-200 mt-0.5">
                      {activeSummary.action_items ? activeSummary.action_items.length : 0}
                    </div>
                  </div>
                </div>

                <div className="rounded-lg bg-slate-800/20 border border-slate-700/30 p-3.5 flex items-center gap-3">
                  <div className="p-2 rounded-md bg-purple-500/10 text-purple-400">
                    <MessageSquare className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="text-xs text-slate-500 font-medium">Decisions</div>
                    <div className="text-base font-semibold text-slate-200 mt-0.5">
                      {activeSummary.decisions ? activeSummary.decisions.length : 0}
                    </div>
                  </div>
                </div>
              </div>

              {/* Exports Actions */}
              <div className="space-y-2">
                <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Export Document</h4>
                <ExportButton summaryId={activeSummary.id} fileName={meetingTitle || activeSummary.meeting_title} />
              </div>
            </div>

            {/* Retain Email Sharing directly in Summaries tab */}
            <EmailSender summary={activeSummary.summary} />
          </>
        )}
      </div>
    </div>
  );
};

export default MeetingSummaries;
