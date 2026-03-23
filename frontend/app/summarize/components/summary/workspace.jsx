"use client";

import EmailSender from "../email/email-sender";
import FileUpload from "../file/file-upload";
import MeetingDetails from "./meeting-details";
import MeetingSummariesList from "./meeting-summaries-list";
import StructuredSummary from "./structured-summary";
import SummaryEditor from "./summary-editor";
import SummaryGenerator from "./summary-generator";

const SummarizeWorkspace = ({
  meetingId,
  meetingSummaries,
  summariesLoading,
  onSelectSummary,
  source,
  autoError,
  transcriptLoading,
  showUpload,
  transcript,
  setTranscript,
  meetingData,
  setMeetingData,
  summary,
  setSummary,
  structured,
  setStructured,
  isLoading,
  setIsLoading,
  currentSummaryId,
  setCurrentSummaryId,
  briefNotice,
  hasGenerated,
  hasExistingSummary = false,
  isGeneratingRef,
  onGenerateLiveSummary,
}) => {
  const showMeetingList =
    meetingId && !(source === "live" && !hasGenerated);

  const showLiveBriefNotice =
    source === "live" &&
    meetingId &&
    hasGenerated &&
    briefNotice &&
    !autoError;

  const showSummaryColumn =
    source === "live"
      ? Boolean((hasGenerated || hasExistingSummary) && summary)
      : Boolean(summary);

  return (
    <div
      className={`layout-container ${showSummaryColumn ? "summary-active" : ""}`}
    >
      <div className="left-content">
        <MeetingDetails meetingData={meetingData} onUpdate={setMeetingData} />

        {showMeetingList ? (
          <MeetingSummariesList
            items={meetingSummaries}
            loading={summariesLoading}
            onSelectSummary={onSelectSummary}
          />
        ) : null}

        {source === "live" && meetingId && autoError ? (
          <div className="card mb-4 border border-amber-600/40 bg-amber-950/30">
            <p className="text-sm text-amber-200">{autoError}</p>
          </div>
        ) : null}

        {source === "live" && meetingId && transcriptLoading ? (
          <div className="card mb-4">
            <p className="text-sm text-slate-400">Loading transcript…</p>
          </div>
        ) : null}

        {showLiveBriefNotice ? (
          <div className="card mb-4 border border-sky-600/40 bg-sky-950/30">
            <p className="text-sm text-sky-100">{briefNotice}</p>
          </div>
        ) : null}

        {showUpload && (
          <div className="mt-3 sm:mt-4 lg:mt-6">
            <FileUpload onFileUpload={setTranscript} transcript={transcript} />
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
                    No transcript available. Please go back to the meeting and
                    ensure transcripts are being captured.
                  </p>
                </div>
              </div>
            )}
          </div>
        )}

        {showUpload ? (
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
        ) : null}

        {source === "live" && meetingId && transcript && transcript.trim() ? (
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
              onLiveGenerate={onGenerateLiveSummary}
              isGeneratingRef={isGeneratingRef}
            />
          </div>
        ) : null}
      </div>

      {showSummaryColumn ? (
        <div className="right-content">
          {source === "live" &&
          hasExistingSummary &&
          !hasGenerated &&
          summary ? (
            <div className="card mb-4 border border-slate-600/40 bg-slate-950/25">
              <p className="text-sm text-slate-300">
                Saved summary for this meeting. Generate a new summary below to
                create a new saved version.
              </p>
            </div>
          ) : null}

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
      ) : null}
    </div>
  );
};

export default SummarizeWorkspace;
