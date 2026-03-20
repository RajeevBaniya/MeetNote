"use client";

import { useCallback } from "react";
import { Captions } from "lucide-react";

const TranscriptButton = ({ onClick, isOpen = false }) => {
  const handleClick = useCallback(() => {
    onClick?.();
  }, [onClick]);

  return (
    <button
      type="button"
      onClick={handleClick}
      className={`flex items-center justify-center w-8 h-8 sm:w-9 sm:h-9 rounded-full transition-colors ${
        isOpen ? "bg-slate-600 hover:bg-slate-500" : "bg-gray-700 hover:bg-gray-600"
      } text-gray-300`}
      title={isOpen ? "Close transcript" : "Live transcript"}
    >
      <Captions className="w-4 h-4 sm:w-5 sm:h-5" strokeWidth={1.5} />
    </button>
  );
};

export default TranscriptButton;
