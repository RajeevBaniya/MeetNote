"use client";

import { useCallback } from "react";

const ParticipantsButton = ({ onClick, count = 0 }) => {
  const handleClick = useCallback(() => {
    onClick?.();
  }, [onClick]);

  return (
    <button
      type="button"
      onClick={handleClick}
      className="relative flex items-center justify-center w-8 h-8 sm:w-9 sm:h-9 rounded-full transition-colors bg-gray-700 hover:bg-gray-600 text-gray-300"
      title="Participants"
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
        strokeWidth={1.5}
        stroke="currentColor"
        className="w-4 h-4 sm:w-5 sm:h-5"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M8.25 6.75h12M8.25 12h12m-12 5.25h12M3.75 6.75h.007v.008H3.75V6.75zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zM3.75 12h.007v.008H3.75V12zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm-.375 5.25h.007v.008H3.75v-.008zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z"
        />
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M6 6.75h.75v.75H6v-.75zM6 12h.75v.75H6V12zm0 5.25h.75v.75H6v-.75z"
        />
      </svg>
      {count > 0 ? (
        <span className="absolute -top-0.5 -right-0.5 bg-slate-500 text-white text-[10px] font-bold rounded-full min-w-[18px] h-[18px] sm:min-w-[20px] sm:h-5 flex items-center justify-center px-1">
          {count > 99 ? "99+" : count}
        </span>
      ) : null}
    </button>
  );
};

export default ParticipantsButton;
