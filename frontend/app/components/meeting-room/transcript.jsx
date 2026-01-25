"use client";

import { useEffect, useState, useRef } from "react";
import { useCall } from "@stream-io/video-react-sdk";
import { useChatContext } from "stream-chat-react";
import iconsData from "@/app/components/icons/icons.json";

export function TranscriptPanel() {
  const { client } = useChatContext();
  const [transcripts, setTranscripts] = useState([]);
  const transcriptEndRef = useRef(null);
  const call = useCall();

  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [transcripts]);

  useEffect(() => {
    if (!call || !client) {
      return;
    }

    const callId = process.env.NEXT_PUBLIC_CALL_ID;
    const channel = client.channel("messaging", callId);

    channel.watch();

    const handleClosedCaption = (event) => {
      if (event.closed_caption) {
        const newTranscript = {
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

    const handleNewMessage = (event) => {
      const message = event.message;

      if (message?.user?.id !== "meeting-assistant-bot") {
        return;
      }
    };

    call.on("call.closed_caption", handleClosedCaption);

    channel.on("message.new", handleNewMessage);

    return () => {
      call.off("call.closed_caption", handleClosedCaption);
      channel.off("message.new", handleNewMessage);
    };
  }, [call, client]);

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="px-6 py-5 border-b border-gray-700 bg-linear-to-r from-gray-800 to-gray-750">
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

      {/* Transcript List */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-3 bg-gray-850 custom-scrollbar">
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
            {transcripts.map((transcript) => {
              const stableKey = `${transcript.timestamp}-${transcript.speaker}-${transcript.text.substring(0, 20)}`;
              return (
                <div
                  key={stableKey}
                  className="group bg-gradient-to-br from-gray-700 to-gray-750 rounded-xl p-4 shadow-lg hover:shadow-xl transition-all duration-300 border border-gray-600 hover:border-blue-500/50 transform hover:-translate-y-0.5"
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center text-white font-bold text-sm shadow-lg ring-2 ring-blue-500/20">
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
              );
            })}
            <div ref={transcriptEndRef} />
          </>
        )}
      </div>
    </div>
  );
}