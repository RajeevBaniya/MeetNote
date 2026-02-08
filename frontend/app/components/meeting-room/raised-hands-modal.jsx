"use client";

import { useEffect } from "react";
import { useCallStateHooks } from "@stream-io/video-react-sdk";

const RaisedHandsModal = ({ onClose, raisedHandUserIds }) => {
  const { useParticipants } = useCallStateHooks();
  const participants = useParticipants() ?? [];

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  const raisedSet = new Set(raisedHandUserIds ?? []);
  const list = participants.filter((p) => p.userId && raisedSet.has(p.userId));

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-md max-h-[80vh] rounded-xl bg-slate-800 border border-slate-600 shadow-2xl flex flex-col">
        <div className="flex items-center justify-between p-4 border-b border-slate-600 shrink-0">
          <h2 className="text-xl font-semibold text-slate-100">Raised hands</h2>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-slate-100 text-2xl leading-none"
            aria-label="Close"
          >
            ×
          </button>
        </div>
        <ul className="flex-1 overflow-y-auto p-4 space-y-2 custom-scrollbar min-h-0">
          {list.length === 0 ? (
            <li className="text-sm text-slate-400 py-4">No hands raised</li>
          ) : (
            list.map((p) => (
              <li
                key={p.sessionId ?? p.userId}
                className="flex items-center gap-3 p-3 rounded-lg bg-slate-900/50 border border-slate-700"
              >
                <span className="text-amber-400 shrink-0" aria-hidden>
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                    strokeWidth={1.5}
                    stroke="currentColor"
                    className="w-5 h-5"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M6.633 10.25c.806 0 1.533-.446 2.031-1.08a9.041 9.041 0 0 1 2.861-2.4c.723-.384 1.35-.956 1.653-1.715a4.498 4.498 0 0 0 .322-1.672V2.75a.75.75 0 0 1 1.5 0v2.716a5.499 5.499 0 0 1-.43 2.103 5.99 5.99 0 0 1 2.43 2.103 5.499 5.499 0 0 1-.43-2.103V2.75a.75.75 0 0 1 1.5 0v2.716a5.499 5.499 0 0 1-.43 2.103 5.99 5.99 0 0 1 2.43 2.103 5.499 5.499 0 0 1-.43-2.103V2.75a.75.75 0 0 1 1.5 0v6.375a4.5 4.5 0 0 1-1.5 3.375 9 9 0 0 1-6.939 2.437A9.001 9.001 0 0 1 6.633 10.25z"
                    />
                  </svg>
                </span>
                <span className="truncate text-slate-200 font-medium">
                  {p.name || p.userId || "Unknown"}
                </span>
              </li>
            ))
          )}
        </ul>
      </div>
    </div>
  );
};

export default RaisedHandsModal;
