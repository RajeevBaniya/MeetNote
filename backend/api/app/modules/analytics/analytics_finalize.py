"""Analytics lifecycle: init on meeting creation, finalize on meeting end, host transfer."""

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.metrics import incr
from app.db.models import Meeting, MeetingAnalytics, MeetingParticipantStats
from app.db.session import async_session_factory

logger = logging.getLogger(__name__)


async def init_analytics(meeting_id: UUID, started_at: datetime | None = None) -> None:
    """Create analytics row on meeting creation. Idempotent."""
    now = started_at or datetime.now(timezone.utc)
    async with async_session_factory() as session:
        async with session.begin():
            existing = await session.execute(
                select(MeetingAnalytics).where(MeetingAnalytics.meeting_id == meeting_id)
            )
            if existing.scalar_one_or_none() is not None:
                return
            row = MeetingAnalytics(
                meeting_id=meeting_id,
                started_at=now,
                duration_seconds=0,
            )
            session.add(row)
        incr("analytics_updates_total")
        logger.info(
            "analytics_initialized",
            extra={"meeting_id": str(meeting_id)},
        )


async def finalize_analytics(meeting_id: UUID, ended_at: datetime | None = None) -> None:
    """Finalize analytics on meeting end. Idempotent; runs once per meeting."""
    now = ended_at or datetime.now(timezone.utc)
    try:
        async with async_session_factory() as session:
            async with session.begin():
                result = await session.execute(
                    select(MeetingAnalytics)
                    .where(
                        MeetingAnalytics.meeting_id == meeting_id,
                        MeetingAnalytics.ended_at.is_(None),
                    )
                    .with_for_update()
                )
                analytics = result.scalar_one_or_none()
                if not analytics:
                    return
                duration = int((now - analytics.started_at).total_seconds())
                stats_result = await session.execute(
                    select(MeetingParticipantStats)
                    .where(MeetingParticipantStats.meeting_id == meeting_id)
                    .with_for_update()
                )
                participants = list(stats_result.scalars().all())
                for row in participants:
                    if row.left_at is None:
                        delta = int((now - row.joined_at).total_seconds())
                        row.left_at = now
                        row.total_time_seconds = row.total_time_seconds + delta
                total_participants = len(participants)
                update_result = await session.execute(
                    update(MeetingAnalytics)
                    .where(
                        MeetingAnalytics.meeting_id == meeting_id,
                        MeetingAnalytics.ended_at.is_(None),
                    )
                    .values(
                        ended_at=now,
                        duration_seconds=duration,
                        total_participants=total_participants,
                        updated_at=now,
                    )
                )
                if update_result.rowcount == 0:
                    return
                await session.execute(
                    update(Meeting)
                    .where(Meeting.id == meeting_id)
                    .values(analytics_state="finalized")
                )
        incr("analytics_updates_total")
        logger.info(
            "analytics_finalized",
            extra={
                "meeting_id": str(meeting_id),
                "duration_seconds": duration,
                "total_participants": total_participants,
            },
        )
    except Exception:
        logger.exception("analytics_finalize_failed meeting_id=%s", meeting_id)
        async with async_session_factory() as session:
            async with session.begin():
                await session.execute(
                    update(Meeting)
                    .where(Meeting.id == meeting_id)
                    .values(analytics_state="failed")
                )
        raise


async def increment_host_transfer_in_session(
    session: AsyncSession,
    meeting_id: UUID,
    new_host_id: UUID,
) -> None:
    """Increment host_transfers only if host actually changed in this transaction."""
    result = await session.execute(
        update(MeetingAnalytics)
        .where(
            MeetingAnalytics.meeting_id == meeting_id,
            MeetingAnalytics.meeting_id.in_(
                select(Meeting.id).where(
                    Meeting.id == meeting_id,
                    Meeting.current_host_id == new_host_id,
                )
            ),
        )
        .values(host_transfers=MeetingAnalytics.host_transfers + 1)
    )
    if result.rowcount > 0:
        incr("analytics_updates_total")


async def increment_host_transfer(meeting_id: UUID, new_host_id: UUID) -> None:
    """Increment host_transfers in own session. Use after Redis idempotency check."""
    async with async_session_factory() as session:
        async with session.begin():
            result = await session.execute(
                update(MeetingAnalytics)
                .where(
                    MeetingAnalytics.meeting_id == meeting_id,
                    MeetingAnalytics.meeting_id.in_(
                        select(Meeting.id).where(
                            Meeting.id == meeting_id,
                            Meeting.current_host_id == new_host_id,
                        )
                    ),
                )
                .values(host_transfers=MeetingAnalytics.host_transfers + 1)
            )
            if result.rowcount > 0:
                incr("analytics_updates_total")
