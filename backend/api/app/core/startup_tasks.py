import asyncio
import logging

from sqlalchemy import select

from app.state.client import get_redis
from app.core.config import (
    get_database_url,
    get_jwt_secret,
    get_stream_api_key,
    get_stream_webhook_secret,
    is_rag_enabled,
)
from app.core.database_setup import ensure_database_schema
from app.core.error_monitoring import initialize_error_monitoring, run_worker_with_sentry
from app.core.metrics import init_metrics_worker, set_gauge
from app.core.redis import get_redis_url
from app.db.base import engine
from app.db.models import Meeting
from app.db.session import async_session_factory
from app.modules.meetings.events import publish_meeting_snapshot
from app.modules.transcripts.worker import run_transcript_worker
from app.workers.convergence_auditor import run_convergence_auditor
from app.workers.meeting_cleanup_worker import run_meeting_cleanup_worker
from app.workers.rag_ingestion_worker import run_rag_ingestion_worker

logger = logging.getLogger(__name__)


async def validate_environment() -> None:
    """
    Validates that all required environment variables are set.
    Raises ValueError if any critical configuration is missing.
    """
    get_database_url()
    get_jwt_secret()
    get_stream_api_key()
    get_stream_webhook_secret()

    if not get_redis_url():
        raise ValueError("REDIS_URL is required")


async def initialize_application() -> asyncio.Task | None:
    """
    Performs all application initialization tasks.
    Returns the transcript worker task if successfully started.
    """
    initialize_error_monitoring()
    await validate_environment()
    await ensure_database_schema(engine)
    await _warn_if_redis_persistence_disabled()

    transcript_task: asyncio.Task | None = None
    try:
        init_metrics_worker()
        await _publish_active_meetings_snapshot()
        transcript_task = asyncio.create_task(
            run_worker_with_sentry("transcript_worker", run_transcript_worker)
        )
        asyncio.create_task(
            run_worker_with_sentry("convergence_auditor", run_convergence_auditor)
        )
        asyncio.create_task(
            run_worker_with_sentry("meeting_cleanup_worker", run_meeting_cleanup_worker)
        )
        if is_rag_enabled():
            asyncio.create_task(
                run_worker_with_sentry("rag_ingestion_worker", run_rag_ingestion_worker)
            )
    except Exception:
        logger.debug("meeting_snapshot_startup_failed", exc_info=True)

    return transcript_task


async def _warn_if_redis_persistence_disabled() -> None:
    try:
        redis = await get_redis()
        info = await redis.info()
    except Exception:
        logger.debug("redis_info_unavailable", exc_info=True)
        return

    appendonly = info.get("appendonly")
    if appendonly is None:
        return
    normalized = str(appendonly).strip().lower()
    if normalized in {"0", "no", "false"}:
        logger.warning("redis_persistence_disabled")


async def _publish_active_meetings_snapshot() -> None:
    """
    Publishes a snapshot of all currently active meetings.
    This helps synchronize the system state on startup.
    """
    async with async_session_factory() as session:
        result = await session.execute(
            select(Meeting).where(Meeting.is_active.is_(True))
        )
        meetings = list(result.scalars().all())

    await set_gauge("active_meetings", len(meetings))
    if meetings:
        try:
            redis = await get_redis()
            for m in meetings:
                await redis.set(f"meeting:host_id:{m.id}", str(m.current_host_id))
        except Exception as exc:
            logger.warning("Failed to cache active meeting host IDs on startup", exc_info=exc)
        await publish_meeting_snapshot([m.id for m in meetings])