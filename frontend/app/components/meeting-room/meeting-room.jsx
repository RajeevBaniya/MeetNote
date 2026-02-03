"use client";

import { useState } from "react";
import { StreamCall, StreamTheme } from "@stream-io/video-react-sdk";
import useMeetingCall from "@/app/hooks/use-meeting-call";
import { useWaitingRoom } from "@/app/hooks/use-waiting-room";
import MeetingRoomContent from "./meeting-room-content";
import MeetingRoomError from "./meeting-room-error";
import MeetingRoomLoading from "./meeting-room-loading";
import WaitingRoomModal from "./waiting-room-panel";

import "@stream-io/video-react-sdk/dist/css/styles.css";

const MeetingRoom = ({ callId, onLeave, userId, jwt }) => {
  const [showAssistant, setShowAssistant] = useState(false);
  const [waitingRoomOpen, setWaitingRoomOpen] = useState(false);
  const { call, error } = useMeetingCall(callId, userId, onLeave);
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
            currentUserId={userId}
            onLeave={onLeave}
          />
          {waitingRoomOpen && isHost ? (
            <WaitingRoomModal
              pendingUserIds={pendingUserIds}
              disconnected={disconnected}
              onClose={() => setWaitingRoomOpen(false)}
              sendAction={sendAction}
            />
          ) : null}
        </div>
      </StreamCall>
    </StreamTheme>
  );
};

export default MeetingRoom;