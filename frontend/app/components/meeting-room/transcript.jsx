"use client";

import { useEffect, useRef } from "react";
import { useCall } from "@stream-io/video-react-sdk";
import iconsData from "@/app/components/icons/icons.json";
import { useLeaveAndSummarize } from "@/app/lib/use-leave-and-summarize";
import { useLiveTranscript } from "@/app/lib/use-live-transcript";

const TranscriptPanel = ({ callId, hasLeftRef, jwt }) => {
  const transcriptEndRef = useRef(null);
  const call = useCall();

  const { transcripts, getSnapshot } = useLiveTranscript(callId, jwt);

  const { handleSummarizeClick, isSummarizing, showEmptyInfo, setShowEmptyInfo } =
    useLeaveAndSummarize(call, callId, getSnapshot, hasLeftRef);

  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [transcripts]);

  return (
    <div className="h-full w-full flex flex-col overflow-hidden">
      <div className="shrink-0 px-2 py-2 sm:px-3 sm:py-3 md:px-4 md:py-4 border-b border-emerald-900/60 bg-gradient-to-r from-emerald-900/30 to-slate-900/60">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5 sm:gap-2">
            <div className="p-1.5 sm:p-2 bg-blue-500/10 rounded-lg">
              <span
                className="w-4 h-4 sm:w-5 sm:h-5 text-blue-500 block"
                dangerouslySetInnerHTML={{ __html: iconsData.document }}
              />
            </div>
            <div>
              <h3 className="text-xs sm:text-sm md:text-base font-bold text-white">
                Live Transcript
              </h3>
              <p className="text-[10px] sm:text-xs text-gray-400">
                {transcripts.length}{" "}
                {transcripts.length === 1 ? "message" : "messages"}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-1.5 sm:gap-2">
            <div className="w-1.5 h-1.5 sm:w-2 sm:h-2 bg-green-500 rounded-full animate-pulse" />
            <span className="text-[10px] sm:text-xs text-green-500 font-medium">
              Live
            </span>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-2 py-2 sm:px-3 sm:py-3 md:px-4 md:py-3 space-y-2 sm:space-y-3 bg-slate-900/80 custom-scrollbar">
        {transcripts.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center px-2 sm:px-3">
            <div className="relative mb-3 sm:mb-4">
              <div className="w-12 h-12 sm:w-16 sm:h-16 bg-gray-700 rounded-full flex items-center justify-center">
                <span
                  className="w-6 h-6 sm:w-8 sm:h-8 text-gray-500 block"
                  dangerouslySetInnerHTML={{ __html: iconsData.microphone }}
                />
              </div>
              <div className="absolute -bottom-1 -right-1 w-4 h-4 sm:w-5 sm:h-5 bg-blue-500 rounded-full flex items-center justify-center">
                <span
                  className="w-2.5 h-2.5 sm:w-3 sm:h-3 text-white block"
                  dangerouslySetInnerHTML={{ __html: iconsData.plus }}
                />
              </div>
            </div>
            <p className="text-gray-300 text-sm sm:text-base font-semibold mb-1.5 sm:mb-2">
              Waiting for transcripts...
            </p>
            <p className="text-gray-500 text-xs sm:text-sm">
              Start speaking to see live transcription appear here.
            </p>
          </div>
        ) : (
          <>
            {transcripts.map((transcript) => (
              <div
                key={transcript.id}
                className="group rounded-lg border border-emerald-900/60 bg-slate-900/80 p-2 sm:p-3 shadow-lg transition-all duration-200 hover:border-emerald-400/70 hover:shadow-emerald-900/40"
              >
                <div className="flex items-start gap-1.5 sm:gap-2 mb-1.5 sm:mb-2">
                  <div className="flex h-7 w-7 sm:h-8 sm:w-8 shrink-0 items-center justify-center rounded-full bg-emerald-500/15 text-emerald-300 text-[10px] sm:text-xs font-bold ring-1 ring-emerald-400/40">
                    {transcript.speaker.charAt(0).toUpperCase()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-baseline justify-between gap-1.5 sm:gap-2">
                      <span className="font-semibold text-blue-400 text-xs sm:text-sm truncate">
                        {transcript.speaker}
                      </span>
                      <span className="text-[10px] sm:text-xs text-gray-400 font-mono shrink-0">
                        {transcript.timestamp}
                      </span>
                    </div>
                    <p className="text-gray-100 leading-relaxed text-xs sm:text-sm mt-0.5 sm:mt-1">
                      {transcript.text}
                    </p>
                  </div>
                </div>
              </div>
            ))}
            <div ref={transcriptEndRef} />
          </>
        )}
      </div>

      <div className="shrink-0 border-t border-slate-700/50 px-3 py-3 bg-slate-900/90">
        {showEmptyInfo ? (
          <div className="mb-2 rounded-md bg-slate-800/80 px-3 py-2 text-[11px] sm:text-xs text-emerald-100">
            Live summarization will be available soon.
          </div>
        ) : null}
        <button
          type="button"
          onClick={handleSummarizeClick}
          disabled={isSummarizing}
          className="w-full inline-flex items-center justify-center rounded-lg bg-emerald-600 py-2 px-4 text-sm font-semibold text-white ring-1 ring-emerald-500 transition hover:bg-emerald-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400 disabled:opacity-70 disabled:cursor-not-allowed"
        >
          {isSummarizing ? "Leaving…" : "Summarize Meeting"}
        </button>
      </div>
    </div>
  );
};

export default TranscriptPanel;
