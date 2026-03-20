"use client";

import { useMemo } from "react";
import { useCallStateHooks } from "@stream-io/video-react-sdk";

import MeetingContent from "./meeting-content";

const GalleryLayout = ({
  showAssistant,
  currentUserId,
  isHost,
  raisedHandUserIds,
}) => {
  const { useParticipants } = useCallStateHooks();
  const participants = useParticipants() || [];
  const isSingleParticipant = useMemo(
    () => participants.length === 1,
    [participants.length],
  );

  return (
    <div className="w-full h-full flex-1 flex items-center justify-center min-h-0 pb-6">
      <div
        className={`w-full h-full mx-auto ${
          isSingleParticipant
            ? "max-w-[min(1300px,94vw)]"
            : "max-w-[min(1700px,96vw)]"
        }`}
      >
        <div
          className={`relative w-full h-full flex-1 min-w-0 min-h-[200px] sm:min-h-[240px] md:min-h-[260px] overflow-hidden flex items-center justify-center ${
            participants.length > 1
              ? "rounded-xl sm:rounded-2xl border border-slate-700/40 bg-[#0a0a0f]"
              : ""
          }`}
        >
          <MeetingContent
            showAssistant={showAssistant}
            currentUserId={currentUserId}
            isHost={isHost}
            raisedHandUserIds={raisedHandUserIds}
          />
        </div>
      </div>
    </div>
  );
};

export default GalleryLayout;
