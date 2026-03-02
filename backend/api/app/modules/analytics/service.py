"""Analytics service: meeting insights, participant stats, speaking time."""

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.metrics import incr
from app.db.models import Meeting, MeetingAnalytics, MeetingParticipantStats
from app.db.session import async_session_factory

logger = logging.getLogger(__name__)

WORDS_PER_SECOND = 3


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
        incr("analytics_updates_total")
        logger.info(
            "analytics_finalized",
            extra={
                "meeting_id": str(meeting_id),
                "duration_seconds": duration,
                "total_participants": total_participants,
            },
        )


async def record_participant_join(
    meeting_id: UUID,
    user_id: UUID,
    joined_at: datetime | None = None,
) -> None:
    """Record participant join. Enforces single active session per user per meeting."""
    now = joined_at or datetime.now(timezone.utc)
    async with async_session_factory() as session:
        async with session.begin():
            result = await session.execute(
                select(Meeting.is_active)
                .where(Meeting.id == meeting_id)
            )
            meeting_row = result.scalar_one_or_none()

            if meeting_row is not True:
                logger.info(
                    "participant_join_ignored_meeting_ended",
                    extra={
                        "meeting_id": str(meeting_id),
                        "user_id": str(user_id),
                        "reason": "meeting_not_active",
                    },
                )
                incr("analytics_mutations_blocked_after_end_total")
                return
            
            result = await session.execute(
                select(MeetingParticipantStats.joined_at, MeetingParticipantStats.left_at)
                .where(
                    MeetingParticipantStats.meeting_id == meeting_id,
                    MeetingParticipantStats.user_id == user_id,
                )
                .with_for_update()
            )
            existing = result.first()
            
            if existing is None:
                # Case A: No row exists → Insert normally
                row = MeetingParticipantStats(
                    meeting_id=meeting_id,
                    user_id=user_id,
                    joined_at=now,
                )
                session.add(row)
            elif existing.joined_at is not None and existing.left_at is None:
                # Case B: User already active → ignore duplicate join
                incr("analytics_session_anomaly_total")
                logger.warning(
                    "duplicate_join_ignored",
                    extra={
                        "meeting_id": str(meeting_id),
                        "user_id": str(user_id),
                        "existing_joined_at": str(existing.joined_at),
                    },
                )
                return
            elif existing.joined_at is None and existing.left_at is not None:
                # Case C: User rejoining → set joined_at, clear left_at
                await session.execute(
                    update(MeetingParticipantStats)
                    .where(
                        MeetingParticipantStats.meeting_id == meeting_id,
                        MeetingParticipantStats.user_id == user_id,
                    )
                    .values(joined_at=now, left_at=None)
                )
            elif existing.joined_at is not None and existing.left_at is not None:
                # Case D: Inconsistent state → force-correct then treat as rejoin
                incr("analytics_session_anomaly_total")
                logger.warning(
                    "overlapping_session_corrected",
                    extra={
                        "meeting_id": str(meeting_id),
                        "user_id": str(user_id),
                        "existing_joined_at": str(existing.joined_at),
                        "existing_left_at": str(existing.left_at),
                    },
                )
                # Normalize if left_at < joined_at
                corrected_left_at = existing.left_at
                if existing.left_at < existing.joined_at:
                    corrected_left_at = existing.joined_at
                    logger.warning(
                        "timestamp_anomaly_corrected",
                        extra={
                            "meeting_id": str(meeting_id),
                            "user_id": str(user_id),
                            "left_at": str(existing.left_at),
                            "joined_at": str(existing.joined_at),
                        },
                    )
                # Treat as rejoin
                await session.execute(
                    update(MeetingParticipantStats)
                    .where(
                        MeetingParticipantStats.meeting_id == meeting_id,
                        MeetingParticipantStats.user_id == user_id,
                    )
                    .values(joined_at=now, left_at=None)
                )
        incr("analytics_updates_total")
        logger.info(
            "participant_join_recorded",
            extra={"meeting_id": str(meeting_id), "user_id": str(user_id)},
        )


async def record_participant_leave(
    meeting_id: UUID,
    user_id: UUID,
    left_at: datetime | None = None,
) -> None:
    """Record participant leave. Updates total_time_seconds with timestamp validation."""
    now = left_at or datetime.now(timezone.utc)
    async with async_session_factory() as session:
        async with session.begin():
            result = await session.execute(
                select(Meeting.is_active)
                .where(Meeting.id == meeting_id)
            )
            meeting_row = result.scalar_one_or_none()

            if meeting_row is not True:
                logger.info(
                    "participant_leave_ignored_meeting_ended",
                    extra={
                        "meeting_id": str(meeting_id),
                        "user_id": str(user_id),
                        "reason": "meeting_not_active",
                    },
                )
                incr("analytics_mutations_blocked_after_end_total")
                return
            
            # First check for anomalies
            check_result = await session.execute(
                select(MeetingParticipantStats.joined_at, MeetingParticipantStats.left_at)
                .where(
                    MeetingParticipantStats.meeting_id == meeting_id,
                    MeetingParticipantStats.user_id == user_id,
                )
            )
            existing = check_result.first()
            
            if existing is None or existing.joined_at is None:
                # Leave without join anomaly
                incr("analytics_session_anomaly_total")
                logger.warning(
                    "leave_without_join_anomaly",
                    extra={
                        "meeting_id": str(meeting_id),
                        "user_id": str(user_id),
                        "left_at": str(now),
                    },
                )
                return
            
            if existing.left_at is not None:
                # Already left anomaly  
                incr("analytics_session_anomaly_total")
                logger.warning(
                    "duplicate_leave_ignored",
                    extra={
                        "meeting_id": str(meeting_id),
                        "user_id": str(user_id),
                        "existing_left_at": str(existing.left_at),
                        "new_left_at": str(now),
                    },
                )
                return
            
            if now < existing.joined_at:
                # Timestamp anomaly: left_at < joined_at
                incr("analytics_session_anomaly_total")
                logger.warning(
                    "leave_before_join_anomaly",
                    extra={
                        "meeting_id": str(meeting_id),
                        "user_id": str(user_id),
                        "joined_at": str(existing.joined_at),
                        "left_at": str(now),
                    },
                )
                # Set left_at but skip delta computation
                await session.execute(
                    update(MeetingParticipantStats)
                    .where(
                        MeetingParticipantStats.meeting_id == meeting_id,
                        MeetingParticipantStats.user_id == user_id,
                    )
                    .values(left_at=now)
                )
                return
            
            # Normal case: update with delta computation
            result = await session.execute(
                text("""
                UPDATE meeting_participant_stats 
                SET 
                    left_at = :left_at,
                    total_time_seconds = total_time_seconds + EXTRACT(EPOCH FROM (:left_at - joined_at))
                WHERE meeting_id = :meeting_id
                  AND user_id = :user_id  
                  AND joined_at IS NOT NULL
                  AND left_at IS NULL
                  AND joined_at <= :left_at
                """),
                {
                    "left_at": now,
                    "meeting_id": meeting_id,
                    "user_id": user_id,
                }
            )
            if result.rowcount == 0:
                return
        incr("analytics_updates_total")
        logger.info(
            "participant_leave_recorded",
            extra={"meeting_id": str(meeting_id), "user_id": str(user_id)},
        )


async def add_speaking_time(
    meeting_id: UUID,
    user_id: UUID,
    word_count: int,
) -> None:
    """Add speaking time: floor(word_count / 3) seconds. Only for final segments."""
    if word_count <= 0:
        return
    seconds = word_count // WORDS_PER_SECOND
    if seconds <= 0:
        return
    async with async_session_factory() as session:
        async with session.begin():
            result = await session.execute(
                select(Meeting.is_active)
                .where(Meeting.id == meeting_id)
            )
            meeting_row = result.scalar_one_or_none()

            if meeting_row is not True:
                logger.info(
                    "speaking_time_ignored_meeting_ended",
                    extra={
                        "meeting_id": str(meeting_id),
                        "user_id": str(user_id),
                        "word_count": word_count,
                        "reason": "meeting_not_active",
                    },
                )
                incr("analytics_mutations_blocked_after_end_total")
                return
            
            result = await session.execute(
                select(MeetingParticipantStats)
                .where(
                    MeetingParticipantStats.meeting_id == meeting_id,
                    MeetingParticipantStats.user_id == user_id,
                )
                .with_for_update()
            )
            row = result.scalar_one_or_none()
            if row is None:
                row = MeetingParticipantStats(
                    meeting_id=meeting_id,
                    user_id=user_id,
                    joined_at=datetime.now(timezone.utc),
                )
                session.add(row)
                await session.flush()
            await session.execute(
                update(MeetingParticipantStats)
                .where(
                    MeetingParticipantStats.meeting_id == meeting_id,
                    MeetingParticipantStats.user_id == user_id,
                )
                .values(
                    speaking_time_seconds=MeetingParticipantStats.speaking_time_seconds
                    + seconds
                )
            )
            await session.execute(
                update(MeetingAnalytics)
                .where(MeetingAnalytics.meeting_id == meeting_id)
                .values(transcript_segments=MeetingAnalytics.transcript_segments + 1)
            )
        incr("analytics_updates_total")
        incr("speaking_time_updates_total")


async def increment_host_transfer_in_session(
    session: AsyncSession,
    meeting_id: UUID,
    new_host_id: UUID,
) -> None:
    """Increment host_transfers only if host actually changed in this transaction."""
    from app.db.models import Meeting
    result = await session.execute(
        update(MeetingAnalytics)
        .where(
            MeetingAnalytics.meeting_id == meeting_id,
            MeetingAnalytics.meeting_id.in_(
                select(Meeting.id).where(
                    Meeting.id == meeting_id,
                    Meeting.current_host_id == new_host_id
                )
            )
        )
        .values(host_transfers=MeetingAnalytics.host_transfers + 1)
    )
    if result.rowcount > 0:
        incr("analytics_updates_total")


async def increment_host_transfer(meeting_id: UUID, new_host_id: UUID) -> None:
    """Increment host_transfers in own session. Use after Redis idempotency check."""
    async with async_session_factory() as session:
        async with session.begin():
            from app.db.models import Meeting
            result = await session.execute(
                update(MeetingAnalytics)
                .where(
                    MeetingAnalytics.meeting_id == meeting_id,
                    MeetingAnalytics.meeting_id.in_(
                        select(Meeting.id).where(
                            Meeting.id == meeting_id,
                            Meeting.current_host_id == new_host_id
                        )
                    )
                )
                .values(host_transfers=MeetingAnalytics.host_transfers + 1)
            )
            if result.rowcount > 0:
                incr("analytics_updates_total")


async def get_analytics_for_meeting(
    session: AsyncSession,
    meeting_id: UUID,
) -> tuple[MeetingAnalytics | None, list[MeetingParticipantStats]]:
    """Fetch analytics and participant stats for a meeting."""
    result = await session.execute(
        select(MeetingAnalytics).where(MeetingAnalytics.meeting_id == meeting_id)
    )
    analytics = result.scalar_one_or_none()
    stats_result = await session.execute(
        select(MeetingParticipantStats)
        .where(MeetingParticipantStats.meeting_id == meeting_id)
        .order_by(MeetingParticipantStats.joined_at)
    )
    participants = list(stats_result.scalars().all())
    return analytics, participants
