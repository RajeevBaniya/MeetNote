"use client";

import { useEffect } from "react";

import RaisedHandsPanel from "./raised-hands-panel";

const RaisedHandsModal = ({
  onClose,
  raisedHandUserIds,
  isHost = false,
  onLowerHandForUser,
}) => {
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

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
        <RaisedHandsPanel
          raisedHandUserIds={raisedHandUserIds}
          isHost={isHost}
          onLowerHandForUser={onLowerHandForUser}
        />
      </div>
    </div>
  );
};

export default RaisedHandsModal;
