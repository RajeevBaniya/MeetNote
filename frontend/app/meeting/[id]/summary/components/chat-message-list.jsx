"use client";

import { Bot, User, Loader2, RotateCcw } from "lucide-react";

const AssistantBubble = ({ content, pending }) => (
  <div className="flex gap-3 max-w-[85%] mr-auto">
    <div className="w-7 h-7 rounded-full bg-slate-800 border border-slate-700 text-slate-300 flex items-center justify-center shrink-0">
      <Bot className="w-4 h-4" />
    </div>
    <div className="rounded-xl px-4 py-2.5 text-sm leading-relaxed bg-slate-800/80 border border-slate-700/50 text-slate-200 rounded-tl-none">
      {pending ? (
        <span className="flex items-center gap-2 text-slate-400">
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
          Thinking…
        </span>
      ) : (
        content
      )}
    </div>
  </div>
);

const UserBubble = ({ content, failed, retrying, onRetry, disabled }) => (
  <div className="flex flex-col items-end gap-1 max-w-[85%] ml-auto">
    <div className="flex gap-3 flex-row-reverse">
      <div className="w-7 h-7 rounded-full bg-emerald-600/20 border border-emerald-500/30 text-emerald-400 flex items-center justify-center shrink-0">
        <User className="w-4 h-4" />
      </div>
      <div
        className={`rounded-xl px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap rounded-tr-none shadow-md ${
          failed
            ? "bg-red-900/30 border border-red-500/40 text-red-200"
            : "bg-emerald-600/90 text-white shadow-emerald-950/20"
        }`}
      >
        {content}
      </div>
    </div>
    {failed && (
      <button
        type="button"
        onClick={onRetry}
        disabled={disabled || retrying}
        className="flex items-center gap-1 text-xs text-red-400 hover:text-red-300 transition disabled:opacity-50 disabled:cursor-not-allowed pr-10"
      >
        <RotateCcw className="w-3 h-3" />
        {retrying ? "Retrying…" : "Failed · Retry"}
      </button>
    )}
  </div>
);

const EmptyState = () => (
  <div className="flex flex-col items-center justify-center h-full text-center px-4">
    <Bot className="w-10 h-10 text-emerald-500/40 mb-3" />
    <p className="text-sm font-medium text-slate-300">Ask anything about the meeting</p>
    <p className="text-xs text-slate-500 max-w-xs mt-1">
      Try: "What were the key action items?" or "What did each speaker decide?"
    </p>
  </div>
);

const ChatMessageList = ({ messages, isSending, scrollRef, onRetry }) => {
  const hasVisibleMessages = messages.some((m) => !m.pending || m.role === "assistant");

  return (
    <div
      ref={scrollRef}
      className="flex-1 overflow-y-auto p-4 space-y-4 min-h-0 scroll-smooth custom-scrollbar"
    >
      {messages.length === 0 && !isSending ? (
        <EmptyState />
      ) : (
        messages.map((msg) => {
          if (msg.role === "user") {
            return (
              <UserBubble
                key={msg.clientId}
                content={msg.content}
                failed={msg.failed}
                retrying={msg.retrying}
                disabled={isSending}
                onRetry={() => onRetry(msg.clientId, msg.content)}
              />
            );
          }
          return (
            <AssistantBubble
              key={msg.clientId}
              content={msg.content}
              pending={msg.pending}
            />
          );
        })
      )}
    </div>
  );
};

export default ChatMessageList;
