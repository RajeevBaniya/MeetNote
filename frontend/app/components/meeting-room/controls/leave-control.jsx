"use client";

import { useCallback } from "react";

import LeaveConfirmModal from "../leave-confirm-modal";

const LeaveControl = ({
  onLeaveClick,
  onLeaveOnly,
  onEndForEveryone,
  showLeaveConfirmModal,
  onCloseLeaveModal,
  isHost,
}) => {
  const handleLeaveButtonClick = useCallback(() => {
    if (isHost && onLeaveClick) {
      onLeaveClick();
    } else {
      onLeaveOnly?.();
    }
  }, [isHost, onLeaveClick, onLeaveOnly]);

  return (
    <>
      <button
        onClick={handleLeaveButtonClick}
        className="flex items-center justify-center w-8 h-8 sm:w-9 sm:h-9 rounded-full transition-colors hover:bg-red-500/20 disabled:opacity-50"
        title="Leave Meeting"
      >
        <div className="w-full h-full rounded-full flex items-center justify-center bg-red-500">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={2}
            stroke="currentColor"
            className="w-4 h-4 sm:w-5 sm:h-5 text-white rotate-[135deg]"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"
            />
          </svg>
        </div>
      </button>

      {showLeaveConfirmModal ? (
        <LeaveConfirmModal
          onClose={onCloseLeaveModal}
          onLeaveOnly={onLeaveOnly}
          onEndForEveryone={onEndForEveryone}
        />
      ) : null}
    </>
  );
};

export default LeaveControl;
