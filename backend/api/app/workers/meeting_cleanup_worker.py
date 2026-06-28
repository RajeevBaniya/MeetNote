import asyncio
import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select, delete

from app.core.config import (
    MEETING_CLEANUP_INTERVAL_SECONDS,
    MEETING_STALE_CLEANUP_HOURS,
)
from app.core.metrics import incr
from app.db.models import Meeting, MeetingTranscript, MeetingTranscriptChunk
from app.db.session import async_session_factory
from app.modules.meetings.meeting_lifecycle import end_meeting

logger = logging.getLogger(__name__)


async def _load_abandoned_meetings() -> list[tuple[UUID, UUID | None, UUID | None]]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=MEETING_STALE_CLEANUP_HOURS)
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


async def _expire_old_transcripts() -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    async with async_session_factory() as session:
        async with session.begin():
            # Find ended meetings that ended before the 7-day cutoff
            stmt = select(Meeting.id).where(
                Meeting.is_active.is_(False),
                Meeting.ended_at < cutoff,
            )
            res = await session.execute(stmt)
            meeting_ids = res.scalars().all()
            
            if not meeting_ids:
                return

            # Purge raw transcript lines
            del_transcripts_stmt = delete(MeetingTranscript).where(
                MeetingTranscript.meeting_id.in_(meeting_ids)
            )
            await session.execute(del_transcripts_stmt)

            # Purge transcript chunks and their vector embeddings
            del_chunks_stmt = delete(MeetingTranscriptChunk).where(
                MeetingTranscriptChunk.meeting_id.in_(meeting_ids)
            )
            await session.execute(del_chunks_stmt)
            
            logger.info(
                "expired_old_transcripts_cleanup",
                extra={"meetings_purged": len(meeting_ids)}
            )


async def run_meeting_cleanup_worker(shutdown_event: asyncio.Event | None = None) -> None:
    while True:
        if shutdown_event and shutdown_event.is_set():
            break
        try:
            meetings = await _load_abandoned_meetings()
            for meeting_id, current_host_id, original_host_id in meetings:
                if shutdown_event and shutdown_event.is_set():
                    break
                await _close_meeting(meeting_id, current_host_id, original_host_id)
            
            await _expire_old_transcripts()
        except asyncio.CancelledError:
            break
        except Exception:
            logger.exception("meeting_cleanup_worker_loop_error")

        # Sleep up to MEETING_CLEANUP_INTERVAL_SECONDS, but check shutdown_event every 0.1s for responsiveness
        try:
            steps = int(MEETING_CLEANUP_INTERVAL_SECONDS / 0.1)
            for _ in range(steps):
                if shutdown_event and shutdown_event.is_set():
                    break
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            raise

