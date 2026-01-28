"use client";

import { ParticipantView } from "@stream-io/video-react-sdk";
import iconsData from "@/app/components/icons/icons.json";

const ParticipantTile = ({ participant, isAssistant = false }) => {
  return (
    <div className="relative w-full h-full bg-gray-900 rounded-lg overflow-hidden border border-gray-700 group">
      <div className="absolute inset-0 w-full h-full participant-video-container">
        <ParticipantView participant={participant} />
      </div>

      {/* Assistant Badge Only - Stream.io handles name display */}
      {isAssistant && (
        <div className="absolute bottom-3 left-3 z-10">
          <span className="inline-flex items-center gap-1 px-2 py-1 bg-green-500 text-white text-xs font-medium rounded-full">
            <span 
              className="w-3 h-3" 
              dangerouslySetInnerHTML={{ __html: iconsData.checkmark }}
            />
            Assistant
          </span>
        </div>
      )}

      <div className="absolute inset-0 bg-blue-500/10 opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none z-0" />
    </div>
  );
};

export default ParticipantTile;