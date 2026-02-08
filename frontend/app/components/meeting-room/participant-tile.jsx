"use client";

import { memo } from "react";
import { ParticipantView, useCallStateHooks } from "@stream-io/video-react-sdk";
import iconsData from "@/app/components/icons/icons.json";

const ParticipantTile = memo(function ParticipantTile({ participant, isAssistant = false, isHost = false, isHandRaised = false }) {
  const { useParticipants } = useCallStateHooks();
  const allParticipants = useParticipants();
  const participantCount = allParticipants?.length || 0;
  const isSingleParticipant = participantCount === 1;

  const displayName = participant?.name || participant?.userId || "Unknown";

  return (
    <div
      className={`relative w-full h-full min-w-0 min-h-0 bg-[#020617] overflow-hidden group ${
        isSingleParticipant
          ? "rounded-none border-0"
          : "rounded-lg md:rounded-xl border border-slate-700/30 shadow-lg"
      }`}
    >
      <div className="absolute inset-0 w-full h-full min-w-full min-h-full participant-video-container">
        <ParticipantView participant={participant} />
      </div>
      <div className="absolute top-3 left-3 z-10 flex flex-col gap-1">
        {isHost ? (
          <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-emerald-500 text-white text-xs font-semibold">
            <span
              className="w-3 h-3"
              dangerouslySetInnerHTML={{ __html: iconsData.checkmark }}
            />
            Host
          </span>
        ) : null}
        {isAssistant ? (
          <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-green-500 text-white text-xs font-medium">
            <span
              className="w-3 h-3"
              dangerouslySetInnerHTML={{ __html: iconsData.checkmark }}
            />
            Assistant
          </span>
        ) : null}
        {isHandRaised ? (
          <span className="inline-flex items-center px-2 py-1 rounded-full bg-amber-500/90 text-white text-xs font-medium" title="Hand raised">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-3.5 h-3.5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6.633 10.25c.806 0 1.533-.446 2.031-1.08a9.041 9.041 0 0 1 2.861-2.4c.723-.384 1.35-.956 1.653-1.715a4.498 4.498 0 0 0 .322-1.672V2.75a.75.75 0 0 1 1.5 0v2.716a5.499 5.499 0 0 1-.43 2.103 5.99 5.99 0 0 1 2.43 2.103 5.499 5.499 0 0 1-.43-2.103V2.75a.75.75 0 0 1 1.5 0v6.375a4.5 4.5 0 0 1-1.5 3.375 9 9 0 0 1-6.939 2.437A9.001 9.001 0 0 1 6.633 10.25z" />
            </svg>
          </span>
        ) : null}
      </div>
      <div className="absolute bottom-3 left-3 z-10">
        <span className="text-white text-sm font-medium drop-shadow-lg">
          {displayName}
        </span>
      </div>
      <div className="absolute inset-0 bg-blue-500/10 opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none z-0" />
    </div>
  );
});

export default ParticipantTile;