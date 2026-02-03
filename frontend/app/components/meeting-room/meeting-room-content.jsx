"use client";

import TranscriptPanel from "./transcript";
import MeetingContent from "./meeting-content";
import MeetingControls from "./meeting-controls";
import iconsData from "@/app/components/icons/icons.json";

const MeetingRoomContent = ({
  showAssistant,
  setShowAssistant,
  isHost,
  pendingCount,
  onOpenWaitingRoom,
  currentUserId,
  onLeave,
}) => {
  return (
    <div className="flex flex-col w-full h-full overflow-hidden bg-[#020617]">
      <div className="flex-1 flex flex-col px-2 py-2 sm:px-4 sm:py-4 md:px-6 md:py-4 lg:px-10 lg:py-6 min-h-0 overflow-hidden">
        <div className="w-full h-full mx-auto flex-1 flex flex-col gap-2 sm:gap-3 md:gap-4 2xl:gap-2 lg:grid lg:grid-cols-[minmax(0,3.1fr)_minmax(280px,0.7fr)] xl:grid-cols-[minmax(0,3.1fr)_minmax(320px,0.7fr)] 2xl:grid-cols-[minmax(0,3.3fr)_minmax(320px,0.7fr)] lg:items-stretch 2xl:max-w-[1660px]">
          <div className="relative flex-1 min-h-[200px] sm:min-h-[240px] md:min-h-[260px] rounded-xl sm:rounded-2xl border border-slate-700/60 bg-[#020617] shadow-2xl overflow-hidden">
            <MeetingContent
              showAssistant={showAssistant}
              currentUserId={currentUserId}
              isHost={isHost}
            />
          </div>

          <div className="flex flex-1 min-h-[200px] sm:min-h-[240px] md:min-h-[260px] rounded-xl sm:rounded-2xl border border-slate-700/60 bg-[#0f172a] shadow-2xl overflow-hidden">
            <TranscriptPanel />
          </div>
        </div>
      </div>

      <div className="flex justify-center items-center shrink-0 pb-1 sm:pb-2">
        <div className="w-full bg-[#020617] px-2 py-1.5 sm:px-4 sm:py-1.5 md:px-6 md:py-2 border-t border-slate-800/80 flex items-center gap-1.5 sm:gap-2 md:gap-3 flex-wrap justify-center">
          <button
            onClick={() => setShowAssistant(!showAssistant)}
            className={`flex items-center justify-center w-8 h-8 sm:w-9 sm:h-9 rounded-full transition-colors ${
              showAssistant
                ? "bg-green-500 hover:bg-green-600 text-white"
                : "bg-gray-700 hover:bg-gray-600 text-gray-300"
            }`}
            title={showAssistant ? "Hide Assistant" : "Show Assistant"}
          >
            <span
              className="w-4 h-4 sm:w-5 sm:h-5"
              dangerouslySetInnerHTML={{ __html: iconsData.robot }}
            />
          </button>

          <MeetingControls onLeave={onLeave} />

          {isHost ? (
            <button
              onClick={onOpenWaitingRoom}
              className="relative flex items-center justify-center w-8 h-8 sm:w-9 sm:h-9 rounded-full transition-colors bg-gray-700 hover:bg-gray-600 text-gray-300"
              title="Waiting Room"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={1.5}
                stroke="currentColor"
                className="w-4 h-4 sm:w-5 sm:h-5"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M18 18.72a9.094 9.094 0 003.741-.479 3 3 0 00-4.682-2.72m.94 3.198l.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0112 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 016 18.719m12 0a5.971 5.971 0 00-.941-3.197m0 0A5.995 5.995 0 0012 12.75a5.995 5.995 0 00-5.058 2.772m0 0a3 3 0 00-4.681 2.72 8.986 8.986 0 003.74.477m.94-3.197a5.971 5.971 0 00-.94 3.197M15 6.75a3 3 0 11-6 0 3 3 0 016 0zm6 3a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0zm-13.5 0a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0z"
                />
              </svg>
              {pendingCount > 0 ? (
                <span className="absolute -top-0.5 -right-0.5 bg-red-500 text-white text-[10px] font-bold rounded-full w-4 h-4 sm:w-5 sm:h-5 flex items-center justify-center">
                  {pendingCount}
                </span>
              ) : null}
            </button>
          ) : null}
        </div>
      </div>
    </div>
  );
};

export default MeetingRoomContent;