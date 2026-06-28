import asyncio
import logging
from uuid import UUID

from redis.asyncio import Redis
from sqlalchemy import select

from app.core.config import TRANSCRIPT_SEGMENT_THRESHOLD
from app.db.models import MeetingTranscript
from app.db.session import async_session_factory
from app.modules.transcripts.segment_storage import (
    append_transcript_segment as _append_segment,
)
from app.modules.transcripts.segment_storage import (
    delete_transcript_state,
    expire_transcript_keys,
    get_live_transcript,
    get_segment_count,
    get_transcript_segments,
    has_user_left,
    mark_user_left,
)
from app.modules.transcripts.summarization import (
    generate_final_summary,
    process_transcript_chunk,
)
from app.state.client import get_redis


logger = logging.getLogger(__name__)


async def append_transcript_segment(
    redis: Redis,
    meeting_id: UUID,
    text: str,
    speaker_id: str | None = None,
    speaker_name: str | None = None,
    timestamp: str | None = None,
    confidence: float | None = None,
) -> None:
    await _append_segment(
        redis,
        meeting_id,
        text,
        speaker_id=speaker_id,
        speaker_name=speaker_name,
        timestamp=timestamp,
        confidence=confidence,
    )
    length = await get_segment_count(redis, meeting_id)
    if length >= TRANSCRIPT_SEGMENT_THRESHOLD:
        asyncio.create_task(process_transcript_chunk(redis, meeting_id))


async def get_transcript_history_segments(
    meeting_id: UUID,
    user_id: UUID,
    limit: int,
) -> list[dict[str, object]]:
    redis = await get_redis()
    normalized_limit = min(max(int(limit), 1), 2000)
    if await has_user_left(redis, meeting_id, user_id):
        raise PermissionError("transcript_unavailable")

    # REST history must return segments ordered ascending by `sequence`.
    # Source of truth is `transcript:segments:{meeting_id}` list.
    raw_items = await get_transcript_segments(
        redis,
        meeting_id,
        limit=normalized_limit,
    )
    segments: list[dict[str, object]] = []

    if not raw_items:
        try:
            async with async_session_factory() as session:
                async with session.begin():
                    stmt = (
                        select(MeetingTranscript)
                        .where(MeetingTranscript.meeting_id == meeting_id)
                        .order_by(MeetingTranscript.sequence.desc())
                        .limit(normalized_limit)
                    )
                    res = await session.execute(stmt)
                    db_segments = res.scalars().all()
                    for seg in reversed(db_segments):
                        segments.append(
                            {
                                "sequence": seg.sequence,
                                "segment_id": str(seg.id),
                                "speaker_id": seg.speaker_id or "",
                                "speaker_name": seg.speaker_name or "",
                                "text": seg.text_content,
                                "original_text": seg.text_content,
                                "timestamp": seg.timestamp.isoformat() if seg.timestamp else "",
                            }
                        )
        except Exception as exc:
            logger.exception(
                "failed_to_fallback_read_transcript_from_db",
                extra={"meeting_id": str(meeting_id)},
                exc_info=exc,
            )
    else:
        for item in raw_items:
            speaker_id = item.get("speaker_id")
            speaker_name = item.get("speaker_name") or speaker_id or ""
            sequence_value = item.get("sequence")
            try:
                sequence = int(sequence_value)  # type: ignore[arg-type]
            except (TypeError, ValueError):
                sequence = 0

            segments.append(
                {
                    "sequence": sequence,
                    "segment_id": str(item.get("segment_id") or ""),
                    "speaker_id": str(speaker_id) if speaker_id is not None else "",
                    "speaker_name": str(speaker_name),
                    "text": str(item.get("corrected_text") or item.get("text") or ""),
                    "original_text": str(item.get("text") or ""),
                    "timestamp": str(item.get("start_time") or ""),
                }
            )

    return segments



__all__ = [
    "append_transcript_segment",
    "delete_transcript_state",
    "expire_transcript_keys",
    "generate_final_summary",
    "get_live_transcript",
    "get_transcript_history_segments",
    "get_transcript_segments",
    "has_user_left",
    "mark_user_left",
    "process_transcript_chunk",
]
