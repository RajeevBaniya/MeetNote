"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useCall, useCallStateHooks } from "@stream-io/video-react-sdk";

import CameraControl from "../controls/camera-control";
import ChatButton from "../controls/chat-button";
import EndMeetingControl from "../controls/end-meeting-control";
import LeaveControl from "../controls/leave-control";
import MicControl from "../controls/mic-control";
import ParticipantsButton from "../controls/participants-button";
import RaisedHandControl from "../controls/raised-hand-control";
import RecordingControl from "../controls/recording-control";
import ScreenShareControl from "../controls/screen-share-control";
import ShareControl from "../controls/share-control";
import TranscriptButton from "../controls/transcript-button";
import ConfirmModal from "../../common/confirm-modal";
import { useRecording } from "../recording/recording-context";

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
  onOpenShare,
  onToggleTranscript,
  isTranscriptOpen = false,
  isLeaving = false,
  isEnding: isExitEnding = false,
  onStartLeaving,
  onStartEnding,
  resetExitState,
}) => {
  const call = useCall();
  const {
    useMicrophoneState,
    useCameraState,
    useScreenShareState,
    useHasOngoingScreenShare,
  } = useCallStateHooks();
  const { microphone, isMute: isMicMuted } = useMicrophoneState();
  const { camera, isMute: isCameraOff } = useCameraState();
  const { screenShare } = useScreenShareState();
  const isScreenSharing = useHasOngoingScreenShare();
  const [isToggling, setIsToggling] = useState(false);
  const [isEnding, setIsEnding] = useState(false);
  const [exitRequested, setExitRequested] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [pendingAction, setPendingAction] = useState(null);
  const pendingActionRef = useRef(null);
  const rec = useRecording();
  const isRecording = Boolean(rec?.isRecording);
  const isRecordingAction = Boolean(rec?.isRecordingAction);

  const isExiting = Boolean(isLeaving || isExitEnding || exitRequested);

  const handleToggleMic = useCallback(async () => {
    if (!call || isToggling || isExiting) return;
    setIsToggling(true);
    try {
      await microphone.toggle();
    } catch (err) {
      console.error("Failed to toggle microphone:", err);
    } finally {
      setIsToggling(false);
    }
  }, [call, isExiting, isToggling, microphone]);

  const handleToggleCamera = useCallback(async () => {
    if (!call || isToggling || isExiting) return;
    setIsToggling(true);
    try {
      await camera.toggle();
    } catch (err) {
      console.error("Failed to toggle camera:", err);
    } finally {
      setIsToggling(false);
    }
  }, [call, camera, isExiting, isToggling]);

  const handleScreenShare = useCallback(async () => {
    if (!call || !screenShare || isToggling || isExiting) return;
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
  }, [call, isExiting, isToggling, screenShare]);

  const proceedLeave = useCallback(async () => {
    if (!call || isExiting) return;
    setExitRequested(true);
    onStartLeaving?.();
    try {
      await call.leave();
      onLeave?.();
    } catch (err) {
      console.error("Failed to leave call:", err);
      resetExitState?.();
      setExitRequested(false);
    }
  }, [call, isExiting, onLeave, onStartLeaving, resetExitState]);

  const proceedEndMeeting = useCallback(async () => {
    if (!call || !onEndMeeting || isEnding || isExiting) return;
    setExitRequested(true);
    onStartEnding?.();
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
      resetExitState?.();
      setExitRequested(false);
    } finally {
      if (!call) {
        resetExitState?.();
        setExitRequested(false);
      }
      setIsEnding(false);
    }
  }, [
    call,
    isEnding,
    isExiting,
    onEndMeeting,
    onLeave,
    onStartEnding,
    resetExitState,
  ]);

  const openRecordingConfirm = useCallback((action) => {
    pendingActionRef.current = action;
    setPendingAction(action);
    setConfirmOpen(true);
  }, []);

  const handleLeave = useCallback(async () => {
    if (isRecording) {
      openRecordingConfirm("leave");
      return;
    }
    await proceedLeave();
  }, [isRecording, openRecordingConfirm, proceedLeave]);

  const handleEndMeeting = useCallback(async () => {
    if (isRecording) {
      openRecordingConfirm("end");
      return;
    }
    await proceedEndMeeting();
  }, [isRecording, openRecordingConfirm, proceedEndMeeting]);

  const handleConfirmCancel = useCallback(() => {
    setConfirmOpen(false);
    setPendingAction(null);
    pendingActionRef.current = null;
  }, []);

  const handleConfirmStopRecording = useCallback(() => {
    const action = pendingActionRef.current;
    pendingActionRef.current = null;
    setPendingAction(null);
    setConfirmOpen(false);
    const cb = () => {
      if (action === "leave") {
        proceedLeave();
        return;
      }
      if (action === "end") {
        proceedEndMeeting();
      }
    };
    if (typeof rec?.stopRecordingWithCallback === "function") {
      rec.stopRecordingWithCallback(cb);
      return;
    }
    rec?.stopRecording?.();
  }, [proceedEndMeeting, proceedLeave, rec]);

  const handleCloseLeaveModal = useCallback(() => {
    setShowLeaveConfirmModal?.(false);
  }, [setShowLeaveConfirmModal]);

  const handleStartRecording = useCallback(() => {
    if (!isHost || !callId || !jwt) return;
    rec?.startRecording?.();
  }, [callId, isHost, jwt, rec]);

  const handleStopRecording = useCallback(() => {
    if (!isHost || !callId || !jwt) return;
    rec?.stopRecording?.();
  }, [callId, isHost, jwt, rec]);

  return (
    <>
      <ConfirmModal
        isOpen={confirmOpen}
        title="Recording in progress"
        message="Stop recording before leaving?"
        onConfirm={handleConfirmStopRecording}
        onCancel={handleConfirmCancel}
        confirmLabel="Stop Recording"
        cancelLabel="Cancel"
      />
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
      {onToggleTranscript ? (
        <TranscriptButton
          onClick={onToggleTranscript}
          isOpen={isTranscriptOpen}
        />
      ) : null}
      {isHost && onOpenShare ? (
        <ShareControl onClick={onOpenShare} />
      ) : null}
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
        disabled={isEnding || isExiting}
      />
      <LeaveControl
        onLeaveClick={onLeaveClick}
        onLeaveOnly={handleLeave}
        onEndForEveryone={handleEndMeeting}
        showLeaveConfirmModal={showLeaveConfirmModal}
        onCloseLeaveModal={handleCloseLeaveModal}
        isHost={isHost}
        disabled={isExiting}
      />
      </div>
    </>
  );
};

export default MeetingControls;
