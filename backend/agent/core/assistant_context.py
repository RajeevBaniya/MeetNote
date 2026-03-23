import logging
import re
from typing import List, Optional

from redis.asyncio import Redis

from agent.config.agent_constants import AgentConstants
from agent.core.transcript_types import TranscriptEntry


logger = logging.getLogger(__name__)

SUMMARY_CHUNKS_KEY_PREFIX = "summary_chunks:"


async def fetch_summary_chunks_text(
    redis: Optional[Redis],
    meeting_id: str,
) -> str:
    if redis is None:
        return ""
    key = f"{SUMMARY_CHUNKS_KEY_PREFIX}{meeting_id}"
    try:
        parts = await redis.lrange(key, 0, -1)
        if not parts:
            return ""
        return "\n\n".join(str(p) for p in parts if p)
    except Exception as exc:
        logger.debug("assistant_chunks_read_failed meeting_id=%s: %s", meeting_id, exc)
        return ""


def transcript_entries_for_context(
    entries: List[TranscriptEntry],
) -> List[TranscriptEntry]:
    limit = AgentConstants.ASSISTANT_CONTEXT_TRANSCRIPT_SEGMENTS
    return entries[-limit:] if len(entries) > limit else entries


def build_transcript_history_text(entries: List[TranscriptEntry]) -> str:
    sliced = transcript_entries_for_context(entries)
    return " ".join(entry.text for entry in sliced)


MIN_TRANSCRIPT_SEGMENTS_FOR_REPLY = 3


def build_reply_from_context(
    question: str,
    transcript_history: str,
    chunks_text: str,
    transcript_segment_count: int,
) -> str:
    if transcript_segment_count < MIN_TRANSCRIPT_SEGMENTS_FOR_REPLY:
        return "Not enough context yet. Please ask again in a moment."

    combined_for_match = f"{transcript_history} {chunks_text}".strip()
    if not combined_for_match.lower():
        return "I do not have enough context from this meeting yet."

    history_lower = combined_for_match.lower()
    question_lower = question.lower()

    words = re.findall(r"\w+", question_lower)
    stop_words = {
        "the",
        "is",
        "are",
        "was",
        "were",
        "what",
        "where",
        "who",
        "when",
        "how",
        "a",
        "an",
        "of",
        "for",
        "in",
        "to",
        "about",
        "this",
        "that",
        "did",
        "do",
        "we",
        "you",
        "i",
        "and",
        "or",
        "on",
        "at",
        "from",
        "our",
        "your",
        "meeting",
    }
    keywords = [w for w in words if w not in stop_words]

    if keywords and not any(k in history_lower for k in keywords):
        return "That was not discussed in this meeting."

    short_question = question.strip()
    if len(short_question) > AgentConstants.MAX_QUESTION_LENGTH:
        short_question = (
            short_question[: AgentConstants.MAX_QUESTION_LENGTH] + "..."
        )

    context_block_parts = []
    if transcript_history.strip():
        context_block_parts.append(transcript_history.strip())
    if chunks_text.strip():
        context_block_parts.append(f"Earlier summary notes: {chunks_text.strip()}")

    context_block = " ".join(context_block_parts)
    if len(context_block) > AgentConstants.MAX_HISTORY_LENGTH:
        context_block = context_block[: AgentConstants.MAX_HISTORY_LENGTH] + "..."

    return (
        "Based strictly on what was said in this meeting, "
        f"here is a focused answer to your question '{short_question}'. "
        f"Relevant context: {context_block}"
    )
