import asyncio
import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select

from app.core.metrics import incr
from app.db.models import Meeting
from app.db.session import async_session_factory
from app.modules.meetings.meeting_lifecycle import end_meeting


logger = logging.getLogger(__name__)

_RUN_INTERVAL_SECONDS = 30 * 60
_STALE_AGE_HOURS = 6


async def _load_abandoned_meetings() -> list[tuple[UUID, UUID | None, UUID | None]]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=_STALE_AGE_HOURS)
    async with async_session_factory() as session:
        result = await session.execute(
            select(Meeting.id, Meeting.current_host_id, Meeting.original_host_id).where(
                Meeting.is_active.is_(True),
                Meeting.created_at < cutoff,
            )
        )
        return [(row[0], row[1], row[2]) for row in result.all()]


async def _close_meeting(
    meeting_id: UUID,
    current_host_id: UUID | None,
    original_host_id: UUID | None,
) -> None:
    host_id = current_host_id or original_host_id
    if host_id is None:
        logger.warning("zombie_meeting_missing_host meeting_id=%s", meeting_id)
        return

    async with async_session_factory() as session:
        try:
            await end_meeting(session, meeting_id, host_id)
            incr("zombie_meetings_cleaned_total")
            logger.info("zombie_meeting_closed", extra={"meeting_id": str(meeting_id)})
        except Exception:
            logger.exception("zombie_meeting_close_failed meeting_id=%s", meeting_id)


async def run_meeting_cleanup_worker() -> None:
    while True:
        try:
            meetings = await _load_abandoned_meetings()
            for meeting_id, current_host_id, original_host_id in meetings:
                await _close_meeting(meeting_id, current_host_id, original_host_id)
        except asyncio.CancelledError:
            break
        except Exception:
            logger.exception("meeting_cleanup_worker_loop_error")
        await asyncio.sleep(_RUN_INTERVAL_SECONDS)

