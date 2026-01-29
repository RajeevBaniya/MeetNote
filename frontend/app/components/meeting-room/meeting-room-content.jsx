"use client";

import TranscriptPanel from "./transcript";
import MeetingContent from "./meeting-content";
import iconsData from "@/app/components/icons/icons.json";
import { CallControls } from "@stream-io/video-react-sdk";

const MeetingRoomContent = ({ showAssistant, setShowAssistant, onLeave }) => {
  return (
    <div className="flex-1 flex flex-col w-full min-w-0 min-h-0 p-0 overflow-hidden">
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-[1fr_320px] xl:grid-cols-[1fr_360px] 2xl:grid-cols-[1fr_380px] gap-2 lg:gap-3 min-h-0 w-full min-w-0 overflow-hidden">
        <div className="flex flex-col gap-2 lg:gap-3 min-h-0 h-full min-w-0 overflow-hidden">
          <div className="relative flex-1 min-h-0 h-full w-full rounded-none lg:rounded-xl border-0 lg:border border-slate-700 overflow-hidden shadow-2xl bg-[#020617]">
            <MeetingContent showAssistant={showAssistant} />
          </div>

          <div className="flex justify-center shrink-0">
            <div className="bg-[#0f172a] rounded-full px-6 py-4 border border-slate-700 shadow-xl flex items-center gap-3">
              <button
                onClick={() => setShowAssistant(!showAssistant)}
                className={`flex items-center justify-center w-10 h-10 rounded-full transition-colors ${
                  showAssistant
                    ? "bg-green-500 hover:bg-green-600 text-white"
                    : "bg-gray-700 hover:bg-gray-600 text-gray-300"
                }`}
                title={showAssistant ? "Hide Assistant" : "Show Assistant"}
              >
                <span 
                  className="w-5 h-5" 
                  dangerouslySetInnerHTML={{ __html: iconsData.robot }}
                />
              </button>

              <CallControls onLeave={onLeave} />
            </div>
          </div>
        </div>

        <div className="min-h-0 h-full min-w-0 flex flex-col bg-[#0f172a] rounded-none lg:rounded-2xl border-0 lg:border border-slate-700 overflow-hidden shadow-2xl">
          <TranscriptPanel />
        </div>
      </div>
    </div>
  );
};

export default MeetingRoomContent;