"use client";

import { useCallback } from "react";

const HAND_ICON_PATH =
  "M6.633 10.25c.806 0 1.533-.446 2.031-1.08a9.041 9.041 0 0 1 2.861-2.4c.723-.384 1.35-.956 1.653-1.715a4.498 4.498 0 0 0 .322-1.672V2.75a.75.75 0 0 1 1.5 0v2.716a5.499 5.499 0 0 1-.43 2.103 5.99 5.99 0 0 1 2.43 2.103 5.499 5.499 0 0 1-.43-2.103V2.75a.75.75 0 0 1 1.5 0v2.716a5.499 5.499 0 0 1-.43 2.103 5.99 5.99 0 0 1 2.43 2.103 5.499 5.499 0 0 1-.43-2.103V2.75a.75.75 0 0 1 1.5 0v6.375a4.5 4.5 0 0 1-1.5 3.375 9 9 0 0 1-6.939 2.437A9.001 9.001 0 0 1 6.633 10.25z";

const RaisedHandControl = ({
  isHost,
  onOpenRaisedHands,
  onRaiseHand,
  onLowerHand,
  isHandRaised = false,
  raisedHandCount = 0,
}) => {
  const handleParticipantClick = useCallback(() => {
    if (isHandRaised) {
      onLowerHand?.();
    } else {
      onRaiseHand?.();
    }
  }, [isHandRaised, onLowerHand, onRaiseHand]);

  if (!isHost && (onRaiseHand || onLowerHand)) {
    return (
      <button
        type="button"
        onClick={handleParticipantClick}
        className={`flex items-center justify-center w-8 h-8 sm:w-9 sm:h-9 rounded-full transition-colors ${
          isHandRaised
            ? "bg-amber-500 hover:bg-amber-600"
            : "bg-gray-700 hover:bg-gray-600"
        } text-white`}
        title={isHandRaised ? "Lower hand" : "Raise hand"}
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          strokeWidth={1.5}
          stroke="currentColor"
          className="w-4 h-4 sm:w-5 sm:h-5"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d={HAND_ICON_PATH} />
        </svg>
      </button>
    );
  }

  if (isHost && onOpenRaisedHands) {
    return (
      <button
        type="button"
        onClick={onOpenRaisedHands}
        className="relative flex items-center justify-center w-8 h-8 sm:w-9 sm:h-9 rounded-full transition-colors bg-gray-700 hover:bg-gray-600 text-amber-400"
        title="Raised hands"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          strokeWidth={1.5}
          stroke="currentColor"
          className="w-4 h-4 sm:w-5 sm:h-5"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d={HAND_ICON_PATH} />
        </svg>
        {raisedHandCount > 0 ? (
          <span className="absolute -top-0.5 -right-0.5 bg-amber-500 text-white text-[10px] font-bold rounded-full min-w-[18px] h-[18px] sm:min-w-[20px] sm:h-5 flex items-center justify-center px-1">
            {raisedHandCount > 99 ? "99+" : raisedHandCount}
          </span>
        ) : null}
      </button>
    );
  }

  return null;
};

export default RaisedHandControl;
