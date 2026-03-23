const LIVE_TRANSCRIPT_SNAPSHOT_STORAGE_KEY = "live_transcript_snapshot";

const formatSegmentTimestampLabel = (s) => {
  if (!s || typeof s !== "object") {
    return "";
  }
  if (s.start_time || s.stop_time) {
    return String(s.start_time || s.stop_time || "");
  }
  if (s.timestamp == null || s.timestamp === "") {
    return "";
  }
  const d = new Date(s.timestamp);
  if (Number.isNaN(d.getTime())) {
    return String(s.timestamp);
  }
  return d.toLocaleTimeString("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
  });
};

const segmentsToTranscriptText = (segments) => {
  if (!Array.isArray(segments) || segments.length === 0) {
    return "";
  }
  return segments
    .map((s) => {
      const time = formatSegmentTimestampLabel(s);
      const speaker = s.speaker_id || s.speaker || "Speaker";
      const line = s.text || "";
      return time ? `[${time}] ${speaker}: ${line}` : `${speaker}: ${line}`;
    })
    .join("\n");
};

const parseSnapshotPayload = (raw, meetingId) => {
  const parsed = JSON.parse(raw);
  const isValidSegment = (s) => {
    if (!s || typeof s !== "object") return false;
    if (typeof s.text !== "string") return false;
    if (s.sequence != null && !Number.isFinite(Number(s.sequence))) {
      return false;
    }
    return true;
  };

  const isValidSegments = (segments) =>
    Array.isArray(segments) &&
    segments.length > 0 &&
    segments.every(isValidSegment);

  if (Array.isArray(parsed)) {
    return isValidSegments(parsed) ? parsed : null;
  }

  if (!parsed || typeof parsed !== "object" || !Array.isArray(parsed.segments)) {
    return null;
  }

  const expected = meetingId != null ? String(meetingId) : "";
  const got = parsed.meetingId != null ? String(parsed.meetingId) : "";
  if (expected && got !== expected) return null;

  const segments = parsed.segments;
  if (!isValidSegments(segments)) return null;

  return segments;
};

const removeSnapshotFromSessionStorage = () => {
  try {
    sessionStorage.removeItem(LIVE_TRANSCRIPT_SNAPSHOT_STORAGE_KEY);
  } catch {}
};
const scheduleSnapshotStorageCleanup = () => {
  const run = removeSnapshotFromSessionStorage;
  if (typeof window !== "undefined" && typeof window.requestIdleCallback === "function") {
    window.requestIdleCallback(run, { timeout: 2000 });
  } else {
    setTimeout(run, 0);
  }
};
const consumeLiveTranscriptSnapshotFromSession = ({
  meetingId,
  setTranscript,
  setAutoStatus,
  setAutoError,
  composedForNodeRef,
  hasLoadedSnapshotRef,
}) => {
  if (typeof sessionStorage === "undefined") {
    return null;
  }
  let raw = null;
  try {
    raw = sessionStorage.getItem(LIVE_TRANSCRIPT_SNAPSHOT_STORAGE_KEY);
  } catch {
    return null;
  }
  if (!raw) {
    return null;
  }
  try {
    const segments = parseSnapshotPayload(raw, meetingId);
    if (!Array.isArray(segments) || segments.length === 0) {
      return null;
    }
    const text = segmentsToTranscriptText(segments).trim();
    if (!text) {
      return null;
    }
    setAutoError(null);
    if (composedForNodeRef) {
      composedForNodeRef.current = text;
    }
    setTranscript(text);
    setAutoStatus("ready");
    if (hasLoadedSnapshotRef) {
      hasLoadedSnapshotRef.current = true;
    }
    if (hasLoadedSnapshotRef && !hasLoadedSnapshotRef.current) {
      return {
        usedSnapshot: true,
        hadExistingSummary: false,
        segmentCount: segments.length,
      };
    }
    scheduleSnapshotStorageCleanup();
    return {
      usedSnapshot: true,
      hadExistingSummary: false,
      segmentCount: segments.length,
    };
  } catch {
    try {
      sessionStorage.removeItem(LIVE_TRANSCRIPT_SNAPSHOT_STORAGE_KEY);
    } catch {
    }
    return null;
  }
};

const fetchEndedMeetingTranscriptText = async (apiUrl, meetingId, jwt) => {
  const base = (apiUrl || "").replace(/\/$/, "");
  if (!base || !meetingId || !jwt) {
    return { ok: false, text: "", status: 0, error: "missing_config" };
  }
  try {
    const res = await fetch(`${base}/meetings/${meetingId}/transcript`, {
      headers: { Authorization: `Bearer ${jwt}` },
    });
    if (!res.ok) {
      return { ok: false, text: "", status: res.status, error: "http_error" };
    }
    const data = await res.json();
    const segments = Array.isArray(data.segments) ? data.segments : [];
    const chunkSummaries = Array.isArray(data.chunk_summaries)
      ? data.chunk_summaries
      : [];
    const text = segmentsToTranscriptText(segments).trim();
    return {
      ok: true,
      text,
      status: res.status,
      segments,
      chunkSummaries,
    };
  } catch {
    return { ok: false, text: "", status: 0, error: "network" };
  }
};

const fetchMeetingTitle = async (apiUrl, meetingId, jwt) => {
  const base = (apiUrl || "").replace(/\/$/, "");
  if (!base || !meetingId || !jwt) return "";
  try {
    const res = await fetch(`${base}/meetings/${meetingId}`, {
      headers: { Authorization: `Bearer ${jwt}` },
    });
    if (!res.ok) return "";
    const data = await res.json();
    return typeof data.title === "string" ? data.title.trim() : "";
  } catch {
    return "";
  }
};

export {
  LIVE_TRANSCRIPT_SNAPSHOT_STORAGE_KEY,
  consumeLiveTranscriptSnapshotFromSession,
  segmentsToTranscriptText,
  fetchEndedMeetingTranscriptText,
  fetchMeetingTitle,
};
