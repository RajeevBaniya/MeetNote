"use client";

import { TranscriptPanel } from "./transcript";
import MeetingContent from "./meeting-content";
import iconsData from "@/app/components/icons/icons.json";
import { CallControls } from "@stream-io/video-react-sdk";

function MeetingRoomContent({ showAssistant, setShowAssistant, onLeave }) {
  return (
    <div className="h-full flex flex-col px-4 py-4">
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-4 min-h-0">
        <div className="flex flex-col gap-4 min-h-0">
          <div className="flex-1 rounded-xl bg-gray-800 border border-gray-700 overflow-hidden shadow-2xl min-h-0">
            <MeetingContent showAssistant={showAssistant} />
          </div>

          <div className="flex justify-center">
            <div className="bg-gray-800 rounded-full px-6 py-4 border border-gray-700 shadow-xl flex items-center gap-3">
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

        <div className="bg-gray-800 rounded-2xl border border-gray-700 overflow-hidden shadow-2xl min-h-0">
          <TranscriptPanel />
        </div>
      </div>
    </div>
  );
}

export default MeetingRoomContent;