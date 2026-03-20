"use client";

import { useCallback } from "react";
import { MonitorUp, MonitorX } from "lucide-react";

const ScreenShareControl = ({ onToggle, disabled, isActive }) => {
  const handleClick = useCallback(() => {
    onToggle?.();
  }, [onToggle]);

  const iconClass = "w-4 h-4 sm:w-5 sm:h-5 text-white";
  const Icon = isActive ? MonitorX : MonitorUp;

  return (
    <button
      onClick={handleClick}
      disabled={disabled}
      className="flex items-center justify-center w-8 h-8 sm:w-9 sm:h-9 rounded-full transition-colors hover:bg-slate-700/50 disabled:opacity-50"
      title={isActive ? "Stop sharing" : "Share Screen"}
    >
      <div
        className={`w-full h-full rounded-full flex items-center justify-center ${
          isActive ? "bg-green-500" : "bg-slate-700"
        }`}
      >
        <Icon className={iconClass} strokeWidth={2} />
      </div>
    </button>
  );
};

export default ScreenShareControl;
