"use client";

import { useEffect } from "react";
import ChatPanel from "./chat-panel";

const ChatOverlay = ({
  onClose,
  messages,
  onSendMessage,
  connectionError,
  connected,
  inputDisabled,
  currentUserId,
}) => {
  useEffect(() => {
    const handleKeyDown = (event) => {
      if (event.key === "Escape") {
        onClose?.();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  const disabled = Boolean(inputDisabled);

  return (
    <div className="fixed inset-0 z-50 flex items-stretch justify-end bg-black/40 backdrop-blur-sm">
      <div className="h-full w-full max-w-md translate-x-0 transform bg-slate-900 border-l border-slate-700 shadow-2xl flex flex-col">
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-700 shrink-0">
          <h2 className="text-sm font-semibold text-slate-100 sm:text-base">
            Chat
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-slate-100 text-2xl leading-none p-1"
            aria-label="Close chat"
          >
            ×
          </button>
        </div>
        <ChatPanel
          messages={messages}
          onSendMessage={onSendMessage}
          connectionError={connectionError}
          connected={connected}
          inputDisabled={disabled}
          currentUserId={currentUserId}
        />
      </div>
    </div>
  );
};

export default ChatOverlay;

