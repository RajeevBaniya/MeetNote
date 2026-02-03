"use client";

import { useCall, useCallStateHooks } from "@stream-io/video-react-sdk";
import { useState } from "react";

const MeetingControls = ({ onLeave }) => {
  const call = useCall();
  const { useMicrophoneState, useCameraState, useScreenShareState, useHasOngoingScreenShare } = useCallStateHooks();
  const { microphone, isMute: isMicMuted } = useMicrophoneState();
  const { camera, isMute: isCameraOff } = useCameraState();
  const { screenShare } = useScreenShareState();
  const isScreenSharing = useHasOngoingScreenShare();
  const [isToggling, setIsToggling] = useState(false);

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
      console.error("Failed to toggle screen share:", err);
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
        onClick={handleLeave}
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
    </div>
  );
};

export default MeetingControls;
