"use client";

import { useCallback, useEffect, useState } from "react";
import { useCallStateHooks } from "@stream-io/video-react-sdk";

const ParticipantsPanel = ({
  onClose,
  currentUserId,
  isHost,
  callId,
  jwt,
  raisedHandUserIds = [],
  embedded = false,
  onLowerHandForUser,
}) => {
  const { useParticipants, useLocalParticipant } = useCallStateHooks();
  const participants = useParticipants() ?? [];
  const localParticipant = useLocalParticipant();
  const [actioningId, setActioningId] = useState(null);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL;
  const canModerate = Boolean(isHost && apiUrl && callId && jwt);
  const raisedSet = new Set(raisedHandUserIds ?? []);
  const canLowerOthersHand = Boolean(
    isHost && typeof onLowerHandForUser === "function",
  );

  const removeParticipant = useCallback(
    async (participantUserId) => {
      if (!canModerate || actioningId) return;
      setActioningId(participantUserId);
      try {
        const res = await fetch(
          `${apiUrl}/meetings/${callId}/remove-participant`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${jwt}`,
            },
            body: JSON.stringify({ user_id: participantUserId }),
          },
        );
        if (res.ok) {
          onClose?.();
        }
      } catch {
      } finally {
        setActioningId(null);
      }
    },
    [canModerate, apiUrl, callId, jwt, onClose, actioningId],
  );

  const muteParticipant = useCallback(
    async (participantUserId) => {
      if (!canModerate || actioningId) return;
      setActioningId(participantUserId);
      try {
        await fetch(`${apiUrl}/meetings/${callId}/mute-participant`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${jwt}`,
          },
          body: JSON.stringify({ user_id: participantUserId }),
        });
      } catch {
      } finally {
        setActioningId(null);
      }
    },
    [canModerate, apiUrl, callId, jwt, actioningId],
  );

  useEffect(() => {
    if (embedded) return;
    const handleKeyDown = (e) => {
      if (e.key === "Escape") onClose?.();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose, embedded]);

  const hasVideoTrack = (p) => {
    const tracks = p.publishedTracks ?? [];
    return tracks.includes("videoTrack") || tracks.includes("video");
  };

  const listContent = (
    <ul className="flex-1 overflow-y-auto p-3 sm:p-4 space-y-2 custom-scrollbar min-h-0">
      {participants.length === 0 ? (
        <li className="text-sm text-slate-400 py-8 text-center">
          No participants in this call
        </li>
      ) : (
        participants.map((p) => {
          const isLocal = localParticipant?.sessionId === p.sessionId;
          const showHostBadge =
            Boolean(isHost) &&
            Boolean(currentUserId) &&
            p.userId === currentUserId;
          const displayName = p.name || p.userId || "Unknown";
          const micMuted = p.isMuted === true;
          const cameraOn = hasVideoTrack(p);

          return (
            <li
              key={p.sessionId ?? p.userId}
              className="flex items-center gap-3 p-3 sm:p-4 rounded-xl bg-slate-800/60 border border-slate-700/50 hover:bg-slate-800/80 hover:border-slate-600/70 transition-all duration-200 shadow-sm"
            >
              <div className="flex flex-col gap-1.5 min-w-0 flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span
                    className="truncate text-slate-100 font-semibold text-sm sm:text-base"
                    title={displayName}
                  >
                    {displayName}
                  </span>
                  {isLocal ? (
                    <span className="text-xs px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-400 font-medium shrink-0">
                      You
                    </span>
                  ) : null}
                  {showHostBadge ? (
                    <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 font-medium shrink-0">
                      Host
                    </span>
                  ) : null}
                  {p.userId && raisedSet.has(p.userId) ? (
                    <span
                      className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-400 shrink-0"
                      title="Hand raised"
                    >
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        fill="none"
                        viewBox="0 0 24 24"
                        strokeWidth={2}
                        stroke="currentColor"
                        className="w-3.5 h-3.5"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M6.633 10.25c.806 0 1.533-.446 2.031-1.08a9.041 9.041 0 0 1 2.861-2.4c.723-.384 1.35-.956 1.653-1.715a4.498 4.498 0 0 0 .322-1.672V2.75a.75.75 0 0 1 1.5 0v2.716a5.499 5.499 0 0 1-.43 2.103 5.99 5.99 0 0 1 2.43 2.103 5.499 5.499 0 0 1-.43-2.103V2.75a.75.75 0 0 1 1.5 0v6.375a4.5 4.5 0 0 1-1.5 3.375 9 9 0 0 1-6.939 2.437A9.001 9.001 0 0 1 6.633 10.25z"
                        />
                      </svg>
                      <span className="text-xs font-medium">Raised</span>
                    </span>
                  ) : null}
                </div>
                <div className="flex items-center gap-3 text-slate-400">
                  <span
                    className={`flex items-center gap-1.5 px-2 py-1 rounded-md ${
                      micMuted ? "bg-red-500/10" : "bg-green-500/10"
                    }`}
                    title={micMuted ? "Muted" : "Unmuted"}
                  >
                    {micMuted ? (
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        fill="none"
                        viewBox="0 0 24 24"
                        strokeWidth={2}
                        stroke="currentColor"
                        className="w-4 h-4 text-red-400"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
                        />
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M5 5l14 14"
                        />
                      </svg>
                    ) : (
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        fill="none"
                        viewBox="0 0 24 24"
                        strokeWidth={2}
                        stroke="currentColor"
                        className="w-4 h-4 text-green-400"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
                        />
                      </svg>
                    )}
                    <span
                      className={`text-xs font-medium ${micMuted ? "text-red-400" : "text-green-400"}`}
                    >
                      {micMuted ? "Muted" : "Mic"}
                    </span>
                  </span>
                  <span
                    className={`flex items-center gap-1.5 px-2 py-1 rounded-md ${
                      cameraOn ? "bg-green-500/10" : "bg-red-500/10"
                    }`}
                    title={cameraOn ? "Camera on" : "Camera off"}
                  >
                    {cameraOn ? (
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        fill="none"
                        viewBox="0 0 24 24"
                        strokeWidth={2}
                        stroke="currentColor"
                        className="w-4 h-4 text-green-400"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
                        />
                      </svg>
                    ) : (
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        fill="none"
                        viewBox="0 0 24 24"
                        strokeWidth={2}
                        stroke="currentColor"
                        className="w-4 h-4 text-red-400"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
                        />
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M5 5l14 14"
                        />
                      </svg>
                    )}
                    <span
                      className={`text-xs font-medium ${cameraOn ? "text-green-400" : "text-red-400"}`}
                    >
                      {cameraOn ? "Cam" : "Off"}
                    </span>
                  </span>
                </div>
              </div>
              {canModerate && !isLocal ? (
                <div className="flex items-center gap-2 shrink-0">
                  {canLowerOthersHand && p.userId && raisedSet.has(p.userId) ? (
                    <button
                      type="button"
                      onClick={() => onLowerHandForUser(p.userId)}
                      className="px-2 py-1.5 rounded-lg bg-amber-500/15 text-amber-300 hover:bg-amber-500/25 text-xs font-medium transition-all duration-200"
                      title="Lower hand"
                    >
                      Lower hand
                    </button>
                  ) : null}
                  <button
                    type="button"
                    onClick={() => muteParticipant(p.userId)}
                    disabled={actioningId != null}
                    className="p-2 rounded-lg bg-slate-700/50 text-slate-300 hover:text-slate-100 hover:bg-slate-700 disabled:opacity-50 transition-all duration-200"
                    title="Mute participant"
                  >
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                      strokeWidth={2}
                      stroke="currentColor"
                      className="w-4 h-4"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
                      />
                    </svg>
                  </button>
                  <button
                    type="button"
                    onClick={() => removeParticipant(p.userId)}
                    disabled={actioningId != null}
                    className="p-2 rounded-lg bg-red-500/10 text-red-400 hover:text-red-300 hover:bg-red-500/20 disabled:opacity-50 transition-all duration-200"
                    title="Remove participant"
                  >
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                      strokeWidth={2}
                      stroke="currentColor"
                      className="w-4 h-4"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M6 18L18 6M6 6l12 12"
                      />
                    </svg>
                  </button>
                </div>
              ) : null}
            </li>
          );
        })
      )}
    </ul>
  );

  if (embedded) {
    return listContent;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-md max-h-[80vh] rounded-xl bg-slate-800 border border-slate-600 shadow-2xl flex flex-col">
        <div className="flex items-center justify-between p-4 border-b border-slate-600 shrink-0">
          <h2 className="text-xl font-semibold text-slate-100">Participants</h2>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-slate-100 text-2xl leading-none"
            aria-label="Close"
          >
            ×
          </button>
        </div>
        {listContent}
      </div>
    </div>
  );
};

export default ParticipantsPanel;
