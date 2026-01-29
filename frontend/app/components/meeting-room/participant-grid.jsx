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
      <div className="absolute inset-0 w-full h-full flex items-center justify-center bg-[#020617] rounded-none min-h-0 min-w-0">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-slate-400">Waiting for participants...</p>
        </div>
      </div>
    );
  }

  const participantCount = participants.length;

  const getGridClass = () => {
    if (isCompact) return "grid-cols-1";
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
    return (
      <div className="absolute inset-0 w-full h-full bg-[#020617] rounded-none overflow-hidden flex flex-col min-h-0 min-w-0">
        <div className="flex-1 overflow-y-auto p-2 space-y-2 custom-scrollbar min-h-0">
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

  if (participantCount === 1) {
    const participant = sortedParticipants[0];
    return (
      <div className="absolute inset-0 w-full h-full bg-[#020617] rounded-none overflow-hidden min-h-0 min-w-0">
        <ParticipantTile 
          participant={participant} 
          isAssistant={isAssistantParticipant(participant)}
        />
      </div>
    );
  }

  return (
    <div className="absolute inset-0 w-full h-full p-0 bg-[#020617] rounded-none overflow-hidden min-h-0 min-w-0 flex">
      <div className={`grid ${getGridClass()} gap-2 w-full h-full min-h-0 min-w-0`}>
        {sortedParticipants.map((participant) => (
          <div key={participant.sessionId || participant.userId} className="min-h-0 min-w-0 w-full h-full">
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