from typing import List

import httpx
from redis.asyncio import Redis
from uuid import UUID

from app.core.config import get_groq_chunk_api_key, get_groq_chunk_model
from app.modules.transcripts.redis_keys import (
    ACTIVE_MEETING_TTL_SECONDS,
    CHUNK_LOCK_TTL_SECONDS,
    TRANSCRIPT_SEGMENT_THRESHOLD,
    buffer_key,
    chunks_key,
    lock_key,
)
from app.modules.transcripts.segment_storage import get_live_transcript


async def process_transcript_chunk(redis: Redis, meeting_id: UUID) -> None:
    lock = lock_key(meeting_id)
    got_lock = await redis.set(lock, "1", nx=True, ex=CHUNK_LOCK_TTL_SECONDS)
    if not got_lock:
        return
    try:
        buf_key = buffer_key(meeting_id)
        segments: List[str] = []
        for _ in range(TRANSCRIPT_SEGMENT_THRESHOLD):
            value = await redis.lpop(buf_key)
            if value is None:
                break
            segments.append(value)
        if not segments:
            return
        chunk_text = "\n".join(segments)
        summary = await _summarize_text(chunk_text, purpose="chunk")
        if summary:
            ckey = chunks_key(meeting_id)
            await redis.rpush(ckey, summary)
            await redis.expire(ckey, ACTIVE_MEETING_TTL_SECONDS)
    finally:
        await redis.delete(lock)


async def generate_final_summary(redis: Redis, meeting_id: UUID) -> str:
    chunks = await redis.lrange(chunks_key(meeting_id), 0, -1)
    if not chunks:
        live_segments = await get_live_transcript(redis, meeting_id)
        if not live_segments:
            return ""
        text = "\n".join(live_segments)
        return await _summarize_text(text, purpose="final")
    combined = "\n\n".join(chunks)
    return await _summarize_text(combined, purpose="final")


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
        "messages": [{"role": "user", "content": prompt}],
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
