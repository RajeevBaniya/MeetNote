"use client";

import { useState, useCallback, useEffect } from "react";
import {
  buildShareMessage,
  copyMeetingShare,
  nativeShareMeeting,
} from "@/app/lib/meeting/share-utils";

const formatJoinCode = (code) => {
  if (!code) return "";
  const digits = code.replace(/\D/g, "").slice(0, 12);
  if (digits.length <= 4) return digits;
  if (digits.length <= 8) return `${digits.slice(0, 4)} ${digits.slice(4)}`;
  return `${digits.slice(0, 4)} ${digits.slice(4, 8)} ${digits.slice(8)}`;
};

const MeetingCreatedModal = ({
  meetingId,
  joinCode,
  passcode,
  onJoin,
  onClose,
  jwt,
}) => {
  const [copied, setCopied] = useState(null);
  const [shareInfo, setShareInfo] = useState(null);
  const [shareLoading, setShareLoading] = useState(Boolean(meetingId && jwt));
  const [shareError, setShareError] = useState(null);

  useEffect(() => {
    if (!meetingId || !jwt) return;
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    if (!apiUrl) {
      setShareError("API URL not configured");
      setShareLoading(false);
      return;
    }
    const base = apiUrl.replace(/\/$/, "");
    fetch(`${base}/meetings/${meetingId}/share`, {
      headers: { Authorization: `Bearer ${jwt}` },
    })
      .then((res) => {
        if (!res.ok) throw new Error(res.status === 404 ? "Not found" : "Failed to load");
        return res.json();
      })
      .then((data) => {
        setShareInfo(data);
        setShareError(null);
      })
      .catch((err) => setShareError(err.message || "Failed to load share info"))
      .finally(() => setShareLoading(false));
  }, [meetingId, jwt]);

  const handleCopyDetails = useCallback(() => {
    if (!shareInfo) return;
    const text = buildShareMessage(shareInfo);
    copyMeetingShare(text).then(() => {
      setCopied("details");
      setTimeout(() => setCopied(null), 2000);
    });
  }, [shareInfo]);

  const handleShareMeeting = useCallback(() => {
    if (!shareInfo) return;
    nativeShareMeeting(shareInfo, copyMeetingShare).then(() => {
      setCopied("details");
      setTimeout(() => setCopied(null), 2000);
    });
  }, [shareInfo]);

  const formattedJoinCode = formatJoinCode(joinCode);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="relative w-full max-w-md rounded-xl bg-slate-800 border border-emerald-500/40 p-6 shadow-2xl">
        {onClose ? (
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="absolute right-3 top-3 flex h-8 w-8 items-center justify-center rounded-full text-slate-400 transition hover:bg-slate-700 hover:text-slate-100"
          >
            ×
          </button>
        ) : null}
        <h2 className="text-xl font-semibold text-emerald-400 mb-4 text-center">
          Meeting Created
        </h2>
        <p className="text-sm text-slate-400 mb-4 text-center">
          Share this with participants
        </p>

        <div className="space-y-4 mb-6">
          <div>
            <label className="block text-xs text-slate-400 mb-2">
              Meeting Code
            </label>
            <div className="px-3 py-2.5 rounded-lg bg-slate-900 border border-slate-600 text-slate-100 text-sm font-mono">
              {formattedJoinCode}
            </div>
          </div>

          <div>
            <label className="block text-xs text-slate-400 mb-2">
              Passcode
            </label>
            <div className="px-3 py-2.5 rounded-lg bg-slate-900 border border-slate-600 text-slate-100 text-sm font-mono">
              {passcode}
            </div>
          </div>
        </div>

        {shareError ? (
          <p className="text-sm text-amber-500 mb-2">{shareError}</p>
        ) : null}
        <div className="flex flex-wrap gap-2 mb-3">
          <button
            type="button"
            onClick={handleCopyDetails}
            disabled={shareLoading || !shareInfo}
            className="flex-1 min-w-[120px] py-2.5 rounded-lg bg-slate-600 text-white text-sm font-medium transition duration-150 ease-in-out hover:bg-emerald-600 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
          >
            {copied === "details" ? "Copied to clipboard" : "Copy details"}
          </button>
          <button
            type="button"
            onClick={handleShareMeeting}
            disabled={shareLoading || !shareInfo}
            className="flex-1 min-w-[120px] py-2.5 rounded-lg bg-slate-600 text-white text-sm font-medium transition duration-150 ease-in-out hover:bg-emerald-600 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
          >
            Share meeting
          </button>
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

export default MeetingCreatedModal;
