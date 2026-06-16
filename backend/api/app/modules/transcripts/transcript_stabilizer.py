import hashlib
import json
import logging
import string
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Any
from uuid import UUID
import uuid

from redis.asyncio import Redis

from app.core.config import is_rag_enabled
from app.core.metrics import incr
from app.modules.transcripts.broadcaster import publish_segment
from app.modules.transcripts.redis_keys import (
    ACTIVE_MEETING_TTL_SECONDS,
    buffer_key,
    correction_queue_key,
    speakers_key,
    segments_key,
    seen_key,
    seq_key,
)
from app.state.redis_client import (
    redis_delete,
    redis_expire,
    redis_hget,
    redis_hset,
    redis_incr,
    redis_lindex,
    redis_lrange,
    redis_ltrim,
    redis_rpush,
    redis_lpush,
    redis_sadd,
    redis_sismember,
)


logger = logging.getLogger(__name__)

_MAX_BUFFER_SEGMENTS = 10
_COMMIT_WINDOW_SECONDS = 0.5


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

    last_raw = await redis_lindex(redis, segments_key(meeting_id), -1)
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
        stored_name = await redis_hget(redis, speakers_hkey, speaker_id_str)
        if stored_name:
            final_speaker_name = stored_name
        elif isinstance(speaker_name_value, str) and speaker_name_value.strip():
            await redis_hset(redis, speakers_hkey, speaker_id_str, speaker_name_value.strip())

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
    if await redis_sismember(redis, sk, segment_id):
        return
    await redis_sadd(redis, sk, segment_id)
    await redis_expire(redis, sk, ACTIVE_MEETING_TTL_SECONDS)

    ts_for_rate = datetime.now(timezone.utc)
    rate_key = f"transcript:rate:{meeting_id}:{int(ts_for_rate.timestamp())}"
    rate_count = await redis_incr(redis, rate_key)
    if rate_count == 1:
        await redis_expire(redis, rate_key, 2)
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
    sequence = await redis_incr(redis, seq_key(meeting_id))
    record["sequence"] = sequence

    seg_key = segments_key(meeting_id)
    await redis_rpush(redis, seg_key, json.dumps(record))
    await redis_ltrim(redis, seg_key, -2000, -1)

    stream_payload = {
        "text": text,
        "speaker_id": speaker_id_str,
        "speaker": final_speaker_name,
        "timestamp": ts,
        "sequence": sequence,
    }
    await publish_segment(redis, meeting_id, stream_payload)
    incr("transcript_segments_committed_total")

    latency_ms = int((datetime.now(timezone.utc) - ts_dt).total_seconds() * 1000)
    logger.info(
        "transcript_segment_committed",
        extra={
            "meeting_id": str(meeting_id),
            "segment_id": segment_id,
            "latency_ms": latency_ms,
        },
    )

    original_text_hash = None
    if is_rag_enabled():
        from app.modules.rag.service import generate_chunk_hash
        original_text_hash = generate_chunk_hash(meeting_id, text)

    correction_payload = {
        "meeting_id": str(meeting_id),
        "segment_id": segment_id,
        "text": text,
        "sequence": sequence,
        "speaker_name": final_speaker_name,
    }
    if original_text_hash:
        correction_payload["original_text_hash"] = original_text_hash
    await redis_rpush(redis, correction_queue_key(), json.dumps(correction_payload))

    if original_text_hash:
        rag_payload = {
            "job_id": str(uuid.uuid4()),
            "meeting_id": str(meeting_id),
            "chunk_type": "transcript",
            "text_hash": original_text_hash,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "text_content": text,
            "speaker_name": final_speaker_name,
        }
        await redis_lpush(redis, "rag:ingestion_queue", json.dumps(rag_payload))



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
    await redis_rpush(redis, buf_key, json.dumps(entry))
    await redis_ltrim(redis, buf_key, -_MAX_BUFFER_SEGMENTS, -1)
    incr("transcript_segments_buffered_total")

    now = datetime.now(timezone.utc)
    raw_items = await redis_lrange(redis, buf_key)
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

    await redis_delete(redis, buf_key)
    for item in buffer[-_MAX_BUFFER_SEGMENTS:]:
        await redis_rpush(redis, buf_key, json.dumps(item))
