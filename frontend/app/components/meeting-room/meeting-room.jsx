"use client";

import { useState } from "react";
import { StreamCall, StreamTheme } from "@stream-io/video-react-sdk";
import useMeetingCall from "@/app/hooks/use-meeting-call";
import MeetingRoomContent from "./meeting-room-content";
import MeetingRoomError from "./meeting-room-error";
import MeetingRoomLoading from "./meeting-room-loading";

import "@stream-io/video-react-sdk/dist/css/styles.css";

const MeetingRoom = ({ callId, onLeave, userId }) => {
  const [showAssistant, setShowAssistant] = useState(false);
  const { call, error, handleLeave } = useMeetingCall(callId, userId, onLeave);

  if (error) {
    return <MeetingRoomError error={error} />;
  }

  if (!call) {
    return <MeetingRoomLoading />;
  }

  return (
    <StreamTheme>
      <StreamCall call={call}>
        <div className="h-screen bg-[#020617] text-slate-100 overflow-hidden">
          <MeetingRoomContent 
            showAssistant={showAssistant}
            setShowAssistant={setShowAssistant}
            onLeave={handleLeave}
          />
        </div>
      </StreamCall>
    </StreamTheme>
  );
};

export default MeetingRoom;