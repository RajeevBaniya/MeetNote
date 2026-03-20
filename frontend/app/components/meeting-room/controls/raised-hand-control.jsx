"use client";

import { useCallback } from "react";
import { Hand } from "lucide-react";

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
        <Hand className="w-4 h-4 sm:w-5 sm:h-5" strokeWidth={1.5} />
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
        <Hand className="w-4 h-4 sm:w-5 sm:h-5" strokeWidth={1.5} />
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
