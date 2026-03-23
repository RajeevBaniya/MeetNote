"use client";

import { Loader2 } from "lucide-react";

const getExitMessage = ({ isEnding, isLeaving }) => {
  if (isEnding) return "Ending meeting...";
  if (isLeaving) return "Leaving meeting...";
  return "";
};

const MeetingExitLoading = ({ isEnding = false, isLeaving = false }) => {
  const message = getExitMessage({ isEnding, isLeaving });
  if (!message) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
      <div className="flex flex-col items-center gap-3 rounded-xl border border-emerald-500/30 bg-slate-900/70 px-6 py-5 shadow-2xl">
        <Loader2 className="h-7 w-7 animate-spin text-emerald-400" />
        <p className="text-sm font-medium text-slate-100">{message}</p>
      </div>
    </div>
  );
};

export default MeetingExitLoading;
