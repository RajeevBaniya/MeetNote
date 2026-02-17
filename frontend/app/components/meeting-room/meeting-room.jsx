"use client";

import { useState, useCallback, useEffect } from "react";
import { StreamCall, StreamTheme } from "@stream-io/video-react-sdk";
import useMeetingCall from "@/app/lib/use-meeting-call";
import { useWaitingRoom } from "@/app/lib/use-waiting-room";
import MeetingRoomContent from "./meeting-room-content";
import MeetingRoomError from "./meeting-room-error";
import MeetingRoomLoading from "./meeting-room-loading";
import WaitingRoomModal from "./waiting-room-panel";
import ConnectionStateBanner from "./connection-state-banner";
import RecordingBanner from "./recording-banner";

import "@stream-io/video-react-sdk/dist/css/styles.css";

const MeetingRoom = ({ callId, onLeave, onSessionEnded, userId, hostId, jwt }) => {
  const [showAssistant, setShowAssistant] = useState(true);
  const [waitingRoomOpen, setWaitingRoomOpen] = useState(false);
  const [participantsOpen, setParticipantsOpen] = useState(false);

  const { call, error } = useMeetingCall(callId, userId, onLeave, onSessionEnded);
  const { pendingUserIds, disconnected, sendAction } = useWaitingRoom(callId, jwt);
  const isHost = Boolean(hostId && userId && String(hostId) === String(userId));

  useEffect(() => {
    if (!callId || !jwt) return;
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    if (!apiUrl) return;
    fetch(`${apiUrl}/meetings/${callId}/assistant-preference`, {
      headers: { Authorization: `Bearer ${jwt}` },
    })
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data && typeof data.enabled === "boolean") setShowAssistant(data.enabled);
      })
      .catch(() => {});
  }, [callId, jwt]);

  const handleLeave = useCallback(() => {
    setWaitingRoomOpen(false);
    setParticipantsOpen(false);
    onLeave?.();
  }, [onLeave]);

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
          <ConnectionStateBanner />
          <RecordingBanner />
          <MeetingRoomContent
            showAssistant={showAssistant}
            setShowAssistant={setShowAssistant}
            isHost={isHost}
            pendingCount={pendingUserIds.length}
            onOpenWaitingRoom={() => setWaitingRoomOpen(true)}
            onOpenParticipants={() => setParticipantsOpen(true)}
            onCloseParticipants={() => setParticipantsOpen(false)}
            participantsOpen={participantsOpen}
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
        </div>
      </StreamCall>
    </StreamTheme>
  );
};

export default MeetingRoom;