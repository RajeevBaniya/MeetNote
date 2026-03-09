"use client";

import { useCallback } from "react";

const ScreenShareControl = ({ onToggle, disabled, isActive }) => {
  const handleClick = useCallback(() => {
    onToggle?.();
  }, [onToggle]);

  return (
    <button
      onClick={handleClick}
      disabled={disabled}
      className="flex items-center justify-center w-8 h-8 sm:w-9 sm:h-9 rounded-full transition-colors hover:bg-slate-700/50 disabled:opacity-50"
      title="Share Screen"
    >
      <div
        className={`w-full h-full rounded-full flex items-center justify-center ${
          isActive ? "bg-green-500" : "bg-slate-700"
        }`}
      >
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
  );
};

export default ScreenShareControl;
