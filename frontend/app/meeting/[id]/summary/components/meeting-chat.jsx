"use client";

import { useState } from "react";
import { Bot, MessageSquareOff, Loader2, ShieldAlert, FileText, BookOpen, Layers } from "lucide-react";

import useChatStatus from "@/app/lib/meeting/use-chat-status";
import useMeetingChatPostCall from "@/app/lib/meeting/use-meeting-chat-post-call";
import useAutoScroll from "@/app/lib/meeting/use-auto-scroll";
import ChatMessageList from "./chat-message-list";
import ChatInput from "./chat-input";

const RETRIEVAL_MODE_CONFIG = {
  transcript: {
    label: "Transcript",
    icon: FileText,
    className: "bg-emerald-500/10 border-emerald-500/30 text-emerald-300",
  },
  summary: {
    label: "Summary",
    icon: BookOpen,
    className: "bg-blue-500/10 border-blue-500/30 text-blue-300",
  },
  hybrid: {
    label: "Transcript + Summary",
    icon: Layers,
    className: "bg-violet-500/10 border-violet-500/30 text-violet-300",
  },
};

const RetrievalModeBadge = ({ mode }) => {
  const config = RETRIEVAL_MODE_CONFIG[mode];
  if (!config) return null;
  const Icon = config.icon;
  return (
    <span
      className={`ml-auto inline-flex items-center gap-1.5 text-[10px] font-medium border rounded px-2 py-0.5 ${config.className}`}
    >
      <Icon className="w-3 h-3" />
      {config.label}
    </span>
  );
};

const UnavailableScreen = ({ message }) => (
  <div className="flex flex-col items-center justify-center py-16 px-6 text-center bg-slate-900/10 rounded-xl border border-slate-800">
    <MessageSquareOff className="w-12 h-12 text-slate-600 mb-4" />
    <p className="text-base font-semibold text-slate-300">AI Chat Unavailable</p>
    <p className="mt-1 text-sm text-slate-500 max-w-sm">{message}</p>
  </div>
);

const IndexingScreen = () => (
  <div className="flex flex-col items-center justify-center py-16 px-6 text-center bg-slate-900/10 rounded-xl border border-slate-800">
    <Loader2 className="w-10 h-10 text-emerald-500/60 mb-4 animate-spin" />
    <p className="text-base font-semibold text-slate-300">Preparing Meeting Context</p>
    <p className="mt-1 text-sm text-slate-500 max-w-sm">
      The transcript is being indexed. This usually takes a minute. Check back shortly.
    </p>
  </div>
);

const TranscriptExpiredScreen = () => (
  <div className="flex flex-col items-center justify-center py-16 px-6 text-center bg-amber-950/10 rounded-xl border border-amber-800/30">
    <BookOpen className="w-10 h-10 text-amber-500/60 mb-4" />
    <p className="text-base font-semibold text-slate-300">Transcript Expired</p>
    <p className="mt-1 text-sm text-slate-500 max-w-sm">
      The raw transcript was deleted after the 7-day retention period. AI Chat continues using
      the generated summary.
    </p>
  </div>
);

const SummaryOnlyScreen = () => (
  <div className="flex flex-col items-center justify-center py-16 px-6 text-center bg-slate-900/10 rounded-xl border border-slate-800">
    <BookOpen className="w-10 h-10 text-blue-500/40 mb-4" />
    <p className="text-base font-semibold text-slate-300">Summary Available</p>
    <p className="mt-1 text-sm text-slate-500 max-w-sm">
      No transcript was found, but a summary exists. You can ask questions based on the meeting
      summary.
    </p>
  </div>
);

const UnauthorizedScreen = () => (
  <div className="flex flex-col items-center justify-center py-16 px-6 text-center bg-slate-900/10 rounded-xl border border-red-900/40">
    <ShieldAlert className="w-12 h-12 text-red-500/60 mb-4" />
    <p className="text-base font-semibold text-slate-300">Access Denied</p>
    <p className="mt-1 text-sm text-slate-500 max-w-sm">
      You must be a host or verified participant of this meeting to use the assistant.
    </p>
  </div>
);

const MeetingChat = ({ meetingId, jwt, chatStatus, chatStatusLoading }) => {
  const status = useChatStatus(chatStatus, chatStatusLoading);
  const {
    messages,
    historyError,
    sendError,
    isSending,
    latestResponseMode,
    sendMessage,
    retryMessage,
  } = useMeetingChatPostCall(meetingId, jwt, status.isAvailable);
  const { scrollRef } = useAutoScroll(messages.length);

  const [draft, setDraft] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!draft.trim() || isSending || !status.isAvailable) return;
    sendMessage(draft);
    setDraft("");
  };

  if (status.isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 bg-slate-900/10 rounded-xl border border-slate-800">
        <Loader2 className="w-8 h-8 animate-spin text-emerald-500" />
        <p className="mt-3 text-sm text-slate-400">Loading chat assistant…</p>
      </div>
    );
  }

  if (status.isUnauthorized) {
    return <UnauthorizedScreen />;
  }

  if (status.isIndexing) {
    return <IndexingScreen />;
  }

  if (status.isTranscriptExpired && !status.isAvailable) {
    return <TranscriptExpiredScreen />;
  }

  if (status.isSummaryOnly && !status.isAvailable) {
    return <SummaryOnlyScreen />;
  }

  if (!status.isAvailable) {
    return (
      <UnavailableScreen message="AI Chat is not available yet. End the meeting first, or wait for the summary to be generated." />
    );
  }

  // The badge shows the mode of the last completed response, or falls back to
  // the meeting's current retrieval mode from chat-status.
  const activeBadgeMode = latestResponseMode || status.displayMode;

  return (
    <div className="flex flex-col h-[520px] rounded-xl border border-slate-700/60 bg-slate-900/40 overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-slate-800 bg-slate-900/60 shrink-0">
        <Bot className="w-5 h-5 text-emerald-400 shrink-0" />
        <div className="min-w-0">
          <h3 className="text-sm font-semibold text-slate-100">Meeting Assistant</h3>
          <p className="text-[10px] text-slate-500">
            {status.isTranscriptExpired ? "Answering from summary only" : "Ask anything about this meeting"}
          </p>
        </div>
        <RetrievalModeBadge mode={activeBadgeMode} />
      </div>

      {/* Error banners — shown below header, do not break message flow */}
      {sendError && (
        <div className="px-4 py-2 bg-red-950/30 border-b border-red-500/30 text-xs text-red-300 shrink-0">
          {sendError}
        </div>
      )}
      {historyError && (
        <div className="px-4 py-2 bg-amber-950/20 border-b border-amber-500/20 text-xs text-amber-300 shrink-0">
          Could not load previous conversation. Starting fresh.
        </div>
      )}

      {/* Messages */}
      <ChatMessageList
        messages={messages}
        isSending={isSending}
        scrollRef={scrollRef}
        onRetry={retryMessage}
      />

      {/* Input — always disabled when chat is unavailable */}
      <ChatInput
        value={draft}
        onChange={setDraft}
        onSubmit={handleSubmit}
        disabled={isSending || !status.isAvailable}
        sending={isSending}
      />
    </div>
  );
};

export default MeetingChat;
