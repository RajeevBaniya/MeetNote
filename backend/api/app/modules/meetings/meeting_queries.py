from uuid import UUID

from sqlalchemy import desc, distinct, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Meeting, MeetingAnalytics, MeetingParticipantStats

JOIN_CODE_LENGTH = 12


def ensure_host_started(meeting: Meeting, requester_id: UUID) -> None:
    """
    Validate that the host has started the meeting before allowing non-host access.
    
    Args:
        meeting: Meeting instance to check
        requester_id: ID of user requesting access
        
    Raises:
        ValueError: If non-host tries to access before host has joined
    """
    if not meeting.host_joined and requester_id != meeting.current_host_id:
        raise ValueError("HOST_NOT_STARTED")


async def get_meeting_by_id(
    session: AsyncSession,
    meeting_id: UUID,
) -> Meeting | None:
    """
    Retrieve a meeting by its unique ID.
    
    Args:
        session: Database session
        meeting_id: UUID of the meeting
        
    Returns:
        Meeting instance if found, None otherwise
    """
    result = await session.execute(select(Meeting).where(Meeting.id == meeting_id))
    return result.scalar_one_or_none()


async def user_was_meeting_member(
    session: AsyncSession,
    meeting_id: UUID,
    user_id: UUID,
) -> bool:
    meeting = await get_meeting_by_id(session, meeting_id)
    if not meeting:
        return False
    if user_id in (
        meeting.host_id,
        meeting.original_host_id,
        meeting.current_host_id,
    ):
        return True
    row = await session.execute(
        select(MeetingParticipantStats.user_id).where(
            MeetingParticipantStats.meeting_id == meeting_id,
            MeetingParticipantStats.user_id == user_id,
        ).limit(1)
    )
    return row.scalar_one_or_none() is not None


async def get_meeting_by_join_code(
    session: AsyncSession,
    join_code: str,
) -> Meeting | None:
    """
    Retrieve a meeting by its join code with input validation and normalization.
    
    Args:
        session: Database session
        join_code: Join code string (may contain spaces/dashes)
        
    Returns:
        Meeting instance if found and valid, None otherwise
    """
    cleaned = join_code.strip().replace(" ", "").replace("-", "")
    if not cleaned.isdigit() or len(cleaned) != JOIN_CODE_LENGTH:
        return None
    
    result = await session.execute(select(Meeting).where(Meeting.join_code == cleaned))
    return result.scalar_one_or_none()


async def get_meetings_for_host(
    session: AsyncSession,
    host_id: UUID,
    ended_limit: int,
) -> tuple[list[Meeting], list[Meeting]]:
    """
    Retrieve active and recent ended meetings for a specific host.
    
    Args:
        session: Database session
        host_id: UUID of the host
        ended_limit: Maximum number of ended meetings to return
        
    Returns:
        Tuple of (active_meetings, ended_meetings) lists
    """
    # Get all active meetings for this host
    active_result = await session.execute(
        select(Meeting)
        .where(Meeting.host_id == host_id, Meeting.is_active.is_(True))
        .order_by(desc(Meeting.created_at))
    )
    active_meetings = list(active_result.scalars().all())

    # Get recent ended meetings for this host
    ended_result = await session.execute(
        select(Meeting)
        .where(Meeting.host_id == host_id, Meeting.is_active.is_(False))
        .order_by(desc(Meeting.created_at))
        .limit(ended_limit)
    )
    ended_meetings = list(ended_result.scalars().all())

    return active_meetings, ended_meetings


async def list_meetings_for_user_host_or_participant(
    session: AsyncSession,
    user_id: UUID,
    *,
    limit: int = 200,
) -> list[tuple[Meeting, int]]:
    """
    Meetings where the user is host (any host role field) or has participant stats.
    Participant count prefers analytics total_participants, else count of participant rows.
    """
    user_is_participant = exists(
        select(MeetingParticipantStats.user_id).where(
            MeetingParticipantStats.meeting_id == Meeting.id,
            MeetingParticipantStats.user_id == user_id,
        )
    )
    user_is_host_family = or_(
        Meeting.host_id == user_id,
        Meeting.original_host_id == user_id,
        Meeting.current_host_id == user_id,
    )
    stats_count = (
        select(func.count(distinct(MeetingParticipantStats.user_id)))
        .select_from(MeetingParticipantStats)
        .where(MeetingParticipantStats.meeting_id == Meeting.id)
        .scalar_subquery()
    )
    participant_count_expr = func.coalesce(
        MeetingAnalytics.total_participants,
        stats_count,
        0,
    )
    stmt = (
        select(Meeting, participant_count_expr)
        .outerjoin(MeetingAnalytics, MeetingAnalytics.meeting_id == Meeting.id)
        .where(or_(user_is_host_family, user_is_participant))
        .order_by(desc(Meeting.created_at))
        .limit(limit)
    )
    result = await session.execute(stmt)
    rows = result.all()
    out: list[tuple[Meeting, int]] = []
    for meeting, p_count in rows:
        out.append((meeting, int(p_count or 0)))
    return out