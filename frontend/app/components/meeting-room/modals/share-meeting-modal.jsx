"use client";

import { useCallback, useEffect, useState } from "react";
import {
  buildShareMessage,
  copyMeetingShare,
  nativeShareMeeting,
} from "@/app/lib/meeting/share-utils";

const ShareMeetingModal = ({ meetingId, jwt, onClose }) => {
  const [info, setInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!meetingId || !jwt) return;
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    if (!apiUrl) {
      setError("API URL not configured");
      setLoading(false);
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
        setInfo(data);
        setError(null);
      })
      .catch((err) => setError(err.message || "Failed to load share info"))
      .finally(() => setLoading(false));
  }, [meetingId, jwt]);

  const shareText = buildShareMessage(info);

  const handleCopy = useCallback(() => {
    if (!shareText) return;
    copyMeetingShare(shareText).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }, [shareText]);

  const handleShare = useCallback(() => {
    if (!info) return;
    nativeShareMeeting(info, copyMeetingShare).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }, [info]);

  if (loading) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
        <div className="rounded-xl bg-slate-800 border border-emerald-500/40 p-6 text-slate-200">
          Loading…
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
        <div className="rounded-xl bg-slate-800 border border-emerald-500/40 p-6 text-slate-200 max-w-md">
          <p className="text-red-400 mb-4">{error}</p>
          <button
            type="button"
            onClick={onClose}
            className="w-full py-2 rounded-lg bg-slate-600 hover:bg-slate-500 text-white"
          >
            Close
          </button>
        </div>
      </div>
    );
  }

  if (!info) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-md rounded-xl bg-slate-800 border border-emerald-500/40 p-6 shadow-2xl">
        <h2 className="text-xl font-semibold text-emerald-400 mb-4 text-center">
          Share Meeting
        </h2>
        <pre className="text-sm text-slate-300 whitespace-pre-wrap mb-6 font-sans bg-slate-900/50 p-4 rounded-lg overflow-auto max-h-48">
          {shareText}
        </pre>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={handleCopy}
            className="flex-1 py-2.5 rounded-lg bg-slate-600 text-white text-sm font-medium transition duration-150 ease-in-out hover:bg-emerald-600 cursor-pointer"
          >
            {copied ? "Copied to clipboard" : "Copy details"}
          </button>
          <button
            type="button"
            onClick={handleShare}
            className="flex-1 py-2.5 rounded-lg bg-slate-600 text-white text-sm font-medium transition duration-150 ease-in-out hover:bg-emerald-600 cursor-pointer"
          >
            Share meeting
          </button>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="mt-3 w-full py-2 rounded-lg border border-slate-600 text-slate-300 hover:bg-slate-700/50 text-sm"
        >
          Close
        </button>
      </div>
    </div>
  );
};

export default ShareMeetingModal;
