"use client";

import { useMemo } from "react";
import { useCallStateHooks } from "@stream-io/video-react-sdk";

import { isScreenSharePublisher } from "@/app/lib/screenshare/screen-share";

import ScreenShareParticipantRail from "../screen-share/screen-share-participant-rail";
import ScreenShareView from "../screen-share/screen-share-view";

const TopBar = ({ sharerName }) => {
  return (
    <div className="absolute top-0 left-0 right-0 z-20 h-9 flex items-center justify-center bg-emerald-600/90 backdrop-blur-sm">
      <span className="text-white text-xs font-medium tracking-wide">
        You are viewing {sharerName}&apos;s screen
      </span>
    </div>
  );
};

const ScreenShareLayout = ({
  showAssistant,
  currentUserId,
  isHost,
  raisedHandUserIds,
}) => {
  const { useParticipants } = useCallStateHooks();
  const participants = useParticipants() || [];
  const raisedSet = useMemo(() => new Set(raisedHandUserIds || []), [raisedHandUserIds]);

  const screenSharingParticipant = participants.find(isScreenSharePublisher);

  const sharerName = screenSharingParticipant?.name || screenSharingParticipant?.userId || "Someone";

  return (
    <div className="relative w-full h-full flex flex-col bg-[#020617] rounded-xl overflow-hidden border border-slate-700/60">
      <TopBar sharerName={sharerName} />

      <div className="flex-1 w-full h-full flex flex-col min-w-0 min-h-0 mt-9">
        <div className="flex w-full h-full">
          <div className="flex-1 w-full h-full min-w-0 min-h-0 flex items-center justify-center bg-[#0a0a0f] relative overflow-hidden">
            <ScreenShareView className="max-w-full max-h-full object-contain" />
          </div>
          <div className="hidden md:flex w-[320px] shrink-0 border-l border-slate-700/60 bg-[#020617]">
            <ScreenShareParticipantRail
              showAssistant={showAssistant}
              currentUserId={currentUserId}
              isHost={isHost}
              raisedHandUserIds={raisedSet}
            />
          </div>
        </div>
      </div>

      <div className="md:hidden h-[100px] shrink-0 border-t border-slate-700/60 bg-[#020617]">
        <ScreenShareParticipantRail
          showAssistant={showAssistant}
          currentUserId={currentUserId}
          isHost={isHost}
          raisedHandUserIds={raisedSet}
          horizontal={true}
        />
      </div>

    </div>
  );
};

export default ScreenShareLayout;
