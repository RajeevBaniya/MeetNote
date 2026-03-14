from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Meeting

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