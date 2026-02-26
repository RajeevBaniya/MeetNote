import asyncio
import hashlib
from datetime import datetime, timezone
from typing import List
from uuid import UUID

import httpx
from redis.asyncio import Redis

from app.core.config import get_groq_chunk_api_key, get_groq_chunk_model
from app.modules.transcripts.broadcaster import publish_segment


TRANSCRIPT_SEGMENT_THRESHOLD = 500
CHUNK_LOCK_TTL_SECONDS = 60
ACTIVE_MEETING_TTL_SECONDS = 3600
POST_MEETING_TTL_SECONDS = 600


def _live_key(meeting_id: UUID) -> str:
    return f"transcript_live:{meeting_id}"


def _buffer_key(meeting_id: UUID) -> str:
    return f"transcript_buffer:{meeting_id}"


def _chunks_key(meeting_id: UUID) -> str:
    return f"summary_chunks:{meeting_id}"


def _lock_key(meeting_id: UUID) -> str:
    return f"chunk_lock:{meeting_id}"


def _seen_key(meeting_id: UUID) -> str:
    return f"transcript_seen:{meeting_id}"


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

    # De-duplication guard: avoid processing the same segment multiple times
    # (eg. webhook retries) while still allowing repeated speech over time.
    bucket = ts[:19]  # second-level bucket YYYY-MM-DDTHH:MM:SS
    hasher = hashlib.sha256()
    hasher.update((speaker_id or "").encode("utf-8"))
    hasher.update(b"|")
    hasher.update((speaker_name or "").encode("utf-8"))
    hasher.update(b"|")
    hasher.update(payload.encode("utf-8"))
    hasher.update(b"|")
    hasher.update(bucket.encode("utf-8"))
    digest = hasher.hexdigest()

    seen_key = _seen_key(meeting_id)
    already_seen = await redis.sismember(seen_key, digest)
    if already_seen:
        return
    await redis.sadd(seen_key, digest)
    await redis.expire(seen_key, ACTIVE_MEETING_TTL_SECONDS)

    live_key = _live_key(meeting_id)
    buffer_key = _buffer_key(meeting_id)
    await redis.rpush(live_key, payload)
    await redis.rpush(buffer_key, payload)
    await redis.expire(live_key, ACTIVE_MEETING_TTL_SECONDS)
    await redis.expire(buffer_key, ACTIVE_MEETING_TTL_SECONDS)
    segment = {
        "text": payload,
        "speaker_id": speaker_id,
        "speaker": speaker_name,
        "timestamp": ts,
    }
    await publish_segment(redis, meeting_id, segment)
    length = await redis.llen(buffer_key)
    if length >= TRANSCRIPT_SEGMENT_THRESHOLD:
        asyncio.create_task(process_transcript_chunk(redis, meeting_id))


async def process_transcript_chunk(redis: Redis, meeting_id: UUID) -> None:
    lock = _lock_key(meeting_id)
    got_lock = await redis.set(lock, "1", nx=True, ex=CHUNK_LOCK_TTL_SECONDS)
    if not got_lock:
        return
    try:
        buffer_key = _buffer_key(meeting_id)
        segments: List[str] = []
        for _ in range(TRANSCRIPT_SEGMENT_THRESHOLD):
            value = await redis.lpop(buffer_key)
            if value is None:
                break
            segments.append(value)
        if not segments:
            return
        chunk_text = "\n".join(segments)
        summary = await _summarize_text(chunk_text, purpose="chunk")
        if summary:
            chunks_key = _chunks_key(meeting_id)
            await redis.rpush(chunks_key, summary)
            await redis.expire(chunks_key, ACTIVE_MEETING_TTL_SECONDS)
    finally:
        await redis.delete(lock)


async def get_live_transcript(redis: Redis, meeting_id: UUID) -> List[str]:
    items = await redis.lrange(_live_key(meeting_id), 0, -1)
    return items or []


async def generate_final_summary(redis: Redis, meeting_id: UUID) -> str:
    chunks = await redis.lrange(_chunks_key(meeting_id), 0, -1)
    if not chunks:
        live_segments = await get_live_transcript(redis, meeting_id)
        if not live_segments:
            return ""
        text = "\n".join(live_segments)
        return await _summarize_text(text, purpose="final")
    combined = "\n\n".join(chunks)
    return await _summarize_text(combined, purpose="final")


async def expire_transcript_keys(redis: Redis, meeting_id: UUID) -> None:
    keys = [
        _live_key(meeting_id),
        _buffer_key(meeting_id),
        _chunks_key(meeting_id),
        _lock_key(meeting_id),
    ]
    for key in keys:
        await redis.expire(key, POST_MEETING_TTL_SECONDS)


async def _summarize_text(text: str, purpose: str) -> str:
    api_key = get_groq_chunk_api_key()
    model = get_groq_chunk_model()
    url = "https://api.groq.com/openai/v1/chat/completions"

    if purpose == "chunk":
        prompt = (
            "Summarize the following part of a meeting transcript. "
            "Focus on key points, decisions, and action items.\n\n"
            f"{text}"
        )
    else:
        prompt = (
            "Create a final meeting summary from the following chunks. "
            "Produce a clear, structured summary with sections for Overview, "
            "Decisions, and Action Items.\n\n"
            f"{text}"
        )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
    choices = data.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    content = message.get("content") or ""
    return str(content).strip()

