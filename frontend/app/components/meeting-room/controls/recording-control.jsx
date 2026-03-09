"use client";

import { useCallback } from "react";

const RecordingControl = ({
  isHost,
  callId,
  jwt,
  isRecording,
  isRecordingAction,
  onStartRecording,
  onStopRecording,
}) => {
  const handleStart = useCallback(
    (e) => {
      e?.preventDefault?.();
      onStartRecording?.();
    },
    [onStartRecording]
  );

  const handleStop = useCallback(
    (e) => {
      e?.preventDefault?.();
      onStopRecording?.();
    },
    [onStopRecording]
  );

  if (!isHost || !callId || !jwt) return null;

  if (isRecording) {
    return (
      <button
        type="button"
        onClick={handleStop}
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
    );
  }

  return (
    <button
      type="button"
      onClick={handleStart}
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
  );
};

export default RecordingControl;
