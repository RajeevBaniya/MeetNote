"use client";

import { useState } from "react";

const MeetingInfoModal = ({ meetingId, passcode, onJoin }) => {
  const [copied, setCopied] = useState(null);

  const copyToClipboard = (text, label) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(label);
      setTimeout(() => setCopied(null), 2000);
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-md rounded-xl bg-slate-800 border border-emerald-500/40 p-6 shadow-2xl">
        <h2 className="text-xl font-semibold text-emerald-400 mb-4 text-center">
          Meeting Created
        </h2>
        <p className="text-sm text-slate-400 mb-4 text-center">
          Share this with participants
        </p>
        
        <div className="space-y-4 mb-6">
          <div>
            <label className="block text-xs text-slate-400 mb-2">Meeting ID</label>
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={meetingId}
                readOnly
                className="flex-1 px-3 py-2.5 rounded-lg bg-slate-900 border border-slate-600 text-slate-100 text-sm font-mono"
              />
              <button
                type="button"
                onClick={() => copyToClipboard(meetingId, "id")}
                className="px-4 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium transition"
              >
                {copied === "id" ? "Copied!" : "Copy"}
              </button>
            </div>
          </div>
          
          <div>
            <label className="block text-xs text-slate-400 mb-2">Passcode</label>
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={passcode}
                readOnly
                className="flex-1 px-3 py-2.5 rounded-lg bg-slate-900 border border-slate-600 text-slate-100 text-sm font-mono"
              />
              <button
                type="button"
                onClick={() => copyToClipboard(passcode, "passcode")}
                className="px-4 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium transition"
              >
                {copied === "passcode" ? "Copied!" : "Copy"}
              </button>
            </div>
          </div>
        </div>

        <button
          type="button"
          onClick={onJoin}
          className="w-full py-3 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-base transition shadow-lg"
        >
          Join meeting
        </button>
      </div>
    </div>
  );
};

export default MeetingInfoModal;
