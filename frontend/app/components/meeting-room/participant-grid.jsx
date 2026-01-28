"use client";

import { useMemo } from "react";
import { useCall, useCallStateHooks } from "@stream-io/video-react-sdk";
import ParticipantTile from "./participant-tile";
import { filterAssistant, sortParticipants, isAssistantParticipant } from "@/app/utils/participant-helpers";

const ParticipantGrid = ({ showAssistant = false, isCompact = false }) => {
  const call = useCall();
  const { useParticipants } = useCallStateHooks();
  const allParticipants = useParticipants();
  
  const participants = useMemo(() => {
    if (!allParticipants) return [];
    return filterAssistant(allParticipants, showAssistant);
  }, [allParticipants, showAssistant]);
  
  const sortedParticipants = useMemo(() => {
    return sortParticipants(participants);
  }, [participants]);

  if (!participants || participants.length === 0) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-gray-900 rounded-lg">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-gray-400">Waiting for participants...</p>
        </div>
      </div>
    );
  }

  const participantCount = participants.length;

  // Determine grid layout based on participant count and compact mode
  const getGridClass = () => {
    if (isCompact) {
      // Compact mode for sidebar (screen sharing active) - always vertical one by one
      return "grid-cols-1";
    }
    
    // Normal mode (no screen sharing)
    if (participantCount === 1) return "grid-cols-1";
    if (participantCount === 2) return "grid-cols-1 sm:grid-cols-2";
    if (participantCount <= 4) return "grid-cols-2";
    if (participantCount <= 6) return "grid-cols-2 md:grid-cols-3";
    if (participantCount <= 9) return "grid-cols-2 md:grid-cols-3";
    if (participantCount <= 12) return "grid-cols-2 md:grid-cols-3 lg:grid-cols-4";
    if (participantCount <= 16) return "grid-cols-3 md:grid-cols-4";
    return "grid-cols-3 md:grid-cols-4 lg:grid-cols-5";
  };


  if (isCompact) {
    // Vertical scrollable list for screen sharing sidebar
    return (
      <div className="w-full h-full bg-gray-900 rounded-lg overflow-hidden flex flex-col">
        <div className="flex-1 overflow-y-auto p-2 space-y-2 custom-scrollbar">
          {sortedParticipants.map((participant) => (
            <div key={participant.sessionId || participant.userId} className="h-32 shrink-0">
              <ParticipantTile 
                participant={participant} 
                isAssistant={isAssistantParticipant(participant)}
              />
            </div>
          ))}
        </div>
      </div>
    );
  }

  // Normal grid layout (no screen sharing)
  return (
    <div className="w-full h-full p-4 bg-gray-900 rounded-lg overflow-hidden">
      <div className={`grid ${getGridClass()} gap-3 h-full w-full`}>
        {sortedParticipants.map((participant) => (
          <div key={participant.sessionId || participant.userId} className="min-h-0">
            <ParticipantTile 
              participant={participant} 
              isAssistant={isAssistantParticipant(participant)}
            />
          </div>
        ))}
      </div>
    </div>
  );
};

export default ParticipantGrid;