import asyncio
from uuid import UUID

from redis.asyncio import Redis

from app.modules.transcripts.redis_keys import TRANSCRIPT_SEGMENT_THRESHOLD
from app.modules.transcripts.segment_storage import (
    append_transcript_segment as _append_segment,
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


async def append_transcript_segment(
    redis: Redis,
    meeting_id: UUID,
    text: str,
    speaker_id: str | None = None,
    speaker_name: str | None = None,
    timestamp: str | None = None,
) -> None:
    await _append_segment(
        redis, meeting_id, text,
        speaker_id=speaker_id,
        speaker_name=speaker_name,
        timestamp=timestamp,
    )
    length = await get_segment_count(redis, meeting_id)
    if length >= TRANSCRIPT_SEGMENT_THRESHOLD:
        asyncio.create_task(process_transcript_chunk(redis, meeting_id))


__all__ = [
    "append_transcript_segment",
    "delete_transcript_state",
    "expire_transcript_keys",
    "generate_final_summary",
    "get_live_transcript",
    "get_transcript_segments",
    "has_user_left",
    "mark_user_left",
    "process_transcript_chunk",
]
