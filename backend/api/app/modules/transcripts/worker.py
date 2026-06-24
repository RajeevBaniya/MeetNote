import asyncio
import hashlib
import json
import logging
from typing import Any
from uuid import UUID

from redis.asyncio import Redis
from sqlalchemy import text as sa_text

from app.core.metrics import incr
from app.db.session import async_session_factory
from app.modules.analytics.service import add_speaking_time
from app.modules.transcripts.service import append_transcript_segment
from app.state.client import get_redis
from app.state.redis_client import redis_brpop, redis_set

logger = logging.getLogger(__name__)

EVENT_QUEUE_KEY = "transcript_events"


async def _get_redis_client() -> Redis:
    return await get_redis()


async def run_transcript_worker(shutdown_event: asyncio.Event | None = None) -> None:
    while True:
        if shutdown_event and shutdown_event.is_set():
            return
        try:
            redis = await _get_redis_client()
            break
        except Exception:
            logger.exception("transcript_worker_redis_connect_failed")
            try:
                for _ in range(50):
                    if shutdown_event and shutdown_event.is_set():
                        return
                    await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                raise

    while True:
        if shutdown_event and shutdown_event.is_set():
            break
        try:
            raw = await redis_brpop(redis, EVENT_QUEUE_KEY, timeout=5)
            if raw is None:
                await asyncio.sleep(0.01)
                continue
            try:
                payload: dict[str, Any] = json.loads(raw)
            except Exception:
                logger.warning("transcript_worker_invalid_payload")
                continue

            meeting_id_raw = payload.get("meeting_id")
            segment_text = payload.get("text") or ""
            speaker_id = payload.get("speaker_id")
            speaker_name = payload.get("speaker_name")
            timestamp = payload.get("timestamp")
            confidence_raw = payload.get("confidence")
            confidence: float | None = None
            if confidence_raw is not None:
                try:
                    confidence = float(confidence_raw)
                except (TypeError, ValueError):
                    confidence = None

            try:
                meeting_id = UUID(str(meeting_id_raw))
            except Exception:
                logger.warning("transcript_worker_invalid_meeting_id payload=%s", payload)
                continue

            if not segment_text.strip():
                continue

            await append_transcript_segment(
                redis,
                meeting_id,
                segment_text,
                speaker_id=speaker_id,
                speaker_name=speaker_name,
                timestamp=timestamp,
                confidence=confidence,
            )
            incr("transcript_chunks_processed_total")
            if speaker_id and segment_text.strip():
                segment_hash = hashlib.sha256(
                    f"{meeting_id}|{speaker_id}|{segment_text}|{timestamp or ''}".encode()
                ).hexdigest()
                inserted = False
                async with async_session_factory() as session:
                    async with session.begin():
                        result = await session.execute(
                            sa_text(
                                "INSERT INTO processed_segments(segment_id) "
                                "VALUES (:segment_id) "
                                "ON CONFLICT (segment_id) DO NOTHING"
                            ),
                            {"segment_id": segment_hash},
                        )
                        inserted = bool(getattr(result, "rowcount", 0))
                if not inserted:
                    continue
                key = f"analytics_segment_seen:{meeting_id}:{segment_hash}"
                if await redis_set(redis, key, "1", nx=True, ex=7200):
                    try:
                        user_id = UUID(str(speaker_id))
                        word_count = len(segment_text.strip().split())
                        await add_speaking_time(meeting_id, user_id, word_count)
                    except (ValueError, TypeError):
                        pass
        except asyncio.CancelledError:
            break
        except Exception:
            logger.exception("transcript_worker_loop_error")
            try:
                for _ in range(10):
                    if shutdown_event and shutdown_event.is_set():
                        break
                    await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                raise
