"use client";

import { useCallback } from "react";

const EndMeetingControl = ({ isHost, onEndMeeting, disabled }) => {
  const handleClick = useCallback(() => {
    onEndMeeting?.();
  }, [onEndMeeting]);

  if (!isHost || !onEndMeeting) return null;

  return (
    <button
      onClick={handleClick}
      disabled={disabled}
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
  );
};

export default EndMeetingControl;
