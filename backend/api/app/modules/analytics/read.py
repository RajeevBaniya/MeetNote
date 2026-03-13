"""Analytics read: fetch meeting analytics and participant stats."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import MeetingAnalytics, MeetingParticipantStats


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
