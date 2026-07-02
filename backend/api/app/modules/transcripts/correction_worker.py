import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from redis.asyncio import Redis

from app.core.config import ENABLE_RAG, GEMINI_API_KEY, GEMINI_CORRECTION_MODEL_NAME
from app.core.gemini_client import GeminiClient
from app.core.metrics import incr
from sqlalchemy import select
from app.db.models import Meeting
from app.db.session import async_session_factory
from app.modules.rag.service import generate_chunk_hash, soft_delete_transcript_chunks
from app.modules.transcripts.broadcaster import publish_correction
from app.modules.transcripts.redis_keys import (
    corrected_segments_key,
    correction_queue_key,
)
from app.state.client import get_redis
from app.state.redis_client import redis_brpop, redis_expire, redis_hset, redis_lpush

logger = logging.getLogger(__name__)


def _get_original_text_hash(payload: dict[str, Any], meeting_id: UUID, text: str) -> str:
    original_text_hash = payload.get("original_text_hash")
    if isinstance(original_text_hash, str) and original_text_hash.strip():
        return original_text_hash.strip()
    return generate_chunk_hash(meeting_id, text)


async def _get_redis_client() -> Redis:
    return await get_redis()


GLOSSARY_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "prompts",
        "transcripts",
        "technical_glossary.txt"
    )
)


def _load_technical_glossary() -> list[str]:
    try:
        if os.path.exists(GLOSSARY_PATH):
            with open(GLOSSARY_PATH, "r", encoding="utf-8") as f:
                return [line.strip() for line in f if line.strip()]
    except Exception as exc:
        logger.warning("failed_to_load_technical_glossary: %s", exc)
    return [
        "Speech Gateway", "SFU", "RAG", "WebRTC", "FastAPI", "ElevenLabs",
        "GetStream", "Prometheus", "PostgreSQL", "Redis", "MeetNote",
        "Gemini", "Whisper", "Vite", "Next.js", "TailwindCSS", "TypeScript", "WebSocket"
    ]


async def correct_segment(text: str) -> str:
    api_key = GEMINI_API_KEY
    if not api_key:
        logger.warning("gemini_key_missing_for_correction")
        return text

    terms = _load_technical_glossary()
    glossary_str = ", ".join(terms)

    prompt = (
        "Correct any obvious spelling, grammar, and punctuation mistakes in the transcript segment. "
        "Keep the speaker's original intent, tone, style, and meaning exactly as is. "
        "Preserve all technical terminology, abbreviations, project names, product names, dates, deadlines, versions, and abbreviations. "
        "Do not over-correct or rewrite the sentence to sound overly formal. "
        "If you see phonetic mishearings or approximations of technical vocabulary, "
        "map them to their correct technical spellings.\n"
        f"Technical Glossary: {glossary_str}\n\n"
        "Output ONLY the corrected text. Do not include introductory text, explanations, or quotes.\n\n"
        f"Text:\n{text}"
    )

    try:
        client = GeminiClient(api_key, GEMINI_CORRECTION_MODEL_NAME)
        corrected_text = await client.generate_content(
            prompt=prompt,
            max_tokens=1000,
            temperature=0.1,
            timeout=10.0,
        )
        return corrected_text.strip() or text
    except Exception as exc:
        logger.warning("transcript_correction_failed", exc_info=exc)
        return text


async def run_correction_worker(shutdown_event: asyncio.Event | None = None) -> None:
    while True:
        if shutdown_event and shutdown_event.is_set():
            return
        try:
            redis = await _get_redis_client()
            break
        except Exception:
            logger.exception("correction_worker_redis_connect_failed")
            try:
                for _ in range(50):
                    if shutdown_event and shutdown_event.is_set():
                        return
                    await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                raise

    queue_key = correction_queue_key()

    while True:
        if shutdown_event and shutdown_event.is_set():
            break
        try:
            raw = await redis_brpop(redis, queue_key, timeout=5)
            if raw is None:
                await asyncio.sleep(0.01)
                continue
            try:
                payload: dict[str, Any] = json.loads(raw)
            except Exception:
                logger.warning("correction_worker_invalid_payload")
                continue

            meeting_id_raw = payload.get("meeting_id")
            segment_id = payload.get("segment_id")
            text = payload.get("text") or ""
            sequence = payload.get("sequence")
            speaker_name = payload.get("speaker_name")

            if not text.strip() or not segment_id or not meeting_id_raw:
                continue

            try:
                meeting_id = UUID(str(meeting_id_raw))
            except Exception:
                continue

            # Verify meeting still exists before processing correction
            try:
                async with async_session_factory() as session:
                    meeting_exists = await session.scalar(
                        select(1).select_from(Meeting).where(Meeting.id == meeting_id).limit(1)
                    )
                if not meeting_exists:
                    logger.info("Meeting %s does not exist. Discarding correction job.", meeting_id)
                    continue
            except Exception as db_exc:
                logger.warning("Database check failed during correction: %s", db_exc)
                continue

            corrected_text = await correct_segment(text)

            if corrected_text and corrected_text != text:
                corrected_key = corrected_segments_key(meeting_id)
                await redis_hset(redis, corrected_key, str(segment_id), corrected_text)
                await redis_expire(redis, corrected_key, 3600)

                correction_event = {
                    "type": "transcript_correction",
                    "segment_id": segment_id,
                    "corrected_text": corrected_text,
                    "sequence": sequence,
                }
                await publish_correction(redis, meeting_id, correction_event)
                incr("transcript_segments_corrected_total")

                try:
                    old_hash = _get_original_text_hash(payload, meeting_id, text)
                    async with async_session_factory() as session:
                        async with session.begin():
                            await soft_delete_transcript_chunks(session, meeting_id, [old_hash])
                            from sqlalchemy import update
                            from app.db.models import MeetingTranscript
                            stmt = (
                                update(MeetingTranscript)
                                .where(
                                    MeetingTranscript.meeting_id == meeting_id,
                                    MeetingTranscript.sequence == sequence
                                )
                                .values(text_content=corrected_text)
                            )
                            await session.execute(stmt)
                except Exception as exc:
                    logger.warning("Failed to update database and soft-delete old transcript chunk on correction: %s", exc)

                if ENABLE_RAG:
                    try:
                        new_hash = generate_chunk_hash(meeting_id, corrected_text)
                        rag_payload = {
                            "job_id": str(uuid.uuid4()),
                            "meeting_id": str(meeting_id),
                            "chunk_type": "transcript",
                            "text_hash": new_hash,
                            "created_at": datetime.now(timezone.utc).isoformat(),
                            "text_content": corrected_text,
                            "speaker_name": speaker_name,
                            "sequence": sequence,
                        }
                        await redis_lpush(redis, "rag:ingestion_queue", json.dumps(rag_payload))
                    except Exception as exc:
                        logger.warning("Failed to enqueue corrected transcript chunk to RAG queue: %s", exc)

        except asyncio.CancelledError:
            break
        except Exception:
            logger.exception("correction_worker_loop_error")
            try:
                for _ in range(10):
                    if shutdown_event and shutdown_event.is_set():
                        break
                    await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                raise
