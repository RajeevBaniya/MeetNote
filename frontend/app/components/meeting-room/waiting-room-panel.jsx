"use client";

import React from "react";

const WaitingRoomModal = ({
  pendingUserIds,
  disconnected,
  onClose,
  sendAction,
}) => {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-md rounded-xl bg-slate-800 border border-slate-600 p-6 shadow-2xl">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-slate-100">Waiting Room</h2>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-slate-100 text-2xl leading-none"
          >
            ×
          </button>
        </div>

        {disconnected ? (
          <div className="p-4 rounded-lg bg-amber-900/20 border border-amber-600 text-amber-200 text-sm">
            Waiting room disconnected
          </div>
        ) : pendingUserIds.length === 0 ? (
          <p className="text-sm text-slate-400">No pending join requests</p>
        ) : (
          <ul className="space-y-3">
            {pendingUserIds.map((uid) => (
              <li
                key={uid}
                className="flex items-center justify-between gap-3 p-3 rounded-lg bg-slate-900/50 border border-slate-700"
              >
                <span className="truncate text-slate-200" title={uid}>
                  {uid}
                </span>
                <span className="flex gap-2 shrink-0">
                  <button
                    type="button"
                    onClick={() => sendAction("approve", uid)}
                    className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium transition"
                  >
                    Approve
                  </button>
                  <button
                    type="button"
                    onClick={() => sendAction("reject", uid)}
                    className="px-3 py-1.5 rounded-lg bg-red-600 hover:bg-red-500 text-white text-sm font-medium transition"
                  >
                    Reject
                  </button>
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};

export default WaitingRoomModal;
