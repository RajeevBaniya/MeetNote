"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";

import HistoryView from "./components/history/history-view";
import SummarizeNavbar from "./components/navbar/summarize-navbar";
import SummarizeWorkspace from "./components/summary/workspace";

import { apiFetch } from "./lib/api";
import { useLiveSummary } from "./lib/use-live-summary";

const getInitialMeetingData = () => ({
  meetingTitle: "",
  meetingDate: "",
  meetingType: "",
  participants: [],
  location: "",
  tags: [],
});

const SummarizePageContent = () => {
  const searchParams = useSearchParams();
  const source = searchParams.get("source") || "upload";
  const meetingId = searchParams.get("meetingId") || null;
  const summaryIdFromUrl = searchParams.get("id") || null;
  const viewHistory = searchParams.get("view") === "history";

  const [transcript, setTranscript] = useState("");
  const [summary, setSummary] = useState("");
  const [structured, setStructured] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [showHistory, setShowHistory] = useState(viewHistory);
  const [meetingData, setMeetingData] = useState(getInitialMeetingData);
  const [currentSummaryId, setCurrentSummaryId] = useState(null);
  const [loadingSummaryById, setLoadingSummaryById] = useState(false);

  const didAutoSelectLatestRef = useRef(false);

  const {
    transcriptLoading,
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
  } = useLiveSummary({
    source,
    meetingId,
    meetingData,
    setTranscript,
    setSummary,
    setStructured,
    setCurrentSummaryId,
    setIsLoading,
  });

  const handleSelectSummary = useCallback((selectedSummary) => {
    resetLivePreview();
    setTranscript(selectedSummary.transcript);
    setSummary(selectedSummary.summary);
    setStructured({
      actionItems: selectedSummary.action_items || [],
      decisions: selectedSummary.decisions || [],
      deadlines: selectedSummary.deadlines || [],
      participants: selectedSummary.extracted_participants || [],
    });
    setMeetingData({
      meetingTitle: selectedSummary.meeting_title || "",
      meetingDate: selectedSummary.meeting_date
        ? new Date(selectedSummary.meeting_date).toISOString().slice(0, 16)
        : "",
      meetingType: selectedSummary.meeting_type || "",
      participants: selectedSummary.participants || [],
      location: selectedSummary.location || "",
      tags: selectedSummary.tags || [],
    });
    setCurrentSummaryId(selectedSummary.id);
    setShowHistory(false);
    if (source === "live") {
      onLiveSummarySelected(selectedSummary.transcript ?? "");
    }
  }, [resetLivePreview, source, onLiveSummarySelected]);

  useEffect(() => {
    didAutoSelectLatestRef.current = false;
  }, [meetingId]);

  useEffect(() => {
    if (!meetingId || source === "live" || summaryIdFromUrl) return;
    if (!meetingSummaries?.length || summary) return;
    if (didAutoSelectLatestRef.current) return;
    didAutoSelectLatestRef.current = true;
    handleSelectSummary(meetingSummaries[0]);
  }, [
    meetingId,
    source,
    meetingSummaries,
    summary,
    summaryIdFromUrl,
    handleSelectSummary,
  ]);

  useEffect(() => {
    if (!summaryIdFromUrl) return;
    let cancelled = false;
    setLoadingSummaryById(true);
    apiFetch(`/api/summaries/${summaryIdFromUrl}`)
      .then((data) => {
        if (cancelled || !data?.item) return;
        handleSelectSummary(data.item);
      })
      .catch((err) => {
        console.error("Load summary by id failed:", err);
      })
      .finally(() => {
        if (!cancelled) setLoadingSummaryById(false);
      });
    return () => {
      cancelled = true;
    };
  }, [summaryIdFromUrl, handleSelectSummary]);

  const handleNewSummary = () => {
    resetLiveSession();
    setTranscript("");
    setSummary("");
    setStructured(null);
    setMeetingData(getInitialMeetingData());
    setCurrentSummaryId(null);
    setShowHistory(false);
  };

  const showUpload = source === "upload";

  return (
    <div className="main-container logged-in-container">
      <SummarizeNavbar />
      <div className="content-wrapper">
        <header className="header-section logged-in-header">
          <button
            onClick={() => {
              if (showHistory) {
                handleNewSummary();
              } else {
                setShowHistory(true);
              }
            }}
            className="primary-button history-toggle-btn"
          >
            <span className="history-toggle-text-desktop">
              {showHistory ? "New Summary" : "View History"}
            </span>
            <span className="history-toggle-text-mobile">
              {showHistory ? "New" : "History"}
            </span>
          </button>
        </header>

        {loadingSummaryById ? (
          <div className="card">
            <div className="loading-container">
              <div className="loading-spinner" />
              <p className="mt-3 text-sm text-slate-400">Loading summary…</p>
            </div>
          </div>
        ) : showHistory ? (
          <HistoryView
            onSelectSummary={handleSelectSummary}
            uploadOnly={viewHistory}
          />
        ) : (
          <SummarizeWorkspace
            meetingId={meetingId}
            meetingSummaries={meetingSummaries}
            summariesLoading={summariesLoading}
            onSelectSummary={handleSelectSummary}
            source={source}
            autoError={autoError}
            transcriptLoading={transcriptLoading}
            showUpload={showUpload}
            transcript={transcript}
            setTranscript={setTranscript}
            meetingData={meetingData}
            setMeetingData={setMeetingData}
            summary={summary}
            setSummary={setSummary}
            structured={structured}
            setStructured={setStructured}
            isLoading={isLoading}
            setIsLoading={setIsLoading}
            currentSummaryId={currentSummaryId}
            setCurrentSummaryId={setCurrentSummaryId}
            briefNotice={briefNotice}
            hasGenerated={hasGenerated}
            hasExistingSummary={hasExistingSummary}
            isGeneratingRef={isGeneratingRef}
            onGenerateLiveSummary={handleGenerateSummary}
          />
        )}
      </div>
    </div>
  );
};

export default SummarizePageContent;
