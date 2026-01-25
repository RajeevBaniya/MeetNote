"use client";

import { useState } from "react";
import { StreamCall, StreamTheme } from "@stream-io/video-react-sdk";
import useMeetingCall from "@/app/hooks/use-meeting-call";
import MeetingRoomContent from "./meeting-room-content";
import MeetingRoomError from "./meeting-room-error";
import MeetingRoomLoading from "./meeting-room-loading";

import "@stream-io/video-react-sdk/dist/css/styles.css";

function MeetingRoom({ callId, onLeave, userId }) {
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
        <div className="h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 text-white overflow-hidden">
          <MeetingRoomContent 
            showAssistant={showAssistant}
            setShowAssistant={setShowAssistant}
            onLeave={handleLeave}
          />
        </div>
      </StreamCall>
    </StreamTheme>
  );
}

export default MeetingRoom;