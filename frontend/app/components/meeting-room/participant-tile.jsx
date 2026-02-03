"use client";

import { ParticipantView, useCallStateHooks } from "@stream-io/video-react-sdk";
import iconsData from "@/app/components/icons/icons.json";

const ParticipantTile = ({ participant, isAssistant = false, isHost = false }) => {
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
        <ParticipantView participant={participant} ParticipantViewUI={null} />
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
      </div>
      <div className="absolute bottom-3 left-3 z-10">
        <span className="text-white text-sm font-medium drop-shadow-lg">
          {displayName}
        </span>
      </div>
      <div className="absolute inset-0 bg-blue-500/10 opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none z-0" />
    </div>
  );
};

export default ParticipantTile;