"use client";

import { useState, useCallback } from "react";
import { useCall, useCallStateHooks } from "@stream-io/video-react-sdk";

import MicControl from "./controls/mic-control";
import CameraControl from "./controls/camera-control";
import ScreenShareControl from "./controls/screen-share-control";
import ParticipantsButton from "./controls/participants-button";
import ChatButton from "./controls/chat-button";
import RaisedHandControl from "./controls/raised-hand-control";
import RecordingControl from "./controls/recording-control";
import EndMeetingControl from "./controls/end-meeting-control";
import LeaveControl from "./controls/leave-control";

const MeetingControls = ({
  onLeave,
  onOpenParticipants,
  participantCount = 0,
  isHost = false,
  onEndMeeting,
  raisedHandCount = 0,
  onOpenRaisedHands,
  onRaiseHand,
  onLowerHand,
  isHandRaised = false,
  onLeaveClick,
  showLeaveConfirmModal = false,
  setShowLeaveConfirmModal,
  callId,
  jwt,
  onOpenChat,
  chatUnreadCount = 0,
}) => {
  const call = useCall();
  const {
    useMicrophoneState,
    useCameraState,
    useScreenShareState,
    useHasOngoingScreenShare,
    useIsCallRecordingInProgress,
  } = useCallStateHooks();
  const { microphone, isMute: isMicMuted } = useMicrophoneState();
  const { camera, isMute: isCameraOff } = useCameraState();
  const { screenShare } = useScreenShareState();
  const isScreenSharing = useHasOngoingScreenShare();
  const isRecording = useIsCallRecordingInProgress();
  const [isToggling, setIsToggling] = useState(false);
  const [isEnding, setIsEnding] = useState(false);
  const [isRecordingAction, setIsRecordingAction] = useState(false);

  const handleToggleMic = useCallback(async () => {
    if (!call || isToggling) return;
    setIsToggling(true);
    try {
      await microphone.toggle();
    } catch (err) {
      console.error("Failed to toggle microphone:", err);
    } finally {
      setIsToggling(false);
    }
  }, [call, isToggling, microphone]);

  const handleToggleCamera = useCallback(async () => {
    if (!call || isToggling) return;
    setIsToggling(true);
    try {
      await camera.toggle();
    } catch (err) {
      console.error("Failed to toggle camera:", err);
    } finally {
      setIsToggling(false);
    }
  }, [call, isToggling, camera]);

  const handleScreenShare = useCallback(async () => {
    if (!call || !screenShare || isToggling) return;
    setIsToggling(true);
    try {
      await screenShare.toggle();
    } catch (err) {
      const msg = typeof err?.message === "string" ? err.message.toLowerCase() : "";
      const causeMsg =
        typeof err?.cause?.message === "string" ? err.cause.message.toLowerCase() : "";
      const isCancelledOrDenied =
        err?.name === "NotAllowedError" ||
        err?.cause?.name === "NotAllowedError" ||
        msg.includes("permission denied") ||
        causeMsg.includes("permission denied");
      if (!isCancelledOrDenied) {
        console.error("Failed to toggle screen share:", err);
      }
    } finally {
      setIsToggling(false);
    }
  }, [call, screenShare, isToggling]);

  const handleLeave = useCallback(async () => {
    if (!call) return;
    try {
      await call.leave();
      onLeave?.();
    } catch (err) {
      console.error("Failed to leave call:", err);
      onLeave?.();
    }
  }, [call, onLeave]);

  const handleEndMeeting = useCallback(async () => {
    if (!call || !onEndMeeting || isEnding) return;
    setIsEnding(true);
    try {
      const ok = await onEndMeeting();
      if (ok) {
        try {
          await call.leave();
        } catch (err) {
          const msg = typeof err?.message === "string" ? err.message.toLowerCase() : "";
          if (!msg.includes("already been left")) {
            console.error("Failed to end meeting:", err);
          }
        }
        onLeave?.();
      }
    } catch (err) {
      console.error("Failed to end meeting:", err);
    } finally {
      setIsEnding(false);
    }
  }, [call, onEndMeeting, onLeave]);

  const handleCloseLeaveModal = useCallback(() => {
    setShowLeaveConfirmModal?.(false);
  }, [setShowLeaveConfirmModal]);

  const handleStartRecording = useCallback(async () => {
    if (!callId || !jwt || isRecordingAction) return;
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    if (!apiUrl) return;
    setIsRecordingAction(true);
    try {
      const res = await fetch(`${apiUrl}/meetings/${callId}/recording/start`, {
        method: "POST",
        headers: { Authorization: `Bearer ${jwt}` },
      });
      if (!res.ok) {
        console.error("Failed to start recording:", res.status);
      }
    } catch (err) {
      console.error("Failed to start recording:", err);
    } finally {
      setIsRecordingAction(false);
    }
  }, [callId, jwt, isRecordingAction]);

  const handleStopRecording = useCallback(async () => {
    if (!callId || !jwt || isRecordingAction) return;
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    if (!apiUrl) return;
    setIsRecordingAction(true);
    try {
      const res = await fetch(`${apiUrl}/meetings/${callId}/recording/stop`, {
        method: "POST",
        headers: { Authorization: `Bearer ${jwt}` },
      });
      if (!res.ok) {
        console.error("Failed to stop recording:", res.status);
      }
    } catch (err) {
      console.error("Failed to stop recording:", err);
    } finally {
      setIsRecordingAction(false);
    }
  }, [callId, jwt, isRecordingAction]);

  return (
    <div className="flex items-center gap-2 sm:gap-3">
      <MicControl
        onToggle={handleToggleMic}
        disabled={isToggling}
        isMuted={isMicMuted}
      />
      <CameraControl
        onToggle={handleToggleCamera}
        disabled={isToggling}
        isOff={isCameraOff}
      />
      <ScreenShareControl
        onToggle={handleScreenShare}
        disabled={isToggling}
        isActive={isScreenSharing}
      />
      <ParticipantsButton onClick={onOpenParticipants} count={participantCount} />
      <ChatButton onClick={onOpenChat} unreadCount={chatUnreadCount} />
      <RaisedHandControl
        isHost={isHost}
        onOpenRaisedHands={onOpenRaisedHands}
        onRaiseHand={onRaiseHand}
        onLowerHand={onLowerHand}
        isHandRaised={isHandRaised}
        raisedHandCount={raisedHandCount}
      />
      <RecordingControl
        isHost={isHost}
        callId={callId}
        jwt={jwt}
        isRecording={isRecording}
        isRecordingAction={isRecordingAction}
        onStartRecording={handleStartRecording}
        onStopRecording={handleStopRecording}
      />
      <EndMeetingControl
        isHost={isHost}
        onEndMeeting={handleEndMeeting}
        disabled={isEnding}
      />
      <LeaveControl
        onLeaveClick={onLeaveClick}
        onLeaveOnly={handleLeave}
        onEndForEveryone={handleEndMeeting}
        showLeaveConfirmModal={showLeaveConfirmModal}
        onCloseLeaveModal={handleCloseLeaveModal}
        isHost={isHost}
      />
    </div>
  );
};

export default MeetingControls;
