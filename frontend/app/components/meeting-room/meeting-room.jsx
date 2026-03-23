"use client";

import { useCallback, useEffect, useState } from "react";
import { StreamCall, StreamTheme } from "@stream-io/video-react-sdk";

import useMeetingCall from "@/app/lib/meeting/use-meeting-call";
import { useMeetingExit } from "@/app/lib/meeting/use-meeting-exit";
import { useLiveTranscript } from "@/app/lib/transcript/use-live-transcript";
import { useTranscriptPanel } from "@/app/lib/transcript/use-transcript-panel";

import ConnectionStateBanner from "./shell/connection-state-banner";
import MeetingExitLoading from "./shell/meeting-exit-loading";
import MeetingRoomContent from "./shell/meeting-room-content";
import MeetingRoomError from "./shell/meeting-room-error";
import MeetingRoomLoading from "./shell/meeting-room-loading";
import RecordingBanner from "./shell/recording-banner";

import "@stream-io/video-react-sdk/dist/css/styles.css";

const MeetingRoom = ({
  callId,
  onLeave,
  onSessionEnded,
  userId,
  hostId,
  jwt,
}) => {
  const [showAssistant, setShowAssistant] = useState(true);
  const [participantsOpen, setParticipantsOpen] = useState(false);
  const [currentHostId, setCurrentHostId] = useState(hostId || null);
  const { isLeaving, isEnding, startLeaving, startEnding, resetExitState } =
    useMeetingExit();

  const { call, error, hasLeftRef } = useMeetingCall(
    callId,
    userId,
    onLeave,
    onSessionEnded,
  );
  const {
    transcripts,
    connected,
    reconnecting,
    connectionError,
  } = useLiveTranscript(callId, jwt);
  const { isTranscriptOpen, toggleTranscript, closeTranscript } =
    useTranscriptPanel();
  const isHost = Boolean(
    currentHostId && userId && String(currentHostId) === String(userId),
  );

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
        if (data && typeof data.enabled === "boolean")
          setShowAssistant(data.enabled);
      })
      .catch((err) => {
        console.error("Assistant preference fetch failed:", err);
      });
  }, [callId, jwt]);

  const handleLeave = useCallback(() => {
    setParticipantsOpen(false);
    onLeave?.();
  }, [onLeave]);

  useEffect(() => {
    if (!callId) resetExitState();
  }, [callId, resetExitState]);

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
          <div className="w-full h-full flex flex-col">
            {isLeaving || isEnding ? (
              <MeetingExitLoading isLeaving={isLeaving} isEnding={isEnding} />
            ) : null}
            <ConnectionStateBanner />
            <RecordingBanner />
            <div className="flex-1 w-full h-full min-w-0 min-h-0">
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
                onLeave={handleLeave}
                callId={callId}
                jwt={jwt}
                hasLeftRef={hasLeftRef}
                transcripts={transcripts}
                transcriptConnected={connected}
                transcriptReconnecting={reconnecting}
                transcriptConnectionError={connectionError}
                isTranscriptOpen={isTranscriptOpen}
                onToggleTranscript={toggleTranscript}
                onCloseTranscript={closeTranscript}
                isLeaving={isLeaving}
                isEnding={isEnding}
                onStartLeaving={startLeaving}
                onStartEnding={startEnding}
                resetExitState={resetExitState}
              />
            </div>
          </div>
        </div>
      </StreamCall>
    </StreamTheme>
  );
};

export default MeetingRoom;
