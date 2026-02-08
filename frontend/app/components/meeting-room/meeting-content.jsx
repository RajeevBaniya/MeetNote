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
      <div className="w-full h-full flex gap-3 min-h-0 min-w-0">
        <div className="flex-1 min-w-0 min-h-0 rounded-lg overflow-hidden">
          <ScreenShareView />
        </div>
        <div className="w-56 shrink-0 min-h-0 rounded-lg overflow-hidden">
          <ParticipantGrid
            showAssistant={showAssistant}
            isCompact={true}
            currentUserId={currentUserId}
            isHost={isHost}
            raisedHandUserIds={raisedSet}
          />
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