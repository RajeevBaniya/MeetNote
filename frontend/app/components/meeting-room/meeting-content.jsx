"use client";

import { useCallStateHooks } from "@stream-io/video-react-sdk";
import ParticipantGrid from "./participant-grid";
import ScreenShareView from "./screen-share-view";

const MeetingContent = ({ showAssistant }) => {
  const { useHasOngoingScreenShare } = useCallStateHooks();
  const hasScreenShare = useHasOngoingScreenShare();

  if (hasScreenShare) {
    return (
      <div className="w-full h-full flex gap-3">
        <div className="flex-1 min-w-0 rounded-lg overflow-hidden">
          <ScreenShareView />
        </div>
        <div className="w-56 shrink-0 rounded-lg overflow-hidden">
          <ParticipantGrid showAssistant={showAssistant} isCompact={true} />
        </div>
      </div>
    );
  }

  return <ParticipantGrid showAssistant={showAssistant} />;
};

export default MeetingContent;