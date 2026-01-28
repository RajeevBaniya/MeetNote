"use client";

import { useCallStateHooks, ParticipantView } from "@stream-io/video-react-sdk";
import { hasScreenShare } from "@stream-io/video-client";

const ScreenShareView = () => {
  const { useParticipants, useHasOngoingScreenShare } = useCallStateHooks();
  const participants = useParticipants();
  const hasOngoingScreenShare = useHasOngoingScreenShare();

  if (!hasOngoingScreenShare || !participants) {
    return null;
  }

  const screenSharingParticipant = participants.find((p) => hasScreenShare(p));

  if (!screenSharingParticipant) {
    return null;
  }

  return (
    <div className="relative w-full h-full bg-gray-900 rounded-lg overflow-hidden border border-gray-700">
      <div className="absolute inset-0 w-full h-full participant-video-container">
        <ParticipantView 
          participant={screenSharingParticipant}
          trackType="screenShareTrack"
        />
      </div>
      <div className="absolute top-4 left-4 z-10 bg-black/60 px-3 py-2 rounded-lg">
        <span className="text-white text-sm font-medium">
          {screenSharingParticipant.name || screenSharingParticipant.userId} is sharing
        </span>
      </div>
    </div>
  );
};

export default ScreenShareView;