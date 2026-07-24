"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { listSummariesForMeeting } from "@/app/lib/summary/summary-api";
import { getToken } from "@/app/lib/auth/token-store";

import {
  generateLiveMeetingPreview,
  prepareLiveMeetingTranscript,
} from "./live-summary-run";
import { sortSummariesByCreatedAtDesc } from "./sort-summaries";

const useLiveSummary = ({
  source,
  meetingId,
  meetingData,
  setTranscript,
  setSummary,
  setStructured,
  setCurrentSummaryId,
  setIsLoading,
}) => {
  const meetingDataRef = useRef(meetingData);
  meetingDataRef.current = meetingData;

  const composedForNodeRef = useRef("");
  const liveSegmentCountRef = useRef(0);
  const hasPreparedRef = useRef(false);
  const snapshotLoadedRef = useRef(false);
  const isGeneratingRef = useRef(false);

  const [transcriptLoading, setTranscriptLoading] = useState(false);
  const [autoStatus, setAutoStatus] = useState("idle");
  const [autoError, setAutoError] = useState(null);
  const [meetingSummaries, setMeetingSummaries] = useState([]);
  const [summariesLoading, setSummariesLoading] = useState(false);
  const [briefNotice, setBriefNotice] = useState("");
  const [hasGenerated, setHasGenerated] = useState(false);
  const [hasExistingSummary, setHasExistingSummary] = useState(false);

  useEffect(() => {
    if (!meetingId) {
      setMeetingSummaries([]);
      return;
    }
    let cancelled = false;
    setSummariesLoading(true);
    listSummariesForMeeting(meetingId)
      .then((data) => {
        if (cancelled || !data?.items) return;
        setMeetingSummaries(sortSummariesByCreatedAtDesc(data.items));
      })
      .catch(() => {
        if (!cancelled) setMeetingSummaries([]);
      })
      .finally(() => {
        if (!cancelled) setSummariesLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [meetingId]);

  useEffect(() => {
    if (source !== "live" || !meetingId) {
      setBriefNotice("");
    }
  }, [source, meetingId]);

  useEffect(() => {
    hasPreparedRef.current = false;
    snapshotLoadedRef.current = false;
    isGeneratingRef.current = false;
  }, [meetingId]);

  useEffect(() => {
    if (source !== "live" || !meetingId) {
      setHasGenerated(false);
      setHasExistingSummary(false);
      setAutoStatus("idle");
      setAutoError(null);
      liveSegmentCountRef.current = 0;
      return;
    }

    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    const jwt = getToken();
    if (!apiUrl || !jwt) {
      setAutoStatus("error");
      setAutoError("Sign in required to load transcript.");
      setHasGenerated(false);
      setHasExistingSummary(false);
      return;
    }

    let cancelled = false;
    const isCancelled = () => cancelled;

    if (snapshotLoadedRef.current) {
      return () => {
        cancelled = true;
      };
    }

    if (hasPreparedRef.current) {
      return () => {
        cancelled = true;
      };
    }
    hasPreparedRef.current = true;

    setHasGenerated(false);
    setHasExistingSummary(false);
    setSummary("");
    setStructured(null);
    setCurrentSummaryId(null);
    liveSegmentCountRef.current = 0;

    (async () => {
      const result = await prepareLiveMeetingTranscript({
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
      });
      if (cancelled || !result) return;
      if (result.skipped) {
        return;
      }
      if (result.usedSnapshot) {
        snapshotLoadedRef.current = true;
        liveSegmentCountRef.current = result.segmentCount ?? 0;
        return;
      }
      if (result.hadExistingSummary) {
        setHasExistingSummary(true);
        return;
      }
      liveSegmentCountRef.current = result.segmentCount ?? 0;
    })();

    return () => {
      cancelled = true;
    };
  }, [
    source,
    meetingId,
    setTranscript,
    setSummary,
    setStructured,
    setCurrentSummaryId,
  ]);

  const handleGenerateSummary = useCallback(async (instructionOverride) => {
    if (source !== "live" || !meetingId) {
      return;
    }
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    const jwt = getToken();
    if (!apiUrl || !jwt) {
      setAutoError("Sign in required to generate summary.");
      return;
    }
    const isCancelled = () => false;
    const ok = await generateLiveMeetingPreview({
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
      segmentCount: liveSegmentCountRef.current,
      isGeneratingRef,
      ...(typeof instructionOverride === "string" && instructionOverride.trim()
        ? { instruction: instructionOverride.trim() }
        : {}),
    });
    if (ok) {
      setHasExistingSummary(false);
      setHasGenerated(true);
      try {
        const refreshed = await listSummariesForMeeting(meetingId);
        if (refreshed?.items) {
          setMeetingSummaries(sortSummariesByCreatedAtDesc(refreshed.items));
        }
      } catch {
        // ignore list refresh errors
      }
    }
  }, [
    source,
    meetingId,
    setSummary,
    setStructured,
    setCurrentSummaryId,
    setIsLoading,
  ]);

  const onLiveSummarySelected = useCallback((transcriptText) => {
    setHasGenerated(false);
    setHasExistingSummary(true);
    const t = (transcriptText ?? "").trim();
    if (t) {
      composedForNodeRef.current = t;
    }
  }, []);

  const resetLivePreview = useCallback(() => {
    setBriefNotice("");
    composedForNodeRef.current = "";
  }, []);

  const resetLiveSession = useCallback(() => {
    resetLivePreview();
    setHasGenerated(false);
    setHasExistingSummary(false);
  }, [resetLivePreview]);

  return {
    transcriptLoading,
    autoStatus,
    autoError,
    meetingSummaries,
    summariesLoading,
    briefNotice,
    resetLivePreview,
    resetLiveSession,
    hasGenerated,
    hasExistingSummary,
    isGeneratingRef,
    handleGenerateSummary,
    onLiveSummarySelected,
  };
};

export { useLiveSummary };
