"use client";

import { useMemo } from "react";

const CHAT_MODE_TO_DISPLAY_MODE = {
  transcript: "transcript",
  transcript_and_summary: "hybrid",
  summary: "summary",
};

const useChatStatus = (chatStatus, chatStatusLoading) => {
  const derived = useMemo(() => {
    if (chatStatusLoading || !chatStatus) {
      return {
        isLoading: true,
        isAvailable: false,
        isIndexing: false,
        isTranscriptExpired: false,
        isSummaryOnly: false,
        isUnauthorized: false,
        chatMode: null,
        displayMode: null,
      };
    }

    const { is_available, has_transcript, chat_mode } = chatStatus;

    const isIndexing = !is_available && !has_transcript && chat_mode === "unavailable";
    const isTranscriptExpired = is_available && has_transcript && chat_mode === "summary";
    const isSummaryOnly = is_available && !has_transcript && chat_mode === "summary";
    const displayMode = CHAT_MODE_TO_DISPLAY_MODE[chat_mode] || null;

    return {
      isLoading: false,
      isAvailable: Boolean(is_available),
      isIndexing,
      isTranscriptExpired,
      isSummaryOnly,
      isUnauthorized: false,
      chatMode: chat_mode || null,
      displayMode,
    };
  }, [chatStatus, chatStatusLoading]);

  return derived;
};

export default useChatStatus;
