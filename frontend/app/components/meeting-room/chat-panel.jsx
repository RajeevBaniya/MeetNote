"use client";

import { useRef, useEffect } from "react";

function formatTime(ts) {
  if (!ts || typeof ts !== "string") return "";
  try {
    const d = new Date(ts);
    return d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
  } catch {
    return "";
  }
}

const ASSISTANT_USER_ID = "system:assistant";
const ASSISTANT_DISPLAY_NAME = "Assistant";

function isAssistantMessage(message) {
  if (!message) return false;
  const id = typeof message.user_id === "string" ? message.user_id : "";
  const name = typeof message.display_name === "string" ? message.display_name : "";
  return id === ASSISTANT_USER_ID || name === ASSISTANT_DISPLAY_NAME;
}

const ChatPanel = ({
  messages,
  onSendMessage,
  connectionError,
  connected,
  inputDisabled,
  currentUserId,
}) => {
  const listRef = useRef(null);
  const inputRef = useRef(null);

  const visibleMessages = Array.isArray(messages)
    ? messages.filter((msg) => !isAssistantMessage(msg))
    : [];

  useEffect(() => {
    const el = listRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [visibleMessages]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (inputDisabled || !connected) return;
    const input = inputRef.current;
    if (!input) return;
    const text = (input.value || "").trim();
    if (!text) return;
    onSendMessage(text);
    input.value = "";
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const disabled = inputDisabled || !connected || connectionError;

  return (
    <div className="flex flex-col flex-1 min-h-0">
      {connectionError ? (
        <div className="shrink-0 px-4 py-2 bg-amber-900/30 border-b border-amber-700/50 text-amber-200 text-sm">
          {connectionError}
        </div>
      ) : null}
      <ul
        ref={listRef}
        className="flex-1 overflow-y-auto p-4 space-y-3 custom-scrollbar min-h-0"
      >
        {visibleMessages.length === 0 && !connectionError ? (
          <li className="text-sm text-slate-500 py-4">No messages yet.</li>
        ) : (
          visibleMessages.map((msg, index) => {
            const isOwn = currentUserId && msg.user_id === String(currentUserId);
            const name = msg.display_name || msg.user_id || "Someone";
            const time = formatTime(msg.timestamp);
            return (
              <li key={`${msg.timestamp}-${index}`} className="flex flex-col gap-0.5">
                <div className="flex items-baseline gap-2 flex-wrap">
                  <span
                    className={`text-sm font-medium ${isOwn ? "text-emerald-400" : "text-slate-300"}`}
                  >
                    {name}
                    {isOwn ? " (You)" : ""}
                  </span>
                  {time ? (
                    <span className="text-xs text-slate-500">{time}</span>
                  ) : null}
                </div>
                <p className="text-sm text-slate-200 break-words">{msg.text}</p>
              </li>
            );
          })
        )}
      </ul>
      <form onSubmit={handleSubmit} className="shrink-0 p-3 border-t border-slate-600">
        <input
          ref={inputRef}
          type="text"
          placeholder={disabled ? "Chat unavailable" : "Type a message…"}
          disabled={disabled}
          onKeyDown={handleKeyDown}
          className="w-full px-3 py-2.5 rounded-lg bg-slate-900 border border-slate-600 text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed"
        />
        <button
          type="submit"
          disabled={disabled}
          className="mt-2 w-full py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium"
        >
          Send
        </button>
      </form>
    </div>
  );
};

export default ChatPanel;
