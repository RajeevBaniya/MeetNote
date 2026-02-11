"use client";

import { useCall, useCallStateHooks } from "@stream-io/video-react-sdk";
import { useState } from "react";
import LeaveConfirmModal from "./leave-confirm-modal";

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
  const { useMicrophoneState, useCameraState, useScreenShareState, useHasOngoingScreenShare, useIsCallRecordingInProgress } = useCallStateHooks();
  const { microphone, isMute: isMicMuted } = useMicrophoneState();
  const { camera, isMute: isCameraOff } = useCameraState();
  const { screenShare } = useScreenShareState();
  const isScreenSharing = useHasOngoingScreenShare();
  const isRecording = useIsCallRecordingInProgress();
  const [isToggling, setIsToggling] = useState(false);
  const [isEnding, setIsEnding] = useState(false);
  const [isRecordingAction, setIsRecordingAction] = useState(false);

  const handleToggleMic = async () => {
    if (!call || isToggling) return;
    setIsToggling(true);
    try {
      await microphone.toggle();
    } catch (err) {
      console.error("Failed to toggle microphone:", err);
    } finally {
      setIsToggling(false);
    }
  };

  const handleToggleCamera = async () => {
    if (!call || isToggling) return;
    setIsToggling(true);
    try {
      await camera.toggle();
    } catch (err) {
      console.error("Failed to toggle camera:", err);
    } finally {
      setIsToggling(false);
    }
  };

  const handleScreenShare = async () => {
    if (!call || !screenShare || isToggling) return;
    setIsToggling(true);
    try {
      await screenShare.toggle();
    } catch (err) {
      const msg = typeof err?.message === "string" ? err.message.toLowerCase() : "";
      const causeMsg = typeof err?.cause?.message === "string" ? err.cause.message.toLowerCase() : "";
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
  };

  const handleLeave = async () => {
    if (!call) return;
    try {
      await call.leave();
      onLeave?.();
    } catch (err) {
      console.error("Failed to leave call:", err);
      onLeave?.();
    }
  };

  const handleEndMeeting = async () => {
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
            // eslint-disable-next-line no-console
            console.error("Failed to end meeting:", err);
          }
        }
        onLeave?.();
      }
    } catch (err) {
      // eslint-disable-next-line no-console
      console.error("Failed to end meeting:", err);
    } finally {
      setIsEnding(false);
    }
  };

  const handleLeaveButtonClick = () => {
    if (isHost && onLeaveClick) {
      onLeaveClick();
    } else {
      handleLeave();
    }
  };

  const handleLeaveOnlyFromModal = () => {
    setShowLeaveConfirmModal?.(false);
    handleLeave();
  };

  const handleEndForEveryoneFromModal = () => {
    setShowLeaveConfirmModal?.(false);
    handleEndMeeting();
  };

  const handleStartRecording = async () => {
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
  };

  const handleStopRecording = async () => {
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
  };

  return (
    <div className="flex items-center gap-2 sm:gap-3">
      <button
        onClick={handleToggleMic}
        disabled={isToggling}
        className="flex items-center justify-center w-8 h-8 sm:w-9 sm:h-9 rounded-full transition-colors hover:bg-slate-700/50 disabled:opacity-50"
        title={isMicMuted ? "Unmute" : "Mute"}
      >
        <div
          className={`w-full h-full rounded-full flex items-center justify-center ${
            isMicMuted ? "bg-red-500" : "bg-slate-700"
          }`}
        >
          {isMicMuted ? (
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={2}
              stroke="currentColor"
              className="w-4 h-4 sm:w-5 sm:h-5 text-white"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
              />
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M5 5l14 14"
              />
            </svg>
          ) : (
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={2}
              stroke="currentColor"
              className="w-4 h-4 sm:w-5 sm:h-5 text-white"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
              />
            </svg>
          )}
        </div>
      </button>

      <button
        onClick={handleToggleCamera}
        disabled={isToggling}
        className="flex items-center justify-center w-8 h-8 sm:w-9 sm:h-9 rounded-full transition-colors hover:bg-slate-700/50 disabled:opacity-50"
        title={isCameraOff ? "Start Video" : "Stop Video"}
      >
        <div
          className={`w-full h-full rounded-full flex items-center justify-center ${
            isCameraOff ? "bg-red-500" : "bg-slate-700"
          }`}
        >
          {isCameraOff ? (
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={2}
              stroke="currentColor"
              className="w-4 h-4 sm:w-5 sm:h-5 text-white"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
              />
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M5 5l14 14"
              />
            </svg>
          ) : (
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={2}
              stroke="currentColor"
              className="w-4 h-4 sm:w-5 sm:h-5 text-white"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
              />
            </svg>
          )}
        </div>
      </button>

      <button
        onClick={handleScreenShare}
        disabled={isToggling}
        className="flex items-center justify-center w-8 h-8 sm:w-9 sm:h-9 rounded-full transition-colors hover:bg-slate-700/50 disabled:opacity-50"
        title="Share Screen"
      >
        <div className={`w-full h-full rounded-full flex items-center justify-center ${
          isScreenSharing ? "bg-green-500" : "bg-slate-700"
        }`}>
          <svg
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={2}
            stroke="currentColor"
            className="w-4 h-4 sm:w-5 sm:h-5 text-white"
            >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
            />
          </svg>
        </div>
      </button>

      <button
        type="button"
        onClick={() => onOpenParticipants?.()}
        className="relative flex items-center justify-center w-8 h-8 sm:w-9 sm:h-9 rounded-full transition-colors bg-gray-700 hover:bg-gray-600 text-gray-300"
        title="Participants"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          strokeWidth={1.5}
          stroke="currentColor"
          className="w-4 h-4 sm:w-5 sm:h-5"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M8.25 6.75h12M8.25 12h12m-12 5.25h12M3.75 6.75h.007v.008H3.75V6.75zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zM3.75 12h.007v.008H3.75V12zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm-.375 5.25h.007v.008H3.75v-.008zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z"
          />
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M6 6.75h.75v.75H6v-.75zM6 12h.75v.75H6V12zm0 5.25h.75v.75H6v-.75z"
          />
        </svg>
        {participantCount > 0 ? (
          <span className="absolute -top-0.5 -right-0.5 bg-slate-500 text-white text-[10px] font-bold rounded-full min-w-[18px] h-[18px] sm:min-w-[20px] sm:h-5 flex items-center justify-center px-1">
            {participantCount > 99 ? "99+" : participantCount}
          </span>
        ) : null}
      </button>

      <button
        type="button"
        onClick={() => onOpenChat?.()}
        className="relative flex items-center justify-center w-8 h-8 sm:w-9 sm:h-9 rounded-full transition-colors bg-gray-700 hover:bg-gray-600 text-gray-300"
        title="Chat"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          strokeWidth={1.5}
          stroke="currentColor"
          className="w-4 h-4 sm:w-5 sm:h-5"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M3 8.25c0-1.243 1.007-2.25 2.25-2.25h13.5A2.25 2.25 0 0 1 21 8.25v6a2.25 2.25 0 0 1-2.25 2.25H8.664a1.5 1.5 0 0 0-1.06.44l-2.22 2.22A.75.75 0 0 1 4 18.94v-2.44A2.25 2.25 0 0 1 3 14.25z"
          />
        </svg>
        {chatUnreadCount > 0 ? (
          <span className="absolute -top-0.5 -right-0.5 bg-red-500 text-white text-[10px] font-bold rounded-full min-w-[18px] h-[18px] sm:min-w-[20px] sm:h-5 flex items-center justify-center px-1">
            {chatUnreadCount > 99 ? "99+" : chatUnreadCount}
          </span>
        ) : null}
      </button>

      {!isHost && (onRaiseHand || onLowerHand) ? (
        <button
          type="button"
          onClick={isHandRaised ? onLowerHand : onRaiseHand}
          className={`flex items-center justify-center w-8 h-8 sm:w-9 sm:h-9 rounded-full transition-colors ${
            isHandRaised ? "bg-amber-500 hover:bg-amber-600" : "bg-gray-700 hover:bg-gray-600"
          } text-white`}
          title={isHandRaised ? "Lower hand" : "Raise hand"}
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={1.5}
            stroke="currentColor"
            className="w-4 h-4 sm:w-5 sm:h-5"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M6.633 10.25c.806 0 1.533-.446 2.031-1.08a9.041 9.041 0 0 1 2.861-2.4c.723-.384 1.35-.956 1.653-1.715a4.498 4.498 0 0 0 .322-1.672V2.75a.75.75 0 0 1 1.5 0v2.716a5.499 5.499 0 0 1-.43 2.103 5.99 5.99 0 0 1 2.43 2.103 5.499 5.499 0 0 1-.43-2.103V2.75a.75.75 0 0 1 1.5 0v2.716a5.499 5.499 0 0 1-.43 2.103 5.99 5.99 0 0 1 2.43 2.103 5.499 5.499 0 0 1-.43-2.103V2.75a.75.75 0 0 1 1.5 0v6.375a4.5 4.5 0 0 1-1.5 3.375 9 9 0 0 1-6.939 2.437A9.001 9.001 0 0 1 6.633 10.25z"
            />
          </svg>
        </button>
      ) : null}

      {isHost && onOpenRaisedHands ? (
        <button
          type="button"
          onClick={onOpenRaisedHands}
          className="relative flex items-center justify-center w-8 h-8 sm:w-9 sm:h-9 rounded-full transition-colors bg-gray-700 hover:bg-gray-600 text-amber-400"
          title="Raised hands"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={1.5}
            stroke="currentColor"
            className="w-4 h-4 sm:w-5 sm:h-5"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M6.633 10.25c.806 0 1.533-.446 2.031-1.08a9.041 9.041 0 0 1 2.861-2.4c.723-.384 1.35-.956 1.653-1.715a4.498 4.498 0 0 0 .322-1.672V2.75a.75.75 0 0 1 1.5 0v2.716a5.499 5.499 0 0 1-.43 2.103 5.99 5.99 0 0 1 2.43 2.103 5.499 5.499 0 0 1-.43-2.103V2.75a.75.75 0 0 1 1.5 0v6.375a4.5 4.5 0 0 1-1.5 3.375 9 9 0 0 1-6.939 2.437A9.001 9.001 0 0 1 6.633 10.25z"
            />
          </svg>
          {raisedHandCount > 0 ? (
            <span className="absolute -top-0.5 -right-0.5 bg-amber-500 text-white text-[10px] font-bold rounded-full min-w-[18px] h-[18px] sm:min-w-[20px] sm:h-5 flex items-center justify-center px-1">
              {raisedHandCount > 99 ? "99+" : raisedHandCount}
            </span>
          ) : null}
        </button>
      ) : null}

      {isHost && callId && jwt ? (
        isRecording ? (
          <button
            type="button"
            onClick={handleStopRecording}
            disabled={isRecordingAction}
            className="flex items-center justify-center w-8 h-8 sm:w-9 sm:h-9 rounded-full transition-colors bg-red-600 hover:bg-red-700 text-white disabled:opacity-50"
            title="Stop recording"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="currentColor"
              viewBox="0 0 24 24"
              className="w-4 h-4 sm:w-5 sm:h-5"
            >
              <rect x="6" y="6" width="12" height="12" rx="1" />
            </svg>
          </button>
        ) : (
          <button
            type="button"
            onClick={handleStartRecording}
            disabled={isRecordingAction}
            className="flex items-center justify-center w-8 h-8 sm:w-9 sm:h-9 rounded-full transition-colors bg-gray-700 hover:bg-gray-600 text-white disabled:opacity-50"
            title="Start recording"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="currentColor"
              viewBox="0 0 24 24"
              className="w-4 h-4 sm:w-5 sm:h-5"
            >
              <circle cx="12" cy="12" r="6" />
            </svg>
          </button>
        )
      ) : null}

      {isHost && onEndMeeting ? (
        <button
          onClick={handleEndMeeting}
          disabled={isEnding}
          className="flex items-center justify-center w-8 h-8 sm:w-9 sm:h-9 rounded-full transition-colors hover:bg-red-600/90 disabled:opacity-50"
          title="End meeting"
        >
          <div className="w-full h-full rounded-full flex items-center justify-center bg-red-600">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={2}
              stroke="currentColor"
              className="w-4 h-4 sm:w-5 sm:h-5 text-white"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </div>
        </button>
      ) : null}
      <button
        onClick={handleLeaveButtonClick}
        className="flex items-center justify-center w-8 h-8 sm:w-9 sm:h-9 rounded-full transition-colors hover:bg-red-500/20 disabled:opacity-50"
        title="Leave Meeting"
      >
        <div className="w-full h-full rounded-full flex items-center justify-center bg-red-500">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={2}
            stroke="currentColor"
            className="w-4 h-4 sm:w-5 sm:h-5 text-white rotate-[135deg]"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"
            />
          </svg>
        </div>
      </button>

      {showLeaveConfirmModal ? (
        <LeaveConfirmModal
          onClose={() => setShowLeaveConfirmModal?.(false)}
          onLeaveOnly={handleLeaveOnlyFromModal}
          onEndForEveryone={handleEndForEveryoneFromModal}
        />
      ) : null}
    </div>
  );
};

export default MeetingControls;
