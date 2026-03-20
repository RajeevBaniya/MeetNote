"use client";

import { useCallback } from "react";
import { Mic, MicOff } from "lucide-react";

const MicControl = ({ onToggle, disabled, isMuted }) => {
  const handleClick = useCallback(() => {
    onToggle?.();
  }, [onToggle]);

  const iconClass = "w-4 h-4 sm:w-5 sm:h-5 text-white";
  const Icon = isMuted ? MicOff : Mic;

  return (
    <button
      onClick={handleClick}
      disabled={disabled}
      className="flex items-center justify-center w-8 h-8 sm:w-9 sm:h-9 rounded-full transition-colors hover:bg-slate-700/50 disabled:opacity-50"
      title={isMuted ? "Unmute" : "Mute"}
    >
      <div
        className={`w-full h-full rounded-full flex items-center justify-center ${
          isMuted ? "bg-red-500" : "bg-slate-700"
        }`}
      >
        <Icon className={iconClass} strokeWidth={2} />
      </div>
    </button>
  );
};

export default MicControl;
