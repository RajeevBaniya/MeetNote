"use client";

import { useCallback } from "react";
import { MessageSquare } from "lucide-react";

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
      <MessageSquare className="w-4 h-4 sm:w-5 sm:h-5" strokeWidth={1.5} />
      {unreadCount > 0 ? (
        <span className="absolute -top-0.5 -right-0.5 bg-red-500 text-white text-[10px] font-bold rounded-full min-w-[18px] h-[18px] sm:min-w-[20px] sm:h-5 flex items-center justify-center px-1">
          {unreadCount > 99 ? "99+" : unreadCount}
        </span>
      ) : null}
    </button>
  );
};

export default ChatButton;
