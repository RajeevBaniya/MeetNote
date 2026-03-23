"use client";

import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";

import { LIVE_TRANSCRIPT_SNAPSHOT_STORAGE_KEY } from "@/app/lib/summary/meeting-transcript";

const STORAGE_KEY_LEAVING = "leaving_for_summarize";

const SNAPSHOT_MAX_WAIT_MS = 2000;
const SNAPSHOT_POLL_INTERVAL_MS = 250;

const getLastSegmentSignature = (segments) => {
  if (!Array.isArray(segments) || segments.length === 0) return "";
  const last = segments[segments.length - 1];
  if (!last) return "";
  const seq = last.sequence != null ? String(last.sequence) : "";
  const speaker = last.speaker_id || last.speaker || "";
  const text = last.text || "";
  const ts = last.timestamp != null ? String(last.timestamp) : "";
  return `${seq}|${speaker}|${text}|${ts}`;
};

const captureStableTranscriptSnapshot = async (getTranscriptSnapshot) => {
  const firstSnapshot = getTranscriptSnapshot?.() || [];
  const firstSignature = getLastSegmentSignature(firstSnapshot);

  const startAt = Date.now();
  let snapshot = firstSnapshot;
  let lastSignature = firstSignature;

  // If the transcript already looks stable, we only wait for one short poll.
  while (Date.now() - startAt < SNAPSHOT_MAX_WAIT_MS) {
    await new Promise((resolve) => setTimeout(resolve, SNAPSHOT_POLL_INTERVAL_MS));
    const nextSnapshot = getTranscriptSnapshot?.() || [];
    const nextSignature = getLastSegmentSignature(nextSnapshot);

    snapshot = nextSnapshot;

    if (nextSignature && nextSignature === lastSignature) {
      break;
    }

    lastSignature = nextSignature;
  }

  return snapshot;
};

export const useLeaveAndSummarize = (call, callId, getTranscriptSnapshot, hasLeftRef) => {
  const router = useRouter();
  const [isSummarizing, setIsSummarizing] = useState(false);
  const [showEmptyInfo, setShowEmptyInfo] = useState(false);

  const handleSummarizeClick = useCallback(async () => {
    if (!call) return;
    if (isSummarizing) return;
    setIsSummarizing(true);
    setShowEmptyInfo(false);

    try {
      const meetingId = callId || "";
      const transcriptSnapshot = await captureStableTranscriptSnapshot(
        getTranscriptSnapshot,
      );
      const lastSegment =
        transcriptSnapshot && transcriptSnapshot.length > 0
          ? transcriptSnapshot[transcriptSnapshot.length - 1]
          : null;
      const lastSequence =
        lastSegment && typeof lastSegment.sequence === "number"
          ? lastSegment.sequence
          : null;
      sessionStorage.setItem(
        LIVE_TRANSCRIPT_SNAPSHOT_STORAGE_KEY,
        JSON.stringify({
          meetingId,
          segments: transcriptSnapshot,
          createdAt: Date.now(),
          lastSequence,
        }),
      );

      sessionStorage.setItem(STORAGE_KEY_LEAVING, callId || "");

      if (hasLeftRef) hasLeftRef.current = true;
      await call.leave();

      const path = `/summarize?source=live${meetingId ? `&meetingId=${encodeURIComponent(meetingId)}` : ""}`;
      router.push(path);
    } catch {
      setIsSummarizing(false);
    }
  }, [call, callId, getTranscriptSnapshot, isSummarizing, hasLeftRef, router]);

  return { handleSummarizeClick, isSummarizing, showEmptyInfo, setShowEmptyInfo };
};

export const checkLeavingForSummarizeAndRedirect = (router, callId) => {
  const stored = sessionStorage.getItem(STORAGE_KEY_LEAVING);
  if (!stored) return false;
  sessionStorage.removeItem(STORAGE_KEY_LEAVING);
  const meetingId = stored || callId || "";
  router.replace(`/summarize?source=live${meetingId ? `&meetingId=${meetingId}` : ""}`);
  return true;
};
