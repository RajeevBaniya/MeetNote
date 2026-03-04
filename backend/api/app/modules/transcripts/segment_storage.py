import hashlib
import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from redis.asyncio import Redis

from app.core.metrics import incr
from app.modules.transcripts.broadcaster import publish_segment
from app.modules.transcripts.redis_keys import (
    ACTIVE_MEETING_TTL_SECONDS,
    POST_MEETING_TTL_SECONDS,
    buffer_key,
    left_users_key,
    lock_key,
    live_key,
    seen_key,
    segments_key,
    seq_key,
    chunks_key,
)


async def append_transcript_segment(
    redis: Redis,
    meeting_id: UUID,
    text: str,
    speaker_id: str | None = None,
    speaker_name: str | None = None,
    timestamp: str | None = None,
) -> None:
    if not text or not text.strip():
        return
    payload = text.strip()
    ts = timestamp or datetime.now(timezone.utc).isoformat()

    bucket = ts[:19]
    hasher = hashlib.sha256()
    hasher.update((speaker_id or "").encode("utf-8"))
    hasher.update(b"|")
    hasher.update((speaker_name or "").encode("utf-8"))
    hasher.update(b"|")
    hasher.update(payload.encode("utf-8"))
    hasher.update(b"|")
    hasher.update(bucket.encode("utf-8"))
    digest = hasher.hexdigest()

    sk = seen_key(meeting_id)
    if await redis.sismember(sk, digest):
        return
    await redis.sadd(sk, digest)
    await redis.expire(sk, ACTIVE_MEETING_TTL_SECONDS)

    segment_record: dict[str, Any] = {
        "segment_id": digest,
        "speaker_id": speaker_id,
        "speaker_name": speaker_name,
        "text": payload,
        "start_time": ts,
        "end_time": ts,
    }
    sequence = await redis.incr(seq_key(meeting_id))
    segment_record["sequence"] = int(sequence)
    seg_key = segments_key(meeting_id)
    await redis.rpush(seg_key, json.dumps(segment_record))
    await redis.ltrim(seg_key, -2000, -1)

    segment_for_stream = {
        "text": payload,
        "speaker_id": speaker_id,
        "speaker": speaker_name,
        "timestamp": ts,
        "sequence": int(sequence),
    }
    await publish_segment(redis, meeting_id, segment_for_stream)
    incr("transcript_segments_received_total")


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
