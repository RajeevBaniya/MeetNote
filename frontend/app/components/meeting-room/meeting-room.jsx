"use client";

import { useState, useCallback, useEffect } from "react";
import { StreamCall, StreamTheme } from "@stream-io/video-react-sdk";

import useMeetingCall from "@/app/lib/meeting/use-meeting-call";

import MeetingRoomContent from "./meeting-room-content";
import MeetingRoomError from "./meeting-room-error";
import MeetingRoomLoading from "./meeting-room-loading";
import ConnectionStateBanner from "./connection-state-banner";
import RecordingBanner from "./recording-banner";

import "@stream-io/video-react-sdk/dist/css/styles.css";

const MeetingRoom = ({ callId, onLeave, onSessionEnded, userId, hostId, jwt }) => {
  const [showAssistant, setShowAssistant] = useState(true);
  const [participantsOpen, setParticipantsOpen] = useState(false);
  const [currentHostId, setCurrentHostId] = useState(hostId || null);

  const { call, error, hasLeftRef } = useMeetingCall(callId, userId, onLeave, onSessionEnded);
  const isHost = Boolean(currentHostId && userId && String(currentHostId) === String(userId));

  useEffect(() => {
    setCurrentHostId(hostId || null);
  }, [hostId]);

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
      .catch((err) => {
        console.error("Assistant preference fetch failed:", err);
      });
  }, [callId, jwt]);

  const handleLeave = useCallback(() => {
    setParticipantsOpen(false);
    onLeave?.();
  }, [onLeave]);

  const handleOpenParticipants = useCallback(() => {
    setParticipantsOpen(true);
  }, []);

  const handleCloseParticipants = useCallback(() => {
    setParticipantsOpen(false);
  }, []);

  const handleHostChanged = useCallback(
    (incomingHostId) => {
      if (!incomingHostId) return;
      const next = String(incomingHostId);
      const current = currentHostId != null ? String(currentHostId) : null;
      if (current === next) return;
      setCurrentHostId(incomingHostId);
    },
    [currentHostId],
  );

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
            setCurrentHostId={handleHostChanged}
            pendingCount={0}
            onOpenWaitingRoom={undefined}
            onOpenParticipants={handleOpenParticipants}
            onCloseParticipants={handleCloseParticipants}
            participantsOpen={participantsOpen}
            currentUserId={userId}
            onLeave={onLeave}
            callId={callId}
            jwt={jwt}
            hasLeftRef={hasLeftRef}
          />
        </div>
      </StreamCall>
    </StreamTheme>
  );
};

export default MeetingRoom;