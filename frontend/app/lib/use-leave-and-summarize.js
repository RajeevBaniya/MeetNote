"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";

const STORAGE_KEY_LEAVING = "leaving_for_summarize";
const STORAGE_KEY_TRANSCRIPT = "live_transcript";

function buildTranscriptText(transcripts) {
  return transcripts
    .map((t) => {
      const speaker = t.speaker || t.display_name || t.user_id || "Speaker";
      return `${speaker}: ${t.text}`;
    })
    .join("\n");
}

export function useLeaveAndSummarize(call, callId, getTranscriptSnapshot, hasLeftRef) {
  const router = useRouter();
  const [isSummarizing, setIsSummarizing] = useState(false);
  const [showEmptyInfo, setShowEmptyInfo] = useState(false);

  const handleSummarizeClick = useCallback(async () => {
    if (!call) return;
    const snapshot = getTranscriptSnapshot();
    if (snapshot.length === 0) {
      setShowEmptyInfo(true);
      return;
    }
    if (isSummarizing) return;
    setIsSummarizing(true);

    try {
      const transcriptText = buildTranscriptText(snapshot);
      sessionStorage.setItem(STORAGE_KEY_TRANSCRIPT, transcriptText);
      sessionStorage.setItem(STORAGE_KEY_LEAVING, callId || "");

      if (hasLeftRef) hasLeftRef.current = true;
      await call.leave();

      const meetingId = callId || "";
      const path = `/summarize?source=live${meetingId ? `&meetingId=${meetingId}` : ""}`;
      router.push(path);
    } catch {
      setIsSummarizing(false);
    }
  }, [call, callId, getTranscriptSnapshot, isSummarizing, hasLeftRef]);

  return { handleSummarizeClick, isSummarizing, showEmptyInfo, setShowEmptyInfo };
}

export function checkLeavingForSummarizeAndRedirect(router, callId) {
  const stored = sessionStorage.getItem(STORAGE_KEY_LEAVING);
  if (!stored) return false;
  sessionStorage.removeItem(STORAGE_KEY_LEAVING);
  const meetingId = stored || callId || "";
  router.replace(`/summarize?source=live${meetingId ? `&meetingId=${meetingId}` : ""}`);
  return true;
}
