"use client";

import { useCallStateHooks } from "@stream-io/video-react-sdk";

function RecordingBanner() {
  const { useIsCallRecordingInProgress } = useCallStateHooks();
  const isRecording = useIsCallRecordingInProgress();

  if (!isRecording) {
    return null;
  }

  return (
    <div className="absolute top-0 left-0 right-0 z-40 flex items-center justify-center gap-2 py-2 px-4 bg-red-600/90 text-white text-sm font-medium">
      <div className="w-3 h-3 rounded-full bg-white animate-pulse" />
      Recording
    </div>
  );
}

export default RecordingBanner;
