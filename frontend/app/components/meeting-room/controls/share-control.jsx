"use client";

import { useCallback } from "react";

const ShareControl = ({ onClick, disabled = false }) => {
  const handleClick = useCallback(() => {
    if (!disabled) onClick?.();
  }, [onClick, disabled]);

  return (
    <button
      type="button"
      onClick={handleClick}
      disabled={disabled}
      className="flex items-center justify-center w-8 h-8 sm:w-9 sm:h-9 rounded-full transition-colors bg-gray-700 hover:bg-gray-600 text-gray-300 disabled:opacity-50"
      title="Share Meeting"
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
          d="M7.217 10.907a2.25 2.25 0 100 2.186m0-2.186c.18.324.283.696.283 1.093s-.103.77-.283 1.093m0-2.186l6.586-3.908m-6.586 3.908l-3.172 1.882m0 0l-3.172-1.882m3.172 1.882V18m0 0l-3.172-1.882m3.172 1.882l6.586 3.908m-6.586-3.908l-3.172-1.882m0 0l3.172-1.882"
        />
      </svg>
    </button>
  );
};

export default ShareControl;
