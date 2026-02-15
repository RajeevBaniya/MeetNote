import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import rate_limit_general
from app.db.session import get_session
from app.modules.auth.deps import get_current_user_id
from app.modules.meetings.schemas import MeetingAnalyticsOut
from app.modules.meetings.service import get_meeting_by_id, STREAM_CALL_TYPE
from app.modules.chat.service import get_recent_messages
from app.state.client import get_redis
from app.modules.stream_tokens.service import list_stream_recordings


logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{meeting_id}/analytics", response_model=MeetingAnalyticsOut)
async def get_meeting_analytics(
    meeting_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(rate_limit_general),
) -> MeetingAnalyticsOut:
    meeting = await get_meeting_by_id(session, meeting_id)
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found",
        )
    if meeting.host_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the host can view analytics for this meeting",
        )
    if meeting.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Analytics are available only after the meeting has ended",
        )
    if not meeting.ended_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Analytics are not available for this meeting yet",
        )
    try:
        redis = await get_redis()
    except Exception:
        redis = None
    chat_messages: list[dict] = []
    if redis is not None:
        try:
            chat_messages = await get_recent_messages(redis, meeting_id)
        except Exception:
            chat_messages = []
    duration_seconds: int | None = None
    if meeting.ended_at and meeting.ended_at >= meeting.created_at:
        duration_seconds = int((meeting.ended_at - meeting.created_at).total_seconds())
    chat_message_count = len(chat_messages)
    participant_ids: set[str] = set()
    for msg in chat_messages:
        uid = msg.get("user_id")
        if isinstance(uid, str) and uid.strip():
            participant_ids.add(uid.strip())
    participant_ids.add(str(meeting.host_id))
    participants_count = len(participant_ids)
    try:
        recordings = await list_stream_recordings(
            STREAM_CALL_TYPE,
            str(meeting_id),
            user_id,
        )
    except Exception:
        recordings = []
    recording_count = len(recordings)
    return MeetingAnalyticsOut(
        meeting_id=meeting_id,
        duration_seconds=duration_seconds,
        participants_count=participants_count,
        chat_message_count=chat_message_count,
        recording_count=recording_count,
    )

