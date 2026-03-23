"use client";

import { useMemo } from "react";
import { useCall, useCallStateHooks } from "@stream-io/video-react-sdk";

import {
  filterAssistant,
  isAssistantParticipant,
  sortParticipants,
} from "@/app/lib/participants/participants-sort";

import ParticipantTile from "./participant-tile";

const ParticipantGrid = ({
  showAssistant = false,
  isCompact = false,
  isStrip = false,
  currentUserId,
  isHost,
  raisedHandUserIds = new Set(),
}) => {
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
    if (participantCount === 2) return "grid-cols-1 lg:grid-cols-2";
    if (participantCount <= 4) return "grid-cols-2";
    if (participantCount <= 6) return "grid-cols-2 lg:grid-cols-3";
    if (participantCount <= 9) return "grid-cols-2 lg:grid-cols-3";
    if (participantCount <= 12)
      return "grid-cols-2 lg:grid-cols-3 xl:grid-cols-4";
    if (participantCount <= 16) return "grid-cols-3 lg:grid-cols-4";
    return "grid-cols-3 lg:grid-cols-4 xl:grid-cols-5";
  };

  if (isStrip) {
    return (
      <div className="w-full h-full bg-[#020617] flex flex-row items-stretch gap-2 overflow-x-auto overflow-y-hidden px-3 py-2 custom-scrollbar">
        {sortedParticipants.map((participant) => {
          const key = participant.sessionId || participant.userId;
          const showHostBadge =
            Boolean(isHost) &&
            Boolean(currentUserId) &&
            participant.userId === currentUserId;
          const isHandRaised = Boolean(
            participant.userId && raisedHandUserIds.has(participant.userId),
          );
          return (
            <div
              key={key}
              className="relative h-full aspect-video shrink-0 rounded-lg overflow-hidden border border-slate-700/40"
            >
              <ParticipantTile
                participant={participant}
                isAssistant={isAssistantParticipant(participant)}
                isHost={showHostBadge}
                isHandRaised={isHandRaised}
              />
            </div>
          );
        })}
      </div>
    );
  }

  if (isCompact) {
    return (
      <div className="absolute inset-0 w-full h-full bg-[#020617] rounded-none overflow-hidden flex flex-col min-h-0 min-w-0">
        <div className="flex-1 overflow-y-auto p-1.5 space-y-1.5 custom-scrollbar min-h-0">
          {sortedParticipants.map((participant) => {
            const key = participant.sessionId || participant.userId;
            const showHostBadge =
              Boolean(isHost) &&
              Boolean(currentUserId) &&
              participant.userId === currentUserId;
            const isHandRaised = Boolean(
              participant.userId && raisedHandUserIds.has(participant.userId),
            );
            return (
              <div
                key={key}
                className="w-full aspect-video shrink-0 rounded-lg overflow-hidden"
              >
                <ParticipantTile
                  participant={participant}
                  isAssistant={isAssistantParticipant(participant)}
                  isHost={showHostBadge}
                  isHandRaised={isHandRaised}
                />
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  if (participantCount === 1) {
    const participant = sortedParticipants[0];
    const showHostBadge =
      Boolean(isHost) &&
      Boolean(currentUserId) &&
      participant.userId === currentUserId;
    const isHandRaised = Boolean(
      participant.userId && raisedHandUserIds.has(participant.userId),
    );
    return (
      <div className="absolute inset-0 w-full h-full bg-[#020617] overflow-hidden">
        <ParticipantTile
          participant={participant}
          isAssistant={isAssistantParticipant(participant)}
          isHost={showHostBadge}
          isHandRaised={isHandRaised}
        />
      </div>
    );
  }

  return (
    <div className="absolute inset-0 w-full h-full p-2 sm:p-3 md:p-4 bg-[#020617] overflow-auto flex items-center justify-center">
      <div
        className={`grid ${getGridClass()} gap-2 sm:gap-3 md:gap-4 w-full max-w-full`}
      >
        {sortedParticipants.map((participant) => {
          const key = participant.sessionId || participant.userId;
          const showHostBadge =
            Boolean(isHost) &&
            Boolean(currentUserId) &&
            participant.userId === currentUserId;
          const isHandRaised = Boolean(
            participant.userId && raisedHandUserIds.has(participant.userId),
          );
          return (
            <div key={key} className="min-h-0 min-w-0 w-full aspect-video">
              <ParticipantTile
                participant={participant}
                isAssistant={isAssistantParticipant(participant)}
                isHost={showHostBadge}
                isHandRaised={isHandRaised}
              />
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default ParticipantGrid;
