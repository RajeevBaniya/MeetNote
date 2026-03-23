const summaryPresenceCache = new Map();

const getCachedSummaryPresence = (meetingId) => {
  const key = String(meetingId);
  if (!summaryPresenceCache.has(key)) {
    return undefined;
  }
  return summaryPresenceCache.get(key);
};

const setCachedSummaryPresence = (meetingId, hasSummary) => {
  summaryPresenceCache.set(String(meetingId), Boolean(hasSummary));
};

export { getCachedSummaryPresence, setCachedSummaryPresence };
