"use client";

import { formatTime } from "@/app/lib/utils/format-time";

import { useRecording } from "../recording/recording-context";

const RecordingBanner = () => {
  const rec = useRecording();
  const isRecording = Boolean(rec?.isRecording);
  const elapsed = Number.isFinite(rec?.elapsed) ? rec.elapsed : 0;

  if (!isRecording) {
    return null;
  }

  return (
    <div className="absolute top-0 left-0 right-0 z-40 flex items-center justify-center gap-2 py-2 px-4 bg-red-600/90 text-white text-sm font-medium">
      <div className="w-3 h-3 rounded-full bg-white animate-pulse" />
      <span>Recording (saved locally)</span>
      <span>{formatTime(elapsed)}</span>
    </div>
  );
};

export default RecordingBanner;
