"use client";

import { useCallStateHooks } from "@stream-io/video-react-sdk";
import ParticipantGrid from "./participant-grid";
import ScreenShareView from "./screen-share-view";

const MeetingContent = ({ showAssistant, currentUserId, isHost, raisedHandUserIds = [] }) => {
  const { useHasOngoingScreenShare } = useCallStateHooks();
  const hasScreenShare = useHasOngoingScreenShare();
  const raisedSet = new Set(raisedHandUserIds);

  if (hasScreenShare) {
    return (
      <div className="absolute inset-0 w-full h-full flex flex-col min-h-0 min-w-0">
        <div className="h-[118px] sm:h-[128px] md:h-[138px] xl:h-[148px] shrink-0 border-b border-slate-700/60 bg-[#020617]">
          <ParticipantGrid
            showAssistant={showAssistant}
            isStrip={true}
            currentUserId={currentUserId}
            isHost={isHost}
            raisedHandUserIds={raisedSet}
          />
        </div>
        <div className="flex-1 min-h-0 min-w-0 overflow-hidden">
          <ScreenShareView />
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-full min-h-0 min-w-0">
      <ParticipantGrid
        showAssistant={showAssistant}
        currentUserId={currentUserId}
        isHost={isHost}
        raisedHandUserIds={raisedSet}
      />
    </div>
  );
};

export default MeetingContent;