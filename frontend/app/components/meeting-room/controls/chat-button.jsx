"use client";

import { useCallback } from "react";

const ChatButton = ({ onClick, unreadCount = 0 }) => {
  const handleClick = useCallback(() => {
    onClick?.();
  }, [onClick]);

  return (
    <button
      type="button"
      onClick={handleClick}
      className="relative flex items-center justify-center w-8 h-8 sm:w-9 sm:h-9 rounded-full transition-colors bg-gray-700 hover:bg-gray-600 text-gray-300"
      title="Chat"
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
          d="M3 8.25c0-1.243 1.007-2.25 2.25-2.25h13.5A2.25 2.25 0 0 1 21 8.25v6a2.25 2.25 0 0 1-2.25 2.25H8.664a1.5 1.5 0 0 0-1.06.44l-2.22 2.22A.75.75 0 0 1 4 18.94v-2.44A2.25 2.25 0 0 1 3 14.25z"
        />
      </svg>
      {unreadCount > 0 ? (
        <span className="absolute -top-0.5 -right-0.5 bg-red-500 text-white text-[10px] font-bold rounded-full min-w-[18px] h-[18px] sm:min-w-[20px] sm:h-5 flex items-center justify-center px-1">
          {unreadCount > 99 ? "99+" : unreadCount}
        </span>
      ) : null}
    </button>
  );
};

export default ChatButton;
