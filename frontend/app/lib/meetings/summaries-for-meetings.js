import { listSummariesForMeeting } from "@/app/lib/summary/summary-api";

import { getCachedSummaryPresence, setCachedSummaryPresence } from "@/app/lib/meetings/summary-presence-cache";
import { runWithLimit } from "@/app/lib/meetings/run-with-limit";

const MAX_CONCURRENT = 5;

const resolveSummaryPresence = async (meetingId) => {
  const cached = getCachedSummaryPresence(meetingId);
  if (cached !== undefined) {
    return { id: meetingId, has_summary: cached };
  }
  try {
    const data = await listSummariesForMeeting(meetingId);
    const items = Array.isArray(data?.items) ? data.items : [];
    const has = items.length > 0;
    setCachedSummaryPresence(meetingId, has);
    return { id: meetingId, has_summary: has };
  } catch {
    setCachedSummaryPresence(meetingId, false);
    return { id: meetingId, has_summary: false };
  }
};

const addSummariesToMeetings = async (meetings) => {
  if (!Array.isArray(meetings) || meetings.length === 0) {
    return [];
  }
  const sorted = [...meetings].sort(
    (a, b) => new Date(b.created_at) - new Date(a.created_at),
  );
  const ended = sorted.filter((m) => !m.is_active);
  const flags = await runWithLimit(ended, MAX_CONCURRENT, (m) =>
    resolveSummaryPresence(m.id),
  );
  const byId = new Map(flags.map((f) => [String(f.id), f.has_summary]));
  return sorted.map((m) => ({
    ...m,
    has_summary: m.is_active ? false : Boolean(byId.get(String(m.id))),
  }));
};

export { addSummariesToMeetings };
