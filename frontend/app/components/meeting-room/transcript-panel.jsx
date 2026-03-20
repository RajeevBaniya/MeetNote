"use client";

import { useRef, useEffect } from "react";

import { Loader2, X } from "lucide-react";

import { useLeaveAndSummarize } from "@/app/lib/meeting/use-leave-and-summarize";
import { useCall } from "@stream-io/video-react-sdk";

const useEscapeKey = (onClose) => {
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape") onClose?.();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);
};

const formatTimeHHmm = (ts) => {
  if (!ts) return "";
  const d = new Date(ts);
  if (Number.isNaN(d.getTime())) return String(ts);
  return d.toLocaleTimeString("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
  });
};

const TranscriptSegment = ({ segment }) => {
  const time = formatTimeHHmm(segment.timestamp);
  return (
    <div className="py-2 border-b border-slate-700/60 last:border-b-0">
      <div className="flex items-baseline justify-between gap-2 mb-0.5">
        <span className="text-sm font-medium text-slate-200 truncate">
          {segment.speaker}
        </span>
        {time ? (
          <span className="text-xs text-slate-500 shrink-0">{time}</span>
        ) : null}
      </div>
      <p className="text-sm text-slate-300 whitespace-pre-wrap wrap-break-word">
        {segment.text || ""}
      </p>
    </div>
  );
};

const TranscriptPanel = ({
  segments = [],
  onClose,
  connected,
  connectionError,
  callId,
  hasLeftRef,
  jwt,
}) => {
  useEscapeKey(onClose);
  const scrollRef = useRef(null);
  const userScrolledRef = useRef(false);
  const prevLengthRef = useRef(0);
  const call = useCall();

  const { handleSummarizeClick, isSummarizing } = useLeaveAndSummarize(
    call,
    callId,
    () => segments,
    hasLeftRef,
  );

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    const len = segments.length;
    if (len > prevLengthRef.current) {
      if (!userScrolledRef.current) {
        el.scrollTop = el.scrollHeight;
      }
    }
    prevLengthRef.current = len;
  }, [segments.length]);

  const handleScroll = () => {
    const el = scrollRef.current;
    if (!el) return;
    const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
    userScrolledRef.current = !nearBottom;
  };

  return (
    <div className="fixed inset-0 z-50 flex items-stretch justify-end">
      <div
        className="absolute inset-0 bg-black/30 backdrop-blur-sm sm:hidden"
        onClick={onClose}
      />
      <div className="relative h-full w-full sm:w-[380px] flex flex-col bg-slate-900 border-l border-slate-700 shadow-2xl">
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-700 shrink-0">
          <h2 className="text-sm font-semibold text-slate-100 sm:text-base">
            Live Transcript
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-full text-slate-400 hover:text-slate-100 hover:bg-slate-700/50 transition-colors"
            aria-label="Close transcript"
          >
            <X className="w-5 h-5" strokeWidth={2} />
          </button>
        </div>
        {connectionError ? (
          <div className="px-4 py-3 text-sm text-amber-500 bg-amber-500/10 border-b border-slate-700">
            {connectionError}
          </div>
        ) : null}
        {!connected && !connectionError ? (
          <div className="px-4 py-3 text-sm text-slate-400">Connecting…</div>
        ) : null}
        <div
          ref={scrollRef}
          onScroll={handleScroll}
          className="flex-1 overflow-y-auto overflow-x-hidden px-4 py-2 min-h-0"
        >
          {segments.length === 0 && connected && !connectionError ? (
            <p className="text-sm text-slate-500 py-4">
              No transcript yet. Speech will appear here.
            </p>
          ) : (
            <div className="space-y-0">
              {segments.map((seg) => (
                <TranscriptSegment key={seg.id} segment={seg} />
              ))}
            </div>
          )}
        </div>
        <div className="shrink-0 border-t border-slate-700/50 px-4 py-3 bg-slate-900/90">
          <button
            type="button"
            onClick={handleSummarizeClick}
            disabled={isSummarizing}
            className="w-full inline-flex items-center justify-center gap-2 rounded-lg bg-emerald-600 py-2 px-4 text-sm font-semibold text-white ring-1 ring-emerald-500 transition hover:bg-emerald-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400 disabled:opacity-70 disabled:cursor-not-allowed"
          >
            {isSummarizing ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Leaving…</span>
              </>
            ) : (
              "Summarize Meeting"
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default TranscriptPanel;
