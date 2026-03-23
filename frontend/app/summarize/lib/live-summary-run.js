import { buildTranscriptForSummaryGeneration } from "@/app/lib/summary/live-summary-input";
import {
  consumeLiveTranscriptSnapshotFromSession,
  fetchEndedMeetingTranscriptText,
  fetchMeetingTitle,
} from "@/app/lib/summary/meeting-transcript";
import {
  DEFAULT_MEETING_SUMMARY_INSTRUCTION,
  generateMeetingSummary,
  listSummariesForMeeting,
} from "@/app/lib/summary/summary-api";

import { applySummaryItemToState } from "./summary-state";
import {
  BRIEF_NOTICE_MIN_SEGMENTS,
  MSG_BRIEF_TRANSCRIPT,
  MSG_TRANSCRIPT_EMPTY,
  MSG_TRANSCRIPT_UNAVAILABLE,
} from "./live-summary-defaults";
import { sortSummariesByCreatedAtDesc } from "./sort-summaries";

const shouldClearTranscript = (usedSnapshot, snapshotLoadedRef) =>
  !usedSnapshot && !snapshotLoadedRef?.current;

const prepareLiveMeetingTranscript = async ({
  isCancelled,
  meetingId,
  apiUrl,
  jwt,
  meetingDataRef,
  setTranscript,
  setSummary,
  setStructured,
  setCurrentSummaryId,
  setMeetingSummaries,
  setAutoStatus,
  setAutoError,
  setTranscriptLoading,
  composedForNodeRef,
  snapshotLoadedRef,
}) => {
  const bailIfCancelled = () => isCancelled();

  let usedSnapshot = false;

  setAutoError(null);
  setAutoStatus("idle");

  if (snapshotLoadedRef?.current) {
    return { skipped: true, hadExistingSummary: false };
  }

  const snapshotResult = consumeLiveTranscriptSnapshotFromSession({
    meetingId,
    setTranscript,
    setAutoStatus,
    setAutoError,
    composedForNodeRef,
    hasLoadedSnapshotRef: snapshotLoadedRef,
  });
  if (snapshotResult) {
    usedSnapshot = true;
    if (bailIfCancelled()) {
      return { hadExistingSummary: false };
    }
    return snapshotResult;
  }

  if (composedForNodeRef && shouldClearTranscript(usedSnapshot, snapshotLoadedRef)) {
    composedForNodeRef.current = "";
  }

  const listData = await listSummariesForMeeting(meetingId);
  if (bailIfCancelled()) {
    return { hadExistingSummary: false };
  }

  const sortedExisting = sortSummariesByCreatedAtDesc(listData?.items);
  setMeetingSummaries(sortedExisting);

  if (sortedExisting.length > 0) {
    const latest = sortedExisting[0];
    applySummaryItemToState(latest, {
      setTranscript,
      setSummary,
      setStructured,
      setCurrentSummaryId,
    });
    if (composedForNodeRef) {
      composedForNodeRef.current = (latest.transcript ?? "").trim();
    }
    setAutoStatus("done");
    return { hadExistingSummary: true };
  }

  setTranscriptLoading(true);

  await fetchMeetingTitle(apiUrl, meetingId, jwt);
  if (bailIfCancelled()) {
    setTranscriptLoading(false);
    return { hadExistingSummary: false };
  }

  const transcriptResult = await fetchEndedMeetingTranscriptText(
    apiUrl,
    meetingId,
    jwt,
  );
  if (bailIfCancelled()) {
    setTranscriptLoading(false);
    return { hadExistingSummary: false };
  }

  setTranscriptLoading(false);

  if (!transcriptResult.ok) {
    if (composedForNodeRef && shouldClearTranscript(usedSnapshot, snapshotLoadedRef)) {
      composedForNodeRef.current = "";
    }
    if (shouldClearTranscript(usedSnapshot, snapshotLoadedRef)) {
      setTranscript("");
    }
    setAutoStatus("error");
    setAutoError(MSG_TRANSCRIPT_UNAVAILABLE);
    return { hadExistingSummary: false };
  }

  const segments = Array.isArray(transcriptResult.segments)
    ? transcriptResult.segments
    : [];
  const chunkSummaries = Array.isArray(transcriptResult.chunkSummaries)
    ? transcriptResult.chunkSummaries
    : [];
  const displayText = (transcriptResult.text || "").trim();

  const composedForNode = buildTranscriptForSummaryGeneration({
    segments,
    chunkSummaries,
  }).trim();

  if (!composedForNode) {
    if (shouldClearTranscript(usedSnapshot, snapshotLoadedRef)) {
      setTranscript("");
    }
    if (composedForNodeRef && shouldClearTranscript(usedSnapshot, snapshotLoadedRef)) {
      composedForNodeRef.current = "";
    }
    setAutoStatus("error");
    setAutoError(MSG_TRANSCRIPT_EMPTY);
    return { hadExistingSummary: false };
  }

  if (composedForNodeRef) {
    composedForNodeRef.current = composedForNode;
  }

  setTranscript(displayText);
  setAutoStatus("ready");
  return { hadExistingSummary: false, segmentCount: segments.length };
};

const generateLiveMeetingPreview = async ({
  isCancelled,
  meetingId,
  apiUrl,
  jwt,
  meetingDataRef,
  setSummary,
  setStructured,
  setCurrentSummaryId,
  setIsLoading,
  setAutoStatus,
  setAutoError,
  setBriefNotice,
  composedForNodeRef,
  segmentCount = 0,
  instruction = DEFAULT_MEETING_SUMMARY_INSTRUCTION,
  isGeneratingRef,
}) => {
  const bailIfCancelled = () => {
    if (!isCancelled()) {
      return false;
    }
    setIsLoading(false);
    return true;
  };

  const composed = (composedForNodeRef?.current || "").trim();
  if (!composed || !meetingId) {
    setAutoError(MSG_TRANSCRIPT_EMPTY);
    return false;
  }

  if (isGeneratingRef) {
    if (isGeneratingRef.current) return false;
    isGeneratingRef.current = true;
  }

  try {
    const md = meetingDataRef.current;
    const title = await fetchMeetingTitle(apiUrl, meetingId, jwt);
    if (bailIfCancelled()) return false;

    setAutoStatus("loading");
    setAutoError(null);
    setIsLoading(true);
    setBriefNotice("");

    const response = await generateMeetingSummary({
      transcript: composed,
      instruction,
      meetingId,
      persist: true,
      meetingTitle: title || md.meetingTitle || null,
      meetingDate: md.meetingDate || null,
      meetingType: md.meetingType || null,
      participants: md.participants || [],
      location: md.location || null,
      tags: md.tags || [],
    });

    if (bailIfCancelled()) return false;

    setSummary(response.summary || "");
    if (response.structured) {
      setStructured({
        actionItems: response.structured.actionItems || [],
        decisions: response.structured.decisions || [],
        deadlines: response.structured.deadlines || [],
        participants: response.structured.participants || [],
      });
    }
    if (response.savedId) {
      setCurrentSummaryId(response.savedId);
    } else {
      setCurrentSummaryId(null);
    }
    if (segmentCount < BRIEF_NOTICE_MIN_SEGMENTS) {
      setBriefNotice(MSG_BRIEF_TRANSCRIPT);
    } else {
      setBriefNotice("");
    }
    setAutoStatus("done");
    return true;
  } catch (err) {
    if (!isCancelled()) {
      setAutoStatus("error");
      setAutoError(
        err?.message || "Summary not available. Please try again.",
      );
    }
    return false;
  } finally {
    if (isGeneratingRef) {
      isGeneratingRef.current = false;
    }
    if (!isCancelled()) {
      setIsLoading(false);
    }
  }
};

export { generateLiveMeetingPreview, prepareLiveMeetingTranscript };
