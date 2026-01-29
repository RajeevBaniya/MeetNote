"use client";

import { useEffect, useState, useRef } from "react";
import { useCall } from "@stream-io/video-react-sdk";
import iconsData from "@/app/components/icons/icons.json";

const TranscriptPanel = () => {
  const [transcripts, setTranscripts] = useState([]);
  const transcriptEndRef = useRef(null);
  const call = useCall();

  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [transcripts]);

  useEffect(() => {
    if (!call) return;

    const handleClosedCaption = (event) => {
      if (event.closed_caption) {
        const newTranscript = {
          id: `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`,
          text: event.closed_caption.text,
          speaker:
            event.closed_caption.user?.name ||
            event.closed_caption.user?.id ||
            "Unknown",
          timestamp: new Date(
            event.closed_caption.start_time
          ).toLocaleTimeString(),
        };
        setTranscripts((prev) => [...prev, newTranscript]);
      }
    };

    call.on("call.closed_caption", handleClosedCaption);

    return () => {
      call.off("call.closed_caption", handleClosedCaption);
    };
  }, [call]);

  return (
    <div className="h-full flex flex-col">
      <div className="px-6 py-5 border-b border-emerald-900/60 bg-linear-to-r from-emerald-900/30 to-slate-900/60">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-500/10 rounded-lg">
              <span 
                className="w-6 h-6 text-blue-500" 
                dangerouslySetInnerHTML={{ __html: iconsData.document }}
              />
            </div>
            <div>
              <h3 className="text-lg font-bold text-white">Live Transcript</h3>
              <p className="text-xs text-gray-400 mt-0.5">
                {transcripts.length}{" "}
                {transcripts.length === 1 ? "message" : "messages"}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
            <span className="text-xs text-green-500 font-medium">Live</span>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-3 bg-slate-900/80 custom-scrollbar">
        {transcripts.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center px-4">
            <div className="relative mb-6">
              <div className="w-20 h-20 bg-gray-700 rounded-full flex items-center justify-center">
                <span 
                  className="w-10 h-10 text-gray-500" 
                  dangerouslySetInnerHTML={{ __html: iconsData.microphone }}
                />
              </div>
              <div className="absolute -bottom-1 -right-1 w-6 h-6 bg-blue-500 rounded-full flex items-center justify-center">
                <span 
                  className="w-4 h-4 text-white" 
                  dangerouslySetInnerHTML={{ __html: iconsData.plus }}
                />
              </div>
            </div>
            <p className="text-gray-300 text-lg font-semibold mb-2">
              Waiting for transcripts...
            </p>
            <p className="text-gray-500 text-sm max-w-xs">
              Start speaking to see live transcription appear here.
            </p>
          </div>
        ) : (
          <>
            {transcripts.map((transcript) => (
              <div
                key={transcript.id}
                className="group rounded-xl border border-emerald-900/60 bg-slate-900/80 p-4 shadow-lg shadow-emerald-900/40 transition-all duration-300 hover:border-emerald-400/70 hover:shadow-[0_0_25px_rgba(16,185,129,0.4)] hover:-translate-y-0.5"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-full bg-emerald-500/15 text-emerald-300 text-sm font-bold ring-2 ring-emerald-400/40">
                      {transcript.speaker.charAt(0).toUpperCase()}
                    </div>
                    <div>
                      <span className="font-semibold text-blue-400 text-sm">
                        {transcript.speaker}
                      </span>
                      <p className="text-xs text-gray-400 font-mono mt-0.5">
                        {transcript.timestamp}
                      </p>
                    </div>
                  </div>
                </div>
                <p className="text-gray-100 leading-relaxed text-sm pl-13">
                  {transcript.text}
                </p>
              </div>
            ))}
            <div ref={transcriptEndRef} />
          </>
        )}
      </div>
    </div>
  );
};

export default TranscriptPanel;