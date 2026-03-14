import json
from typing import Any
from uuid import UUID

from redis.asyncio import Redis

from app.modules.transcripts.redis_keys import (
    POST_MEETING_TTL_SECONDS,
    buffer_key,
    chunks_key,
    left_users_key,
    live_key,
    lock_key,
    segments_key,
    seq_key,
    seen_key,
)
from app.modules.transcripts.transcript_stabilizer import append_and_stabilize_segment


async def append_transcript_segment(
    redis: Redis,
    meeting_id: UUID,
    text: str,
    speaker_id: str | None = None,
    speaker_name: str | None = None,
    timestamp: str | None = None,
    confidence: float | None = None,
) -> None:
    await append_and_stabilize_segment(
        redis=redis,
        meeting_id=meeting_id,
        text=text,
        speaker_id=speaker_id,
        speaker_name=speaker_name,
        timestamp=timestamp,
        confidence=confidence,
    )


async def get_segment_count(redis: Redis, meeting_id: UUID) -> int:
    length = await redis.llen(segments_key(meeting_id))
    return int(length)


async def get_live_transcript(redis: Redis, meeting_id: UUID) -> list[str]:
    items = await redis.lrange(live_key(meeting_id), 0, -1)
    return list(items) if items else []


async def get_transcript_segments(
    redis: Redis,
    meeting_id: UUID,
) -> list[dict[str, Any]]:
    raw_items = await redis.lrange(segments_key(meeting_id), 0, -1)
    segments: list[dict[str, Any]] = []
    for raw in raw_items or []:
        try:
            data = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            continue
        if isinstance(data, dict):
            segments.append(data)
    return segments


async def mark_user_left(redis: Redis, meeting_id: UUID, user_id: UUID) -> None:
    await redis.sadd(left_users_key(meeting_id), str(user_id))


async def has_user_left(redis: Redis, meeting_id: UUID, user_id: UUID) -> bool:
    return bool(await redis.sismember(left_users_key(meeting_id), str(user_id)))


async def expire_transcript_keys(redis: Redis, meeting_id: UUID) -> None:
    keys_for_ttl = [
        live_key(meeting_id),
        buffer_key(meeting_id),
        chunks_key(meeting_id),
        lock_key(meeting_id),
        segments_key(meeting_id),
        seq_key(meeting_id),
        seen_key(meeting_id),
    ]
    for key in keys_for_ttl:
        await redis.expire(key, POST_MEETING_TTL_SECONDS)
    await redis.delete(left_users_key(meeting_id))


async def delete_transcript_state(redis: Redis, meeting_id: UUID) -> None:
    await redis.delete(
        segments_key(meeting_id),
        left_users_key(meeting_id),
        live_key(meeting_id),
        buffer_key(meeting_id),
        chunks_key(meeting_id),
        lock_key(meeting_id),
        seen_key(meeting_id),
        seq_key(meeting_id),
    )
