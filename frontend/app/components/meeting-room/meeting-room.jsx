"use client";

import { useState } from "react";
import { StreamCall, StreamTheme } from "@stream-io/video-react-sdk";
import useMeetingCall from "@/app/hooks/use-meeting-call";
import { useWaitingRoom } from "@/app/hooks/use-waiting-room";
import MeetingRoomContent from "./meeting-room-content";
import MeetingRoomError from "./meeting-room-error";
import MeetingRoomLoading from "./meeting-room-loading";
import WaitingRoomModal from "./waiting-room-panel";
import ParticipantsPanel from "./participants-panel";

import "@stream-io/video-react-sdk/dist/css/styles.css";

const MeetingRoom = ({ callId, onLeave, onSessionEnded, userId, jwt }) => {
  const [showAssistant, setShowAssistant] = useState(false);
  const [waitingRoomOpen, setWaitingRoomOpen] = useState(false);
  const [participantsOpen, setParticipantsOpen] = useState(false);

  const { call, error } = useMeetingCall(callId, userId, onLeave, onSessionEnded);
  const { pendingUserIds, isHost, disconnected, sendAction } = useWaitingRoom(callId, jwt);

  if (error) {
    return <MeetingRoomError error={error} />;
  }

  if (!call) {
    return <MeetingRoomLoading />;
  }

  return (
    <StreamTheme>
      <StreamCall call={call}>
        <div className="fixed inset-0 w-full h-full bg-[#020617] text-slate-100 overflow-hidden">
          <MeetingRoomContent
            showAssistant={showAssistant}
            setShowAssistant={setShowAssistant}
            isHost={isHost}
            pendingCount={pendingUserIds.length}
            onOpenWaitingRoom={() => setWaitingRoomOpen(true)}
            onOpenParticipants={() => setParticipantsOpen(true)}
            currentUserId={userId}
            onLeave={onLeave}
            callId={callId}
            jwt={jwt}
          />
          {waitingRoomOpen && isHost ? (
            <WaitingRoomModal
              pendingUserIds={pendingUserIds}
              disconnected={disconnected}
              onClose={() => setWaitingRoomOpen(false)}
              sendAction={sendAction}
            />
          ) : null}
          {participantsOpen ? (
            <ParticipantsPanel
              onClose={() => setParticipantsOpen(false)}
              currentUserId={userId}
              isHost={isHost}
              callId={callId}
              jwt={jwt}
            />
          ) : null}
        </div>
      </StreamCall>
    </StreamTheme>
  );
};

export default MeetingRoom;