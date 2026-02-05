"use client";

import { useEffect, useState } from "react";
import { useCallStateHooks } from "@stream-io/video-react-sdk";

const ParticipantsPanel = ({ onClose, currentUserId, isHost, callId, jwt }) => {
  const { useParticipants, useLocalParticipant } = useCallStateHooks();
  const participants = useParticipants() ?? [];
  const localParticipant = useLocalParticipant();
  const [actioningId, setActioningId] = useState(null);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL;
  const canModerate = Boolean(isHost && apiUrl && callId && jwt);

  const removeParticipant = async (participantUserId) => {
    if (!canModerate || actioningId) return;
    setActioningId(participantUserId);
    try {
      const res = await fetch(`${apiUrl}/meetings/${callId}/remove-participant`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${jwt}`,
        },
        body: JSON.stringify({ user_id: participantUserId }),
      });
      if (res.ok) {
        onClose?.();
      }
    } catch {
      // ignore
    } finally {
      setActioningId(null);
    }
  };

  const muteParticipant = async (participantUserId) => {
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
      // ignore
    } finally {
      setActioningId(null);
    }
  };

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  const hasVideoTrack = (p) => {
    const tracks = p.publishedTracks ?? [];
    return tracks.includes("videoTrack") || tracks.includes("video");
  };

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

        <ul className="flex-1 overflow-y-auto p-4 space-y-2 custom-scrollbar min-h-0">
          {participants.length === 0 ? (
            <li className="text-sm text-slate-400 py-4">No participants in this call</li>
          ) : (
            participants.map((p) => {
              const isLocal = localParticipant?.sessionId === p.sessionId;
              const showHostBadge =
                Boolean(isHost) && Boolean(currentUserId) && p.userId === currentUserId;
              const displayName = p.name || p.userId || "Unknown";
              const micMuted = p.isMuted === true;
              const cameraOn = hasVideoTrack(p);

              return (
                <li
                  key={p.sessionId ?? p.userId}
                  className="flex items-center gap-3 p-3 rounded-lg bg-slate-900/50 border border-slate-700"
                >
                  <div className="flex flex-col gap-1 min-w-0 flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="truncate text-slate-200 font-medium" title={displayName}>
                        {displayName}
                      </span>
                      {isLocal ? (
                        <span className="text-xs text-slate-400 shrink-0">(You)</span>
                      ) : null}
                      {showHostBadge ? (
                        <span className="text-xs font-medium text-emerald-400 shrink-0">Host</span>
                      ) : null}
                    </div>
                    <div className="flex items-center gap-3 text-slate-400">
                      <span
                        className="flex items-center gap-1"
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
                            <path strokeLinecap="round" strokeLinejoin="round" d="M5 5l14 14" />
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
                        <span className="text-xs">{micMuted ? "Muted" : "On"}</span>
                      </span>
                      <span
                        className="flex items-center gap-1"
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
                            <path strokeLinecap="round" strokeLinejoin="round" d="M5 5l14 14" />
                          </svg>
                        )}
                        <span className="text-xs">{cameraOn ? "On" : "Off"}</span>
                      </span>
                    </div>
                  </div>
                  {canModerate && !isLocal ? (
                    <div className="flex items-center gap-1 shrink-0">
                      <button
                        type="button"
                        onClick={() => muteParticipant(p.userId)}
                        disabled={actioningId != null}
                        className="p-1.5 rounded text-slate-400 hover:text-slate-200 hover:bg-slate-700 disabled:opacity-50"
                        title="Mute"
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
                        className="p-1.5 rounded text-red-400 hover:text-red-200 hover:bg-slate-700 disabled:opacity-50"
                        title="Remove"
                      >
                        <svg
                          xmlns="http://www.w3.org/2000/svg"
                          fill="none"
                          viewBox="0 0 24 24"
                          strokeWidth={2}
                          stroke="currentColor"
                          className="w-4 h-4"
                        >
                          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    </div>
                  ) : null}
                </li>
              );
            })
          )}
        </ul>
      </div>
    </div>
  );
};

export default ParticipantsPanel;
