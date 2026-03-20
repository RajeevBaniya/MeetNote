"use client";

import { useCallback } from "react";
import { Users } from "lucide-react";

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
      <Users className="w-4 h-4 sm:w-5 sm:h-5" strokeWidth={1.5} />
      {count > 0 ? (
        <span className="absolute -top-0.5 -right-0.5 bg-slate-500 text-white text-[10px] font-bold rounded-full min-w-[18px] h-[18px] sm:min-w-[20px] sm:h-5 flex items-center justify-center px-1">
          {count > 99 ? "99+" : count}
        </span>
      ) : null}
    </button>
  );
};

export default ParticipantsButton;
