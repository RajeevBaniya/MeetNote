"use client";

import { useCallback, useEffect } from "react";

const LeaveConfirmModal = ({ onClose, onLeaveOnly, onEndForEveryone, disabled = false }) => {
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  const handleLeaveOnly = useCallback(() => {
    if (disabled) return;
    onClose();
    onLeaveOnly?.();
  }, [disabled, onClose, onLeaveOnly]);

  const handleEndForEveryone = useCallback(() => {
    if (disabled) return;
    onClose();
    onEndForEveryone?.();
  }, [disabled, onClose, onEndForEveryone]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-sm rounded-xl bg-slate-800 border border-slate-600 p-6 shadow-2xl">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-slate-100">Leave meeting?</h2>
          <button
            type="button"
            onClick={onClose}
            disabled={disabled}
            className="text-slate-400 hover:text-slate-100 text-2xl leading-none"
            aria-label="Close"
          >
            ×
          </button>
        </div>
        <p className="text-sm text-slate-400 mb-4">
          You can leave the call or end it for everyone.
        </p>
        <div className="flex flex-col gap-2">
          <button
            type="button"
            onClick={handleLeaveOnly}
            disabled={disabled}
            className="w-full py-3 rounded-lg bg-slate-600 hover:bg-slate-500 text-white font-medium transition"
          >
            Leave meeting
          </button>
          <button
            type="button"
            onClick={handleEndForEveryone}
            disabled={disabled}
            className="w-full py-3 rounded-lg bg-red-600 hover:bg-red-500 text-white font-medium transition"
          >
            End meeting for everyone
          </button>
        </div>
      </div>
    </div>
  );
};

export default LeaveConfirmModal;
