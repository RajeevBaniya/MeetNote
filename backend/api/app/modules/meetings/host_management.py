import logging
from uuid import UUID

from sqlalchemy import select, update

from app.core.dependencies import get_service
from app.core.interfaces import (
    AnalyticsServiceInterface,
    CacheServiceInterface,
    MetricsServiceInterface,
    StreamServiceInterface,
)
from app.db.models import Meeting
from app.db.session import async_session_factory
from app.modules.stream_tokens.constants import STREAM_CALL_TYPE

logger = logging.getLogger(__name__)


async def select_next_host_candidate(
    meeting_id: UUID,
    original_host_id: UUID,
    exclude_user_id: UUID,
) -> UUID | None:
    """
    Select the next available host from active Stream call members.
    
    Args:
        meeting_id: UUID of the meeting
        original_host_id: UUID of original host (for Stream API access)
        exclude_user_id: UUID of user to exclude from selection
        
    Returns:
        UUID of selected candidate or None if no suitable candidate found
    """
    try:
        stream_service = get_service(StreamServiceInterface)  # type: ignore[type-abstract]
        members = await stream_service.query_call_members(
            call_type=STREAM_CALL_TYPE,
            call_id=str(meeting_id),
            acting_user_id=original_host_id,
        )
    except Exception as exc:
        logger.warning(
            "host_candidate_stream_query_failed",
            extra={"meeting_id": str(meeting_id), "error": str(exc)},
            exc_info=exc,
        )
        return None
    
    # Find first valid member who is not the excluded user
    for member in members:
        uid = member.get("user_id")
        if not uid or not isinstance(uid, str):
            continue
        
        try:
            user_uuid = UUID(uid)
        except Exception:
            continue  # skip non-UUID string when selecting host candidate
            
        return user_uuid
    
    return None


async def transfer_host_if_current_disconnected(
    meeting_id: UUID,
    disconnected_user_id: UUID | None,
) -> UUID | None:
    """
    Transfer host role if current host has disconnected from the Stream call.
    
    Args:
        meeting_id: UUID of the meeting
        disconnected_user_id: UUID of user who disconnected (None to check current host)
        
    Returns:
        UUID of new host if transfer occurred, None otherwise
    """
    # Get meeting info outside transaction to avoid locking during Stream API calls
    meeting = await _get_meeting_for_host_check(meeting_id)
    if not meeting:
        return None
    
    target_id = disconnected_user_id or meeting.current_host_id
    if meeting.current_host_id != target_id:
        return None
    
    # Check if target user is still connected to Stream call
    connected_ids = await _get_connected_user_ids(meeting_id, meeting.original_host_id)
    if connected_ids is None:
        return None
    
    if target_id in connected_ids:
        return None  # Host is still connected
    
    # Find a replacement host
    candidate = await select_next_host_candidate(
        meeting_id=meeting_id,
        original_host_id=meeting.original_host_id,
        exclude_user_id=target_id,
    )
    
    if candidate is None:
        return None
    
    # Update host in database with proper locking
    success = await _update_meeting_host(meeting_id, target_id, candidate)
    if not success:
        return None
    
    # Record host transfer metrics and analytics
    await _record_host_transfer(meeting_id, target_id, candidate)
    
    return candidate


async def restore_original_host_if_rejoined(
    meeting_id: UUID,
    user_id: UUID,
) -> UUID | None:
    """
    Restore original host role if they have rejoined the Stream call.
    
    Args:
        meeting_id: UUID of the meeting
        user_id: UUID of user who may be the original host
        
    Returns:
        UUID of restored host if successful, None otherwise
    """
    # Get meeting info outside transaction
    meeting = await _get_meeting_for_host_check(meeting_id)
    if not meeting:
        return None
    
    # Check if this user is the original host and not currently host
    if meeting.original_host_id != user_id:
        return None
    if meeting.current_host_id == meeting.original_host_id:
        return None  # Already the host
    
    # Verify user is connected to Stream call
    connected_ids = await _get_connected_user_ids(meeting_id, user_id)
    if connected_ids is None or str(user_id) not in {str(uid) for uid in connected_ids}:
        return None
    
    # Restore original host in database
    success = await _restore_original_host_in_db(meeting_id, user_id)
    if success:
        return meeting.original_host_id
    
    return None


async def ensure_host_consistency(meeting_id: UUID) -> UUID | None:
    """
    Ensure host consistency by checking if current host is still connected.
    This is a convenience wrapper around transfer_host_if_current_disconnected.
    """
    return await transfer_host_if_current_disconnected(meeting_id, None)


async def _get_meeting_for_host_check(meeting_id: UUID) -> Meeting | None:
    """Get meeting info for host consistency checks."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(Meeting).where(Meeting.id == meeting_id)
        )
        meeting = result.scalar_one_or_none()
        if not meeting or not meeting.is_active:
            return None
        return meeting


async def _get_connected_user_ids(meeting_id: UUID, acting_user_id: UUID) -> set[UUID] | None:
    """Get set of user IDs currently connected to the Stream call."""
    try:
        stream_service = get_service(StreamServiceInterface)  # type: ignore[type-abstract]
        members = await stream_service.query_call_members(
            call_type=STREAM_CALL_TYPE,
            call_id=str(meeting_id),
            acting_user_id=acting_user_id,
        )
    except Exception as exc:
        logger.warning(
            "host_check_stream_query_failed",
            extra={"meeting_id": str(meeting_id), "error": str(exc)},
            exc_info=exc,
        )
        return None
    
    connected_ids: set[UUID] = set()
    for member in members:
        uid = member.get("user_id")
        if not uid or not isinstance(uid, str):
            continue
        try:
            connected_ids.add(UUID(uid))
        except Exception:
            continue  # skip invalid member uid from Stream API

    return connected_ids


async def _update_meeting_host(meeting_id: UUID, current_host_id: UUID, new_host_id: UUID) -> bool:
    """Update meeting host with proper database locking."""
    async with async_session_factory() as session:
        async with session.begin():
            # Re-check meeting state with lock
            result = await session.execute(
                select(Meeting).where(Meeting.id == meeting_id).with_for_update()
            )
            meeting = result.scalar_one_or_none()
            if not meeting or not meeting.is_active:
                return False
            
            # Verify current host hasn't changed
            if meeting.current_host_id != current_host_id:
                return False
            
            # Update to new host
            await session.execute(
                update(Meeting)
                .where(Meeting.id == meeting_id)
                .values(current_host_id=new_host_id)
            )
    
    return True


async def _restore_original_host_in_db(meeting_id: UUID, original_host_id: UUID) -> bool:
    """Restore original host in database with proper locking."""
    async with async_session_factory() as session:
        async with session.begin():
            # Re-check meeting state with lock
            result = await session.execute(
                select(Meeting).where(Meeting.id == meeting_id).with_for_update()
            )
            meeting = result.scalar_one_or_none()
            if not meeting or not meeting.is_active:
                return False
            if meeting.original_host_id != original_host_id:
                return False
            if meeting.current_host_id == meeting.original_host_id:
                return False  # Already restored
            
            # Restore original host
            await session.execute(
                update(Meeting)
                .where(Meeting.id == meeting_id)
                .values(current_host_id=meeting.original_host_id)
            )
            
            return True


async def _record_host_transfer(meeting_id: UUID, old_host_id: UUID, new_host_id: UUID) -> None:
    """Record host transfer in metrics and analytics."""
    metrics_service = get_service(MetricsServiceInterface)  # type: ignore[type-abstract]
    cache_service = get_service(CacheServiceInterface)  # type: ignore[type-abstract]
    analytics_service = get_service(AnalyticsServiceInterface)  # type: ignore[type-abstract]
    
    metrics_service.increment_counter("host_transfers_total")
    
    try:
        key = f"analytics_host_transfer_seen:{meeting_id}:{old_host_id}:{new_host_id}"
        if await cache_service.set_with_expiry(key, "1", 600, only_if_not_exists=True):
            await analytics_service.record_host_transfer(meeting_id, new_host_id)
    except Exception:
        logger.exception("host_transfer_analytics_failed meeting_id=%s", meeting_id)