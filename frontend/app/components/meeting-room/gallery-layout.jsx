"use client";

import TranscriptPanel from "./transcript";
import MeetingContent from "./meeting-content";

const GalleryLayout = ({
  showAssistant,
  currentUserId,
  isHost,
  raisedHandUserIds,
  callId,
  hasLeftRef,
  jwt,
}) => {
  return (
    <div className="w-full h-full mx-auto flex-1 flex flex-col gap-2 sm:gap-3 md:gap-4 2xl:gap-2 lg:grid lg:grid-cols-[minmax(0,3.1fr)_minmax(280px,0.7fr)] xl:grid-cols-[minmax(0,3.1fr)_minmax(320px,0.7fr)] 2xl:grid-cols-[minmax(0,3.3fr)_minmax(320px,0.7fr)] lg:items-stretch 2xl:max-w-[1660px]">
      <div className="relative flex-1 min-h-[200px] sm:min-h-[240px] md:min-h-[260px] rounded-xl sm:rounded-2xl border border-slate-700/60 bg-[#020617] shadow-2xl overflow-hidden">
        <MeetingContent
          showAssistant={showAssistant}
          currentUserId={currentUserId}
          isHost={isHost}
          raisedHandUserIds={raisedHandUserIds}
        />
      </div>

      <div className="flex flex-1 min-h-[200px] sm:min-h-[240px] md:min-h-[260px] rounded-xl sm:rounded-2xl border border-slate-700/60 bg-[#0f172a] shadow-2xl overflow-hidden">
        <TranscriptPanel callId={callId} hasLeftRef={hasLeftRef} jwt={jwt} />
      </div>
    </div>
  );
};

export default GalleryLayout;
