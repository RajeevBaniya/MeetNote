import asyncio
import logging
from datetime import datetime, timezone
from typing import Iterable
from uuid import UUID

from sqlalchemy import select, update

from app.core.dependencies import get_service
from app.core.interfaces import (
    AnalyticsServiceInterface,
    CacheServiceInterface,
    ChatServiceInterface,
    EventServiceInterface,
    StreamServiceInterface,
    TranscriptServiceInterface,
)
from app.core.metrics import incr
from app.db.models import Meeting
from app.db.session import async_session_factory
from app.modules.stream_tokens.constants import STREAM_CALL_TYPE

logger = logging.getLogger(__name__)


async def _load_unconverged_meetings() -> Iterable[Meeting]:
    async with async_session_factory() as session:
        result = await session.execute(
            select(Meeting).where(
                Meeting.is_active.is_(False),
                Meeting.convergence_state != "converged",
            )
        )
        return list(result.scalars().all())


async def _run_repair_tasks(
    meeting_id: UUID,
    ended_at: datetime | None,
    current_host_id: UUID | None,
    host_joined: bool = False,
) -> bool:
    analytics_service = get_service(AnalyticsServiceInterface)  # type: ignore[type-abstract]
    stream_service = get_service(StreamServiceInterface)  # type: ignore[type-abstract]
    event_service = get_service(EventServiceInterface)  # type: ignore[type-abstract]
    chat_service = get_service(ChatServiceInterface)  # type: ignore[type-abstract]
    cache_service = get_service(CacheServiceInterface)  # type: ignore[type-abstract]
    transcript_service = get_service(TranscriptServiceInterface)  # type: ignore[type-abstract]

    ok = True

    try:
        await analytics_service.finalize_meeting_analytics(
            meeting_id, ended_at or datetime.now(timezone.utc)
        )
    except Exception:
        logger.exception("convergence_analytics_repair_failed meeting_id=%s", meeting_id)
        ok = False

    try:
        if current_host_id is not None and host_joined:
            await stream_service.end_call(
                STREAM_CALL_TYPE,
                str(meeting_id),
                current_host_id,
            )
    except Exception:
        logger.exception("convergence_stream_repair_failed meeting_id=%s", meeting_id)
        ok = False

    try:
        await event_service.publish_meeting_ended(meeting_id)
    except Exception:
        logger.exception("convergence_events_repair_failed meeting_id=%s", meeting_id)
        ok = False

    try:
        await chat_service.close_meeting_connections(meeting_id)
    except Exception:
        logger.exception("convergence_chat_repair_failed meeting_id=%s", meeting_id)
        ok = False

    try:
        await transcript_service.expire_meeting_keys(cache_service, meeting_id)
        await cache_service.delete_keys(
            f"assistant_enabled:{meeting_id}",
            f"meeting:{meeting_id}:removed_users",
        )
    except Exception:
        logger.exception("convergence_transcript_repair_failed meeting_id=%s", meeting_id)
        ok = False

    return ok


async def _mark_converged(meeting_id: UUID) -> None:
    now = datetime.now(timezone.utc)
    async with async_session_factory() as session:
        async with session.begin():
            db_meeting = await session.get(Meeting, meeting_id)
            if db_meeting is None:
                return
            started = db_meeting.convergence_started_at or db_meeting.ended_at or now
            await session.execute(
                update(Meeting)
                .where(Meeting.id == meeting_id)
                .values(
                    convergence_state="converged",
                    convergence_completed_at=now,
                )
            )
    seconds = max(0, int((now - started).total_seconds()))
    if seconds:
        incr("meeting_convergence_seconds", seconds)
    incr("meeting_convergence_repaired_total")


async def _mark_failed(meeting_id: UUID) -> None:
    async with async_session_factory() as session:
        async with session.begin():
            await session.execute(
                update(Meeting)
                .where(Meeting.id == meeting_id)
                .values(convergence_state="failed")
            )
    incr("meeting_convergence_failed_total")


async def run_convergence_auditor(shutdown_event: asyncio.Event | None = None) -> None:
    while True:
        if shutdown_event and shutdown_event.is_set():
            break
        try:
            meetings = await _load_unconverged_meetings()
            for meeting in meetings:
                if shutdown_event and shutdown_event.is_set():
                    break
                try:
                    ok = await _run_repair_tasks(
                        meeting.id,
                        meeting.ended_at,
                        meeting.current_host_id,
                        meeting.host_joined,
                    )
                except Exception:
                    logger.exception("convergence_repair_unexpected_error meeting_id=%s", meeting.id)
                    ok = False
                if ok:
                    await _mark_converged(meeting.id)
                else:
                    await _mark_failed(meeting.id)
        except asyncio.CancelledError:
            break
        except Exception:
            logger.exception("convergence_auditor_loop_error")

        # Sleep up to 60 seconds, but check shutdown_event every 0.1s for responsiveness
        try:
            for _ in range(600):
                if shutdown_event and shutdown_event.is_set():
                    break
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            raise

