import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_service
from app.core.interfaces import (
    AnalyticsServiceInterface,
    CacheServiceInterface,
    ChatServiceInterface,
    EventServiceInterface,
    StreamServiceInterface,
    TranscriptServiceInterface,
)
from app.db.models import Meeting
from app.modules.meetings.meeting_queries import get_meeting_by_id
from app.modules.stream_tokens.constants import STREAM_CALL_TYPE

logger = logging.getLogger(__name__)


async def end_meeting(
    session: AsyncSession,
    meeting_id: UUID,
    requester_id: UUID,
) -> Meeting:
    """
    End an active meeting and execute all cleanup side effects.
    
    Args:
        session: Database session
        meeting_id: UUID of meeting to end
        requester_id: UUID of user requesting to end meeting
        
    Returns:
        Updated meeting instance
        
    Raises:
        ValueError: If meeting not found, already ended, or requester not host
    """
    # Validate meeting and permissions
    meeting = await get_meeting_by_id(session, meeting_id)
    if not meeting:
        raise ValueError("Meeting not found")
    if meeting.current_host_id != requester_id:
        raise ValueError("Only the host can end the meeting")
    if not meeting.is_active:
        raise ValueError("Meeting is already ended")

    # Update meeting status in database
    now = datetime.now(timezone.utc)
    await session.execute(
        update(Meeting)
        .where(Meeting.id == meeting_id)
        .values(
            is_active=False,
            ended_at=now,
            convergence_started_at=now,
            convergence_state="pending",
            analytics_state="pending",
        )
    )
    await session.commit()
    await session.refresh(meeting)

    # Execute cleanup side effects after successful commit
    await _execute_meeting_cleanup_tasks(meeting_id, now, requester_id, meeting.host_joined)

    # Mark as converged since all cleanup tasks succeeded
    await session.execute(
        update(Meeting)
        .where(Meeting.id == meeting_id)
        .values(
            convergence_state="converged",
            convergence_completed_at=datetime.now(timezone.utc),
        )
    )
    await session.commit()

    return meeting


async def _execute_meeting_cleanup_tasks(
    meeting_id: UUID, 
    ended_at: datetime, 
    requester_id: UUID,
    host_joined: bool = False
) -> None:
    """
    Execute all cleanup tasks after meeting ends.
    Each task is isolated with error handling to prevent cascading failures.
    Any captured failures are raised at the end to allow task retry.
    """
    # Get service instances
    analytics_service = get_service(AnalyticsServiceInterface)  # type: ignore[type-abstract]
    stream_service = get_service(StreamServiceInterface)  # type: ignore[type-abstract]
    event_service = get_service(EventServiceInterface)  # type: ignore[type-abstract]
    chat_service = get_service(ChatServiceInterface)  # type: ignore[type-abstract]
    cache_service = get_service(CacheServiceInterface)  # type: ignore[type-abstract]
    transcript_service = get_service(TranscriptServiceInterface)  # type: ignore[type-abstract]

    errors = []

    # Finalize analytics data
    try:
        await analytics_service.finalize_meeting_analytics(meeting_id, ended_at)
    except Exception as exc:
        logger.exception("finalize_analytics_failed meeting_id=%s", meeting_id)
        errors.append(exc)

    # End Stream video call if the host joined
    if host_joined:
        try:
            await stream_service.end_call(STREAM_CALL_TYPE, str(meeting_id), requester_id)
        except Exception as exc:
            logger.exception("end_stream_call_failed meeting_id=%s", meeting_id)
            errors.append(exc)
    else:
        logger.info("skip_end_stream_call_host_never_joined meeting_id=%s", meeting_id)

    # Notify other systems of meeting end
    try:
        await event_service.publish_meeting_ended(meeting_id)
    except Exception as exc:
        logger.exception("publish_meeting_ended_failed meeting_id=%s", meeting_id)
        errors.append(exc)

    # Close chat WebSocket connections
    try:
        await chat_service.close_meeting_connections(meeting_id)
    except Exception as exc:
        logger.exception("close_chat_connections_failed meeting_id=%s", meeting_id)
        errors.append(exc)

    # Clean up cache keys and transcript data
    try:
        await transcript_service.expire_meeting_keys(cache_service, meeting_id)
        await cache_service.delete_keys(
            f"assistant_enabled:{meeting_id}", 
            f"meeting:{meeting_id}:removed_users",
            f"meeting:host_id:{meeting_id}",
            f"assistant:pending_q:{meeting_id}",
            f"assistant:ext_approved:{meeting_id}"
        )
    except Exception as exc:
        logger.exception("cache_cleanup_failed meeting_id=%s", meeting_id)
        errors.append(exc)

    if errors:
        raise RuntimeError("; ".join(str(e) for e in errors))