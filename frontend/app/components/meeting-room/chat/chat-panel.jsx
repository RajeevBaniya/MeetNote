"use client";

import { useCallback, useEffect, useRef, useState } from "react";

const formatTime = (ts) => {
  if (!ts || typeof ts !== "string") return "";
  try {
    const d = new Date(ts);
    return d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
  } catch {
    return "";
  }
};

const ASSISTANT_USER_ID = "system:assistant";
const ASSISTANT_DISPLAY_NAME = "Assistant";

const isAssistantMessage = (message) => {
  if (!message) return false;
  const id = typeof message.user_id === "string" ? message.user_id : "";
  const name = typeof message.display_name === "string" ? message.display_name : "";
  return id === ASSISTANT_USER_ID || name === ASSISTANT_DISPLAY_NAME;
};

const ChatPanel = ({
  messages,
  onSendMessage,
  removeMessage,
  connectionError,
  connected,
  reconnecting,
  inputDisabled,
  currentUserId,
}) => {
  const listRef = useRef(null);
  const inputRef = useRef(null);
  const [showNewMessages, setShowNewMessages] = useState(false);
  const [inputFocused, setInputFocused] = useState(false);
  const isNearBottomRef = useRef(true);
  const prevLengthRef = useRef(0);

  const handleSubmit = useCallback(
    (e) => {
      e.preventDefault();
      if (inputDisabled || !connected) return;
      const input = inputRef.current;
      if (!input) return;
      const text = (input.value || "").trim();
      if (!text) return;
      onSendMessage(text);
      input.value = "";
    },
    [inputDisabled, connected, onSendMessage],
  );

  const handleKeyDown = useCallback(
    (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSubmit(e);
      }
    },
    [handleSubmit],
  );

  const visibleMessages = Array.isArray(messages)
    ? messages.filter((msg) => !isAssistantMessage(msg))
    : [];

  const handleRetry = useCallback(
    (msg) => {
      if (!msg || !msg.text) return;
      if (msg.client_id && removeMessage) {
        removeMessage(msg.client_id);
      }
      onSendMessage(msg.text);
    },
    [onSendMessage, removeMessage],
  );

  useEffect(() => {
    const el = listRef.current;
    if (!el) return;
    const isNearBottom =
      el.scrollHeight - el.scrollTop - el.clientHeight < 80;
    isNearBottomRef.current = isNearBottom;

    const prevLength = prevLengthRef.current;
    const nextLength = visibleMessages.length;

    const hasNewMessage = nextLength > prevLength;
    prevLengthRef.current = nextLength;

    if (hasNewMessage && !isNearBottom) {
      setShowNewMessages(true);
      return;
    }

    if (isNearBottom) {
      el.scrollTop = el.scrollHeight;
      setShowNewMessages(false);
    }
  }, [visibleMessages]);

  const handleScroll = useCallback(() => {
    const el = listRef.current;
    if (!el) return;
    const isNearBottom =
      el.scrollHeight - el.scrollTop - el.clientHeight < 80;
    isNearBottomRef.current = isNearBottom;
    if (isNearBottom) {
      setShowNewMessages(false);
    }
  }, []);

  const handleScrollToBottom = useCallback(() => {
    const el = listRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
    isNearBottomRef.current = true;
    setShowNewMessages(false);
  }, []);

  const disabled = inputDisabled || !connected || connectionError;

  return (
    <div className="flex flex-col flex-1 min-h-0">
      {connectionError ? (
        <div className="shrink-0 px-4 py-2 bg-amber-900/30 border-b border-amber-700/50 text-amber-200 text-sm">
          {connectionError}
        </div>
      ) : null}
      {!connectionError && reconnecting && !connected ? (
        <div className="shrink-0 px-4 py-2 bg-amber-900/20 border-b border-amber-700/30 text-amber-200 text-sm">
          Reconnecting…
        </div>
      ) : null}
      <div className="relative flex-1 min-h-0">
        <ul
          ref={listRef}
          onScroll={handleScroll}
          className="h-full overflow-y-auto p-4 space-y-3 custom-scrollbar min-h-0"
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
                      <p className="text-sm text-slate-200 wrap-break-word">
                    {msg.text}
                    {msg.failed ? (
                      <>
                        <span className="text-xs text-red-400 ml-2">Failed to send</span>
                        <button
                          type="button"
                          className="text-xs text-emerald-400 ml-2 hover:text-emerald-300"
                          onClick={() => handleRetry(msg)}
                        >
                          Retry
                        </button>
                      </>
                    ) : null}
                    {!msg.failed && msg.optimistic ? (
                      <span className="text-xs text-slate-400 ml-2">sending...</span>
                    ) : null}
                  </p>
                </li>
              );
            })
          )}
        </ul>
        {showNewMessages && !inputFocused ? (
          <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-10">
            <button
              type="button"
              onClick={handleScrollToBottom}
              className="mx-auto flex items-center justify-center rounded-full bg-slate-800/80 backdrop-blur-md border border-slate-600/40 px-3 py-1 text-xs text-slate-100 shadow hover:bg-slate-700/90 transition-all animate-fade-in"
            >
              New messages ↓
            </button>
          </div>
        ) : null}
      </div>
      <form onSubmit={handleSubmit} className="shrink-0 p-3 border-t border-slate-600">
        <input
          ref={inputRef}
          type="text"
          placeholder={disabled ? "Chat unavailable" : "Type a message…"}
          disabled={disabled}
          onKeyDown={handleKeyDown}
          onFocus={() => setInputFocused(true)}
          onBlur={() => setInputFocused(false)}
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
