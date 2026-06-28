import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict

from redis.asyncio import Redis
from sqlalchemy import update

from app.core.config import ENABLE_RAG, GEMINI_EMBEDDING_MODEL_NAME, GEMINI_API_KEY
from app.core.gemini_client import GeminiClient
from app.db.models import RagFailedJob
from app.db.session import async_session_factory
from app.modules.rag.service import (
    process_rag_ingestion_job,
    record_failed_job,
    mark_failed_job_completed,
)
from app.state.client import get_redis
from app.state.redis_client import redis_brpop, redis_lpush

logger = logging.getLogger(__name__)

INGESTION_QUEUE = "rag:ingestion_queue"
RETRY_QUEUE = "rag:retry_queue"
DEAD_LETTER_QUEUE = "rag:dead_letter_queue"


async def restore_pending_retries(redis: Redis) -> None:
    """Restores pending failed jobs from the database back to Redis retry queue on startup."""
    try:
        async with async_session_factory() as session:
            async with session.begin():
                stmt = (
                    update(RagFailedJob)
                    .where(
                        RagFailedJob.status == "failed",
                        RagFailedJob.attempts < RagFailedJob.max_attempts
                    )
                    .values(status="queued")
                    .returning(RagFailedJob)
                )
                res = await session.execute(stmt)
                jobs = res.scalars().all()

                for job in jobs:
                    payload = dict(job.payload)
                    payload["attempts"] = job.attempts
                    payload["job_id"] = str(job.id)
                    payload["meeting_id"] = str(job.meeting_id)
                    payload["chunk_type"] = job.chunk_type
                    
                    now = datetime.now(timezone.utc)
                    payload["scheduled_at"] = (now + timedelta(seconds=10)).isoformat()
                    
                    await redis_lpush(redis, RETRY_QUEUE, json.dumps(payload))
                    logger.info("Restored pending retry job %s to Redis", job.id)
    except Exception as exc:
        logger.warning("Failed to restore pending retries from DB on startup: %s", exc, exc_info=exc)


async def _process_embedding_job(
    session: Any,
    client: GeminiClient,
    job_id: uuid.UUID,
    meeting_id: uuid.UUID,
    chunk_type: str,
    text_content: str,
    speaker_name: str | None,
    sequence: int | None = None,
) -> bool:
    """Delegates chunk checks, overlap calculation, embedding generation, and saving to RAG service layer."""
    return await process_rag_ingestion_job(
        session=session,
        client=client,
        meeting_id=meeting_id,
        chunk_type=chunk_type,
        text_content=text_content,
        speaker_name=speaker_name,
        sequence=sequence,
    )


async def handle_failed_job_retry_setup(
    session: Any,
    redis: Redis,
    job_id: uuid.UUID,
    meeting_id: uuid.UUID,
    chunk_type: str,
    payload: Dict[str, Any],
    error_msg: str,
    attempts: int,
) -> None:
    """Updates failed job state in Postgres and pushes payload to Redis retry or dead-letter queue."""
    # Update attempts
    next_attempts = attempts + 1
    delay = min(300, 10 * (2 ** next_attempts))
    
    # Write failure state to Postgres
    await record_failed_job(
        session=session,
        job_id=job_id,
        meeting_id=meeting_id,
        chunk_type=chunk_type,
        payload=payload,
        error_message=error_msg,
    )
    
    # Enqueue to proper Redis channel
    now = datetime.now(timezone.utc)
    payload["attempts"] = next_attempts
    payload["scheduled_at"] = (now + timedelta(seconds=delay)).isoformat()
    
    if next_attempts >= 5:
        # Pushed to dead-letter queue
        await redis_lpush(redis, DEAD_LETTER_QUEUE, json.dumps(payload))
        logger.error("Job %s reached maximum retries and has been dead-lettered.", job_id)
    else:
        # Pushed to retry queue
        await redis_lpush(redis, RETRY_QUEUE, json.dumps(payload))
        logger.info("Job %s enqueued to retry_queue with delay %ds (Attempt %d)", job_id, delay, next_attempts)


async def run_ingestion_consumer(
    redis: Redis,
    client: GeminiClient,
    run_once: bool = False,
    shutdown_event: asyncio.Event | None = None,
) -> None:
    """List consumer polling the main ingestion queue."""
    while True:
        if shutdown_event and shutdown_event.is_set():
            break
        try:
            if not ENABLE_RAG:
                try:
                    for _ in range(50):
                        if shutdown_event and shutdown_event.is_set():
                            break
                        await asyncio.sleep(0.1)
                except asyncio.CancelledError:
                    raise
                if run_once:
                    break
                continue

            raw = await redis_brpop(redis, INGESTION_QUEUE, timeout=5)
            if raw is None:
                await asyncio.sleep(0.01)
                if run_once:
                    break
                continue

            try:
                payload: dict = json.loads(raw)
            except Exception:
                logger.warning("RAG worker: invalid JSON payload received in ingestion queue")
                if run_once:
                    break
                continue

            job_id = uuid.UUID(payload["job_id"])
            meeting_id = uuid.UUID(payload["meeting_id"])
            chunk_type = payload["chunk_type"]
            text_content = payload["text_content"]
            speaker_name = payload.get("speaker_name")
            attempts = payload.get("attempts", 0)

            # Process job
            async with async_session_factory() as session:
                async with session.begin():
                    try:
                        await _process_embedding_job(
                            session=session,
                            client=client,
                            job_id=job_id,
                            meeting_id=meeting_id,
                            chunk_type=chunk_type,
                            text_content=text_content,
                            speaker_name=speaker_name,
                            sequence=payload.get("sequence"),
                        )
                    except Exception as exc:
                        # Record failure and schedule retry
                        logger.exception("RAG ingestion error for job %s", job_id)
                        await handle_failed_job_retry_setup(
                            session=session,
                            redis=redis,
                            job_id=job_id,
                            meeting_id=meeting_id,
                            chunk_type=chunk_type,
                            payload=payload,
                            error_msg=str(exc),
                            attempts=attempts,
                        )
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.error("Error in RAG ingestion consumer loop: %s", exc, exc_info=exc)
            try:
                for _ in range(20):
                    if shutdown_event and shutdown_event.is_set():
                        break
                    await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                raise

        if run_once:
            break


async def run_retry_consumer(
    redis: Redis,
    client: GeminiClient,
    run_once: bool = False,
    shutdown_event: asyncio.Event | None = None,
) -> None:
    """Consumer polling the retry queue with exponential backoff checks."""
    while True:
        if shutdown_event and shutdown_event.is_set():
            break
        try:
            if not ENABLE_RAG:
                try:
                    for _ in range(50):
                        if shutdown_event and shutdown_event.is_set():
                            break
                        await asyncio.sleep(0.1)
                except asyncio.CancelledError:
                    raise
                if run_once:
                    break
                continue

            raw = await redis_brpop(redis, RETRY_QUEUE, timeout=5)
            if raw is None:
                await asyncio.sleep(0.01)
                if run_once:
                    break
                continue

            try:
                payload: dict = json.loads(raw)
            except Exception:
                logger.warning("RAG worker: invalid JSON payload received in retry queue")
                if run_once:
                    break
                continue

            job_id = uuid.UUID(payload["job_id"])
            meeting_id = uuid.UUID(payload["meeting_id"])
            chunk_type = payload["chunk_type"]
            text_content = payload["text_content"]
            speaker_name = payload.get("speaker_name")
            attempts = payload.get("attempts", 0)
            scheduled_raw = payload.get("scheduled_at")

            # Check backoff timing
            if scheduled_raw:
                try:
                    scheduled_at = datetime.fromisoformat(scheduled_raw)
                except ValueError:
                    scheduled_at = datetime.now(timezone.utc)
                
                now = datetime.now(timezone.utc)
                if now < scheduled_at:
                    wait_sec = (scheduled_at - now).total_seconds()
                    total_sleep = min(wait_sec, 30.0)
                    if total_sleep > 0:
                        steps = int(total_sleep / 0.1)
                        try:
                            for _ in range(steps):
                                if shutdown_event and shutdown_event.is_set():
                                    break
                                await asyncio.sleep(0.1)
                        except asyncio.CancelledError:
                            raise

            # Process retry job
            async with async_session_factory() as session:
                async with session.begin():
                    try:
                        await _process_embedding_job(
                            session=session,
                            client=client,
                            job_id=job_id,
                            meeting_id=meeting_id,
                            chunk_type=chunk_type,
                            text_content=text_content,
                            speaker_name=speaker_name,
                            sequence=payload.get("sequence"),
                        )
                        # Clean up job upon successful execution
                        await mark_failed_job_completed(session, job_id)
                        logger.info("Successfully recovered failed RAG job %s", job_id)
                    except Exception as exc:
                        logger.exception("RAG retry failed for job %s", job_id)
                        await handle_failed_job_retry_setup(
                            session=session,
                            redis=redis,
                            job_id=job_id,
                            meeting_id=meeting_id,
                            chunk_type=chunk_type,
                            payload=payload,
                            error_msg=str(exc),
                            attempts=attempts,
                        )
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.error("Error in RAG retry consumer loop: %s", exc, exc_info=exc)
            try:
                for _ in range(20):
                    if shutdown_event and shutdown_event.is_set():
                        break
                    await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                raise

        if run_once:
            break


async def run_rag_ingestion_worker(shutdown_event: asyncio.Event | None = None) -> None:
    """Main daemon runner for RAG workers."""
    if not ENABLE_RAG:
        logger.info("RAG is disabled. Ingestion worker will not start.")
        return

    api_key = GEMINI_API_KEY
    if not api_key:
        logger.error("GEMINI_API_KEY environment variable is missing; RAG worker cannot run.")
        return

    # Ensure Redis connectivity before starting
    while True:
        if shutdown_event and shutdown_event.is_set():
            return
        try:
            redis = await get_redis()
            break
        except Exception:
            logger.exception("RAG worker: Redis connection failed, retrying in 5s")
            try:
                for _ in range(50):
                    if shutdown_event and shutdown_event.is_set():
                        return
                    await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                raise

    client = GeminiClient(api_key, GEMINI_EMBEDDING_MODEL_NAME)

    # Restore pending retries on worker startup
    await restore_pending_retries(redis)

    logger.info("RAG Ingestion and Retry workers started successfully.")
    
    # Run ingestion and retry consumers concurrently
    try:
        await asyncio.gather(
            run_ingestion_consumer(redis, client, shutdown_event=shutdown_event),
            run_retry_consumer(redis, client, shutdown_event=shutdown_event)
        )
    except asyncio.CancelledError:
        logger.info("RAG workers shutting down cleanly.")
