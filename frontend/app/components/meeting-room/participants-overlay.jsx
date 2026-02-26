"use client";

import { useEffect } from "react";
import ParticipantsPanel from "./participants-panel";

const ParticipantsOverlay = ({
  onClose,
  currentUserId,
  isHost,
  callId,
  jwt,
  raisedHandUserIds = [],
}) => {
  useEffect(() => {
    const handleKeyDown = (event) => {
      if (event.key === "Escape") {
        onClose?.();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 flex items-stretch justify-end bg-black/50 backdrop-blur-sm animate-fadeIn">
      <div className="h-full w-full max-w-[90vw] sm:max-w-md md:max-w-lg lg:max-w-xl translate-x-0 transform bg-gradient-to-b from-slate-900 to-slate-950 border-l border-slate-700/80 shadow-2xl flex flex-col animate-slideInRight">
        <div className="flex items-center justify-between px-4 py-4 sm:px-5 sm:py-4 border-b border-slate-700/80 bg-slate-900/80 backdrop-blur-md shrink-0">
          <div className="flex items-center gap-2">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={2}
              stroke="currentColor"
              className="w-5 h-5 text-emerald-400"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z"
              />
            </svg>
            <h2 className="text-base font-semibold text-slate-100 sm:text-lg">
              Participants
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-slate-100 hover:bg-slate-800 rounded-full p-1.5 transition-all duration-200"
            aria-label="Close participants"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={2.5}
              stroke="currentColor"
              className="w-5 h-5"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>
        <ParticipantsPanel
          embedded
          onClose={onClose}
          currentUserId={currentUserId}
          isHost={isHost}
          callId={callId}
          jwt={jwt}
          raisedHandUserIds={raisedHandUserIds}
        />
      </div>
    </div>
  );
};

export default ParticipantsOverlay;

