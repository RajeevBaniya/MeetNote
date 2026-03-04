import asyncio
import logging

from sqlalchemy import select

from app.core.config import (
    get_database_url,
    get_jwt_secret,
    get_stream_api_key,
    get_stream_webhook_secret,
)
from app.core.database_setup import ensure_database_schema
from app.core.metrics import init_metrics_worker
from app.core.redis import get_redis_url
from app.db.base import engine
from app.db.models import Meeting
from app.db.session import async_session_factory
from app.modules.meetings.events import publish_meeting_snapshot
from app.modules.transcripts.worker import run_transcript_worker

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
    await validate_environment()
    await ensure_database_schema(engine)

    transcript_task: asyncio.Task | None = None
    try:
        init_metrics_worker()
        await _publish_active_meetings_snapshot()
        transcript_task = asyncio.create_task(run_transcript_worker())
    except Exception:
        logger.debug("meeting_snapshot_startup_failed", exc_info=True)

    return transcript_task


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

    if meetings:
        await publish_meeting_snapshot([m.id for m in meetings])