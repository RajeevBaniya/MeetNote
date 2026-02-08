"use client";

import { useState, useEffect } from "react";
import ParticipantsPanel from "./participants-panel";
import ChatPanel from "./chat-panel";
import { useMeetingChat } from "@/app/hooks/use-meeting-chat";

const TAB_PARTICIPANTS = "participants";
const TAB_CHAT = "chat";

const ParticipantsAndChatPanel = ({
  onClose,
  currentUserId,
  isHost,
  callId,
  jwt,
  raisedHandUserIds = [],
}) => {
  const [activeTab, setActiveTab] = useState(TAB_PARTICIPANTS);
  const isChatVisible = activeTab === TAB_CHAT;
  const {
    messages,
    connected,
    connectionError,
    sendMessage,
    unreadCount,
    markChatRead,
  } = useMeetingChat(callId, jwt, isChatVisible);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape") onClose?.();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  const handleSelectChat = () => {
    setActiveTab(TAB_CHAT);
    markChatRead();
  };

  const chatInputDisabled = Boolean(connectionError);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-md max-h-[80vh] rounded-xl bg-slate-800 border border-slate-600 shadow-2xl flex flex-col">
        <div className="flex items-center justify-between p-3 border-b border-slate-600 shrink-0 gap-2">
          <div className="flex gap-1">
            <button
              type="button"
              onClick={() => setActiveTab(TAB_PARTICIPANTS)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition ${
                activeTab === TAB_PARTICIPANTS
                  ? "bg-slate-600 text-slate-100"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-700/50"
              }`}
            >
              Participants
            </button>
            <button
              type="button"
              onClick={handleSelectChat}
              className={`relative px-3 py-1.5 rounded-lg text-sm font-medium transition ${
                activeTab === TAB_CHAT
                  ? "bg-slate-600 text-slate-100"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-700/50"
              }`}
            >
              Chat
              {unreadCount > 0 ? (
                <span className="absolute -top-0.5 -right-0.5 bg-red-500 text-white text-xs font-bold rounded-full min-w-[18px] h-[18px] flex items-center justify-center px-1">
                  {unreadCount > 99 ? "99+" : unreadCount}
                </span>
              ) : null}
            </button>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-slate-100 text-2xl leading-none p-1"
            aria-label="Close"
          >
            ×
          </button>
        </div>
        <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
          {activeTab === TAB_PARTICIPANTS ? (
            <ParticipantsPanel
              embedded
              onClose={onClose}
              currentUserId={currentUserId}
              isHost={isHost}
              callId={callId}
              jwt={jwt}
              raisedHandUserIds={raisedHandUserIds}
            />
          ) : (
            <ChatPanel
              messages={messages}
              onSendMessage={sendMessage}
              connectionError={connectionError}
              connected={connected}
              inputDisabled={chatInputDisabled}
              currentUserId={currentUserId}
            />
          )}
        </div>
      </div>
    </div>
  );
};

export default ParticipantsAndChatPanel;
