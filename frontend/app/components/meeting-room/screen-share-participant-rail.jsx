"use client";

import { useMemo } from "react";
import { useCallStateHooks } from "@stream-io/video-react-sdk";
import ParticipantTile from "./participant-tile";
import {
  filterAssistant,
  sortParticipants,
  isAssistantParticipant,
} from "@/app/lib/participants/participant-helpers";

const ScreenShareParticipantRail = ({
  showAssistant = false,
  currentUserId,
  isHost,
  raisedHandUserIds = new Set(),
  horizontal = false,
}) => {
  const { useParticipants } = useCallStateHooks();
  const allParticipants = useParticipants();

  const participants = useMemo(() => {
    if (!allParticipants) return [];
    return filterAssistant(allParticipants, showAssistant);
  }, [allParticipants, showAssistant]);

  const sortedParticipants = useMemo(() => {
    return sortParticipants(participants);
  }, [participants]);

  if (!sortedParticipants || sortedParticipants.length === 0) {
    return (
      <div className="w-full h-full flex items-center justify-center">
        <p className="text-slate-500 text-xs">No participants</p>
      </div>
    );
  }

  if (horizontal) {
    return (
      <div className="w-full h-full flex flex-row items-stretch gap-1.5 overflow-x-auto overflow-y-hidden px-2 py-1.5 custom-scrollbar">
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
              className="h-full aspect-video shrink-0 rounded-md overflow-hidden border border-slate-700/40"
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

  return (
    <div className="w-full h-full overflow-y-auto overflow-x-hidden p-2 space-y-2 custom-scrollbar">
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
            className="w-full aspect-video rounded-md overflow-hidden border border-slate-700/40"
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
};

export default ScreenShareParticipantRail;
