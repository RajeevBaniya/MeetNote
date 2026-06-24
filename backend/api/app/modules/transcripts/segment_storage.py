import json
from typing import Any
from uuid import UUID

from redis.asyncio import Redis

from app.core.config import ENDED_MEETING_CACHE_TTL
from app.modules.transcripts.redis_keys import (
    buffer_key,
    chunks_initialized_key,
    chunks_key,
    corrected_segments_key,
    left_users_key,
    live_key,
    lock_key,
    seen_key,
    segments_key,
    seq_key,
    speakers_key,
)
from app.modules.transcripts.transcript_stabilizer import append_and_stabilize_segment
from app.state.redis_client import (
    redis_delete,
    redis_expire,
    redis_hmget,
    redis_llen,
    redis_lrange,
    redis_sadd,
    redis_sismember,
)


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
    return await redis_llen(redis, segments_key(meeting_id))


async def get_live_transcript(redis: Redis, meeting_id: UUID) -> list[str]:
    return await redis_lrange(redis, live_key(meeting_id))


async def get_transcript_segments(
    redis: Redis,
    meeting_id: UUID,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    if limit is None:
        raw_items = await redis_lrange(redis, segments_key(meeting_id))
    else:
        normalized_limit = int(limit)
        if normalized_limit <= 0:
            return []
        raw_items = await redis_lrange(
            redis,
            segments_key(meeting_id),
            -normalized_limit,
            -1,
        )

    segments: list[dict[str, Any]] = []
    for raw in raw_items:
        try:
            data = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            continue
        if isinstance(data, dict):
            segments.append(data)

    if segments:
        corrected_key = corrected_segments_key(meeting_id)
        segment_ids: list[str] = [
            str(s["segment_id"])
            for s in segments
            if s.get("segment_id") is not None
        ]
        if segment_ids:
            try:
                corrections = await redis_hmget(redis, corrected_key, segment_ids)
                ids_iter = (s for s in segments if s.get("segment_id") is not None)
                for segment, correction in zip(ids_iter, corrections):
                    if correction is not None:
                        segment["corrected_text"] = correction
            except Exception:
                pass

    return segments


async def mark_user_left(redis: Redis, meeting_id: UUID, user_id: UUID) -> None:
    await redis_sadd(redis, left_users_key(meeting_id), str(user_id))


async def has_user_left(redis: Redis, meeting_id: UUID, user_id: UUID) -> bool:
    return await redis_sismember(redis, left_users_key(meeting_id), str(user_id))


async def expire_transcript_keys(redis: Redis, meeting_id: UUID) -> None:
    keys_for_ttl = [
        live_key(meeting_id),
        buffer_key(meeting_id),
        chunks_key(meeting_id),
        chunks_initialized_key(meeting_id),
        lock_key(meeting_id),
        segments_key(meeting_id),
        speakers_key(meeting_id),
        seq_key(meeting_id),
        seen_key(meeting_id),
        corrected_segments_key(meeting_id),
    ]
    for key in keys_for_ttl:
        await redis_expire(redis, key, ENDED_MEETING_CACHE_TTL)
    await redis_delete(redis, left_users_key(meeting_id))


async def delete_transcript_state(redis: Redis, meeting_id: UUID) -> None:
    await redis_delete(
        redis,
        segments_key(meeting_id),
        speakers_key(meeting_id),
        left_users_key(meeting_id),
        live_key(meeting_id),
        buffer_key(meeting_id),
        chunks_key(meeting_id),
        chunks_initialized_key(meeting_id),
        lock_key(meeting_id),
        seen_key(meeting_id),
        seq_key(meeting_id),
        corrected_segments_key(meeting_id),
    )
