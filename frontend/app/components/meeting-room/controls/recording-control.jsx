"use client";

import { useCallback } from "react";
import { Disc, DiscAlbum } from "lucide-react";

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

  const iconClass = "w-4 h-4 sm:w-5 sm:h-5";

  if (isRecording) {
    return (
      <button
        type="button"
        onClick={handleStop}
        disabled={isRecordingAction}
        className="flex items-center justify-center w-8 h-8 sm:w-9 sm:h-9 rounded-full transition-colors bg-red-600 hover:bg-red-700 text-white disabled:opacity-50"
        title="Stop recording"
      >
        <Disc className={iconClass} />
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
      <DiscAlbum className={iconClass} />
    </button>
  );
};

export default RecordingControl;
