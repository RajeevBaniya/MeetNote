"use client";

import { useState, useEffect, Suspense, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import FileUpload from "./components/FileUpload";
import SummaryGenerator from "./components/SummaryGenerator";
import SummaryEditor from "./components/SummaryEditor";
import EmailSender from "./components/EmailSender";
import Navbar from "./components/Navbar";
import HistoryView from "./components/HistoryView";
import MeetingDetails from "./components/MeetingDetails";
import StructuredSummary from "./components/StructuredSummary";
import { apiFetch } from "./lib/api";

function getInitialMeetingData() {
  return {
    meetingTitle: "",
    meetingDate: "",
    meetingType: "",
    participants: [],
    location: "",
    tags: [],
  };
}

const SummarizeContent = () => {
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

  const handleSelectSummary = useCallback((selectedSummary) => {
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
  }, []);

  useEffect(() => {
    if (source === "live") {
      const storedTranscript = sessionStorage.getItem("live_transcript");
      if (storedTranscript && storedTranscript.trim()) {
        setTranscript(storedTranscript);
        sessionStorage.removeItem("live_transcript");
      }
    }
  }, [source]);

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
      <Navbar />
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
          <div
            className={`layout-container ${summary ? "summary-active" : ""}`}
          >
            <div className="left-content">
              <MeetingDetails
                meetingData={meetingData}
                onUpdate={setMeetingData}
              />

              {showUpload && (
                <div className="mt-3 sm:mt-4 lg:mt-6">
                  <FileUpload
                    onFileUpload={setTranscript}
                    transcript={transcript}
                  />
                </div>
              )}

              {!showUpload && (
                <div className="mt-3 sm:mt-4 lg:mt-6">
                  {transcript ? (
                    <div className="card">
                      <h2 className="section-title mb-4">Live Transcript</h2>
                      <div className="transcript-preview">
                        <p className="text-sm text-slate-300 whitespace-pre-wrap">
                          {transcript}
                        </p>
                      </div>
                    </div>
                  ) : (
                    <div className="card">
                      <h2 className="section-title mb-4">Live Transcript</h2>
                      <div className="transcript-preview">
                        <p className="text-sm text-slate-400">
                          No transcript available. Please go back to the meeting
                          and ensure transcripts are being captured.
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              )}

              <div className="mt-3 sm:mt-4 lg:mt-6">
                <SummaryGenerator
                  transcript={transcript}
                  setSummary={setSummary}
                  setStructured={setStructured}
                  isLoading={isLoading}
                  setIsLoading={setIsLoading}
                  meetingData={meetingData}
                  setSummaryId={setCurrentSummaryId}
                  meetingId={meetingId}
                />
              </div>
            </div>

            {summary && (
              <div className="right-content">
                <SummaryEditor
                  summary={summary}
                  setSummary={setSummary}
                  summaryId={currentSummaryId}
                  meetingTitle={meetingData.meetingTitle}
                />

                {structured && (
                  <div className="mt-3 sm:mt-4 lg:mt-6">
                    <StructuredSummary
                      structured={structured}
                      manualParticipants={meetingData.participants}
                    />
                  </div>
                )}

                <div className="mt-3 sm:mt-4 lg:mt-6">
                  <EmailSender summary={summary} />
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

const SummarizePage = () => {
  return (
    <Suspense
      fallback={
        <div className="main-container logged-in-container">
          <div className="content-wrapper">
            <div className="card">
              <div className="loading-container">
                <div className="loading-spinner" />
              </div>
            </div>
          </div>
        </div>
      }
    >
      <SummarizeContent />
    </Suspense>
  );
};

export default SummarizePage;
