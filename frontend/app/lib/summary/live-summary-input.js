import { segmentsToTranscriptText } from "./meeting-transcript";

const LIVE_SUMMARY_MAX_INPUT_CHARS = 48_000;

const CHUNK_HEADER = "Prior meeting chunk summaries (from Redis chunking pipeline):\n\n";
const TRANSCRIPT_HEADER = "\n\nRecent transcript (verbatim):\n\n";

const tailChars = (text, max) => {
  if (!text || max <= 0) {
    return "";
  }
  if (text.length <= max) {
    return text;
  }
  return text.slice(-max);
};

const buildTranscriptForSummaryGeneration = ({
  segments,
  chunkSummaries,
  maxChars = LIVE_SUMMARY_MAX_INPUT_CHARS,
}) => {
  const segList = Array.isArray(segments) ? segments : [];
  const chunkList = Array.isArray(chunkSummaries)
    ? chunkSummaries.filter((c) => typeof c === "string" && c.trim())
    : [];

  const fullTranscript = segmentsToTranscriptText(segList).trim();
  const chunksJoined = chunkList.join("\n\n---\n\n");

  if (!chunksJoined) {
    return tailChars(fullTranscript, maxChars);
  }

  if (!fullTranscript) {
    return tailChars(chunksJoined, maxChars);
  }

  const overhead = CHUNK_HEADER.length + TRANSCRIPT_HEADER.length;
  const maxChunks = Math.min(
    chunksJoined.length,
    Math.floor(maxChars * 0.45),
  );
  const chunksBody =
    chunksJoined.length > maxChunks
      ? `${chunksJoined.slice(0, maxChunks)}\n…`
      : chunksJoined;

  const chunksSection = `${CHUNK_HEADER}${chunksBody}`;
  const transBudget = Math.max(0, maxChars - overhead - chunksSection.length);
  const tailTranscript = tailChars(fullTranscript, transBudget);

  return `${chunksSection}${TRANSCRIPT_HEADER}${tailTranscript}`;
};

export {
  LIVE_SUMMARY_MAX_INPUT_CHARS,
  buildTranscriptForSummaryGeneration,
};
