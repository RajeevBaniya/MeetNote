import { apiFetch } from "@/app/summarize/lib/api";

const DEFAULT_MEETING_SUMMARY_INSTRUCTION =
  "Summarize this meeting with key points, action items, and decisions";

const generateMeetingSummary = async ({
  transcript,
  instruction,
  meetingId,
  meetingTitle,
  meetingDate,
  meetingType,
  participants,
  location,
  tags,
  persist = true,
}) => {
  const body = {
    transcript,
    instruction: instruction || DEFAULT_MEETING_SUMMARY_INSTRUCTION,
    title: meetingTitle ? `Summary — ${meetingTitle}` : new Date().toLocaleString(),
    meetingId: meetingId || null,
    meetingTitle: meetingTitle || null,
    meetingDate: meetingDate || null,
    meetingType: meetingType || null,
    participants: participants || [],
    location: location || null,
    tags: tags || [],
    extractStructured: true,
    persist,
  };
  return apiFetch("/api/summary/generate", {
    method: "POST",
    body: JSON.stringify(body),
  });
};

const listSummariesForMeeting = async (meetingId, take = 50) => {
  if (!meetingId) {
    return { items: [] };
  }
  const q = new URLSearchParams({
    meetingId: String(meetingId),
    take: String(take),
    sortBy: "created_at",
    sortOrder: "desc",
  });
  return apiFetch(`/api/summaries?${q.toString()}`);
};

export {
  DEFAULT_MEETING_SUMMARY_INSTRUCTION,
  generateMeetingSummary,
  listSummariesForMeeting,
};
