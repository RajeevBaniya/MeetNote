import hashlib
import json
import logging
import string
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Any
from uuid import UUID

from redis.asyncio import Redis

from app.core.metrics import incr
from app.modules.transcripts.broadcaster import publish_segment
from app.modules.transcripts.redis_keys import (
    ACTIVE_MEETING_TTL_SECONDS,
    buffer_key,
    speakers_key,
    segments_key,
    seen_key,
    seq_key,
)


logger = logging.getLogger(__name__)

_MAX_BUFFER_SEGMENTS = 10
_COMMIT_WINDOW_SECONDS = 2


def _normalize_text(text: str) -> str:
    table = str.maketrans("", "", string.punctuation)
    cleaned = text.translate(table).lower().strip()
    return " ".join(cleaned.split())


def _is_similar(a: str, b: str) -> bool:
    if not a or not b:
        return False
    return SequenceMatcher(None, a, b).ratio() >= 0.9


async def _commit_segment(
    redis: Redis,
    meeting_id: UUID,
    segment: dict[str, Any],
) -> None:
    text = (segment.get("text") or "").strip()
    if not text:
        return

    confidence_value = segment.get("confidence")
    if confidence_value is not None:
        try:
            confidence = float(confidence_value)
        except (TypeError, ValueError):
            confidence = None
        if confidence is not None and confidence < 0.6:
            incr("transcript_segments_dropped_low_confidence_total")
            logger.debug(
                "transcript_segment_low_confidence",
                extra={"meeting_id": str(meeting_id), "confidence": confidence},
            )
            return

    last_raw = await redis.lindex(segments_key(meeting_id), -1)
    if last_raw:
        try:
            last_data = json.loads(last_raw)
        except (TypeError, json.JSONDecodeError):
            last_data = {}
        last_text = (last_data.get("text") or "").strip()
        if _is_similar(_normalize_text(text), _normalize_text(last_text)):
            incr("transcript_segments_deduplicated_total")
            return

    speaker_id_value = segment.get("speaker_id")
    speaker_name_value = segment.get("speaker_name")
    speaker_id_str = str(speaker_id_value) if speaker_id_value is not None else None
    speakers_hkey = speakers_key(meeting_id)
    final_speaker_name = speaker_name_value

    if speaker_id_str:
        stored_name = await redis.hget(speakers_hkey, speaker_id_str)
        if stored_name:
            if isinstance(stored_name, (bytes, bytearray)):
                final_speaker_name = stored_name.decode("utf-8", errors="replace")
            else:
                final_speaker_name = str(stored_name)
        elif (
            isinstance(speaker_name_value, str) and speaker_name_value.strip()
        ):
            await redis.hset(speakers_hkey, speaker_id_str, speaker_name_value.strip())

    segment_id = segment.get("segment_id")
    if not segment_id:
        hasher = hashlib.sha256()
        hasher.update((speaker_id_str or "").encode("utf-8"))
        hasher.update(b"|")
        hasher.update((final_speaker_name or "").encode("utf-8"))
        hasher.update(b"|")
        hasher.update(text.encode("utf-8"))
        hasher.update(b"|")
        hasher.update((segment.get("timestamp") or "").encode("utf-8"))
        segment_id = hasher.hexdigest()

    sk = seen_key(meeting_id)
    if await redis.sismember(sk, segment_id):
        return
    await redis.sadd(sk, segment_id)
    await redis.expire(sk, ACTIVE_MEETING_TTL_SECONDS)

    # Soft commit-stage rate limit: max 5 committed segments/second/meeting.
    # This applies after stabilization/dedup/idempotency checks.
    ts_for_rate = datetime.now(timezone.utc)
    rate_key = f"transcript:rate:{meeting_id}:{int(ts_for_rate.timestamp())}"
    rate_count = await redis.incr(rate_key)
    if rate_count == 1:
        await redis.expire(rate_key, 2)
    if rate_count > 5:
        incr("transcript_segments_rate_limited_total")
        return

    ts_raw = segment.get("timestamp")
    if ts_raw is not None:
        try:
            ts_dt = datetime.fromisoformat(str(ts_raw))
        except (TypeError, ValueError):
            ts_dt = datetime.now(timezone.utc)
    else:
        ts_dt = datetime.now(timezone.utc)
    ts = ts_dt.isoformat()

    record: dict[str, Any] = {
        "segment_id": segment_id,
        "speaker_id": speaker_id_str,
        "speaker_name": final_speaker_name,
        "text": text,
        "start_time": ts,
        "end_time": ts,
    }
    sequence = await redis.incr(seq_key(meeting_id))
    record["sequence"] = int(sequence)

    seg_key = segments_key(meeting_id)
    await redis.rpush(seg_key, json.dumps(record))
    await redis.ltrim(seg_key, -2000, -1)

    stream_payload = {
        "text": text,
        "speaker_id": speaker_id_str,
        "speaker": final_speaker_name,
        "timestamp": ts,
        "sequence": int(sequence),
    }
    await publish_segment(redis, meeting_id, stream_payload)
    incr("transcript_segments_committed_total")


async def append_and_stabilize_segment(
    redis: Redis,
    meeting_id: UUID,
    text: str,
    speaker_id: str | None,
    speaker_name: str | None,
    timestamp: str | None,
    confidence: float | None,
) -> None:
    payload = (text or "").strip()
    if not payload:
        return

    ts = timestamp or datetime.now(timezone.utc).isoformat()
    entry: dict[str, Any] = {
        "text": payload,
        "speaker_id": speaker_id,
        "speaker_name": speaker_name,
        "timestamp": ts,
    }
    if confidence is not None:
        entry["confidence"] = confidence

    buf_key = buffer_key(meeting_id)
    await redis.rpush(buf_key, json.dumps(entry))
    await redis.ltrim(buf_key, -_MAX_BUFFER_SEGMENTS, -1)
    incr("transcript_segments_buffered_total")

    now = datetime.now(timezone.utc)
    raw_items = await redis.lrange(buf_key, 0, -1)
    buffer: list[dict[str, Any]] = []
    to_commit: list[dict[str, Any]] = []

    for raw in raw_items:
        try:
            item = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            continue
        ts_value = item.get("timestamp")
        try:
            ts_dt = datetime.fromisoformat(str(ts_value))
        except (TypeError, ValueError):
            ts_dt = now
        age_seconds = (now - ts_dt).total_seconds()
        if age_seconds >= _COMMIT_WINDOW_SECONDS:
            to_commit.append(item)
        else:
            buffer.append(item)

    if buffer and len(raw_items) > _MAX_BUFFER_SEGMENTS:
        oldest = buffer[0]
        oldest_raw_ts = oldest.get("timestamp")
        try:
            oldest_dt = datetime.fromisoformat(str(oldest_raw_ts))
        except (TypeError, ValueError):
            oldest_dt = now
        if (now - oldest_dt).total_seconds() > 5:
            to_commit.insert(0, oldest)
            buffer = buffer[1:]

    for segment in to_commit:
        await _commit_segment(redis, meeting_id, segment)

    await redis.delete(buf_key)
    for item in buffer[-_MAX_BUFFER_SEGMENTS:]:
        await redis.rpush(buf_key, json.dumps(item))
