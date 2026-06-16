import logging
from uuid import UUID
import uuid
import json
from datetime import datetime, timezone

import httpx
from redis.asyncio import Redis

from app.core.config import get_groq_chunk_api_key, get_groq_chunk_model, is_rag_enabled
from app.modules.transcripts.redis_keys import (
    ACTIVE_MEETING_TTL_SECONDS,
    CHUNK_LOCK_TTL_SECONDS,
    TRANSCRIPT_SEGMENT_THRESHOLD,
    chunks_initialized_key,
    chunks_key,
    lock_key,
)
from app.modules.transcripts.segment_storage import get_live_transcript, get_transcript_segments
from app.state.redis_client import (
    redis_delete,
    redis_expire,
    redis_get,
    redis_llen,
    redis_lpop,
    redis_lrange,
    redis_rpush,
    redis_lpush,
    redis_set,
)

logger = logging.getLogger(__name__)


async def _mark_chunks_ensure_initialized(redis: Redis, meeting_id: UUID) -> None:
    ikey = chunks_initialized_key(meeting_id)
    await redis_set(redis, ikey, "1", ex=ACTIVE_MEETING_TTL_SECONDS)


async def ensure_summary_chunks_for_meeting_end(redis: Redis, meeting_id: UUID) -> None:
    try:
        flag = await redis_get(redis, chunks_initialized_key(meeting_id))
        if flag:
            return
    except Exception:
        logger.exception("ensure_summary_chunks_init_flag_read_failed meeting_id=%s", meeting_id)
        return

    ckey = chunks_key(meeting_id)
    try:
        n_chunks: int = await redis_llen(redis, ckey)
    except Exception:
        logger.exception("ensure_summary_chunks_llen_failed meeting_id=%s", meeting_id)
        return
    if n_chunks > 0:
        try:
            await _mark_chunks_ensure_initialized(redis, meeting_id)
        except Exception:
            logger.exception(
                "ensure_summary_chunks_init_flag_set_failed meeting_id=%s",
                meeting_id,
            )
        return

    try:
        segments = await get_transcript_segments(redis, meeting_id)
    except Exception:
        logger.exception("ensure_summary_chunks_read_segments_failed meeting_id=%s", meeting_id)
        return
    if not segments:
        return

    batch_size = TRANSCRIPT_SEGMENT_THRESHOLD
    pushed_any = False
    for start in range(0, len(segments), batch_size):
        batch = segments[start : start + batch_size]
        lines: list[str] = []
        for seg in batch:
            if not isinstance(seg, dict):
                continue
            text = (seg.get("text") or "").strip()
            if not text:
                continue
            speaker = seg.get("speaker_name") or seg.get("speaker_id") or "Speaker"
            lines.append(f"{speaker}: {text}")
        if not lines:
            continue
        chunk_text = "\n".join(lines)
        try:
            summary = await _summarize_text(chunk_text, purpose="chunk")
        except Exception:
            logger.exception(
                "ensure_summary_chunks_batch_failed meeting_id=%s offset=%s",
                meeting_id,
                start,
            )
            continue
        if summary:
            await redis_rpush(redis, ckey, summary)
            await redis_expire(redis, ckey, ACTIVE_MEETING_TTL_SECONDS)
            pushed_any = True
            if is_rag_enabled():
                from app.modules.rag.service import generate_chunk_hash
                text_hash = generate_chunk_hash(meeting_id, summary)
                rag_payload = {
                    "job_id": str(uuid.uuid4()),
                    "meeting_id": str(meeting_id),
                    "chunk_type": "summary",
                    "text_hash": text_hash,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "text_content": summary,
                }
                await redis_lpush(redis, "rag:ingestion_queue", json.dumps(rag_payload))

    if pushed_any:
        try:
            await _mark_chunks_ensure_initialized(redis, meeting_id)
        except Exception:
            logger.exception(
                "ensure_summary_chunks_init_flag_set_failed meeting_id=%s",
                meeting_id,
            )


async def process_transcript_chunk(redis: Redis, meeting_id: UUID) -> None:
    lock = lock_key(meeting_id)
    got_lock: bool = await redis_set(redis, lock, "1", nx=True, ex=CHUNK_LOCK_TTL_SECONDS)
    if not got_lock:
        return
    try:
        buf_key = chunks_key(meeting_id)
        segments: list[str] = []
        for _ in range(TRANSCRIPT_SEGMENT_THRESHOLD):
            value = await redis_lpop(redis, buf_key)
            if value is None:
                break
            segments.append(value)
        if not segments:
            return
        chunk_text = "\n".join(segments)
        summary = await _summarize_text(chunk_text, purpose="chunk")
        if summary:
            ckey = chunks_key(meeting_id)
            await redis_rpush(redis, ckey, summary)
            await redis_expire(redis, ckey, ACTIVE_MEETING_TTL_SECONDS)
            if is_rag_enabled():
                from app.modules.rag.service import generate_chunk_hash
                text_hash = generate_chunk_hash(meeting_id, summary)
                rag_payload = {
                    "job_id": str(uuid.uuid4()),
                    "meeting_id": str(meeting_id),
                    "chunk_type": "summary",
                    "text_hash": text_hash,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "text_content": summary,
                }
                await redis_lpush(redis, "rag:ingestion_queue", json.dumps(rag_payload))
    finally:
        await redis_delete(redis, lock)


async def generate_final_summary(redis: Redis, meeting_id: UUID) -> str:
    chunks: list[str] = await redis_lrange(redis, chunks_key(meeting_id))
    if not chunks:
        live_segments: list[str] = await get_live_transcript(redis, meeting_id)
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
