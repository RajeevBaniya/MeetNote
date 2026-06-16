"""Meeting join/leave/host actions: end, remove-participant, mute-participant, leave."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import rate_limit_general
from app.db.session import get_session
from app.modules.auth.deps import get_current_user_id
from app.modules.meetings.schemas import EndMeetingOut, ParticipantActionIn
from app.modules.meetings.service import end_meeting, get_meeting_by_id
from app.modules.stream_tokens.constants import STREAM_CALL_TYPE
from app.modules.stream_tokens.service import (
    add_removed_user,
    kick_stream_user,
    mute_stream_user,
)
from app.state.client import get_redis
from app.modules.chat.websocket import close_chat_connections_for_user
from app.modules.transcripts.service import mark_user_left

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/{meeting_id}/end", response_model=EndMeetingOut)
async def post_end_meeting(
    meeting_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(rate_limit_general),
) -> EndMeetingOut:
    try:
        meeting = await end_meeting(session, meeting_id, user_id)
    except ValueError as exc:
        message = str(exc)
        lower = message.lower()
        if "not found" in lower:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Meeting not found",
            )
        if "host" in lower:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the host can end the meeting",
            )
        if "already ended" in lower:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Meeting is already ended",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        )
    return EndMeetingOut(
        status="ended",
        meeting_id=meeting_id,
        ended_at=meeting.ended_at,
        ended_by=user_id,
    )


@router.post("/{meeting_id}/remove-participant", status_code=status.HTTP_204_NO_CONTENT)
async def post_remove_participant(
    meeting_id: UUID,
    body: ParticipantActionIn,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(rate_limit_general),
) -> None:
    meeting = await get_meeting_by_id(session, meeting_id)
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found",
        )
    if not meeting.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Meeting is inactive",
        )
    if meeting.current_host_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the host can remove participants",
        )
    target_id = body.user_id
    if meeting.current_host_id == target_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Host cannot remove themselves this way",
        )
    try:
        redis = await get_redis()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable",
        )
    await add_removed_user(redis, meeting_id, target_id)
    try:
        await close_chat_connections_for_user(meeting_id, target_id)
    except Exception:
        logger.exception(
            "close_chat_connections_for_user_failed meeting_id=%s", meeting_id
        )
    try:
        await kick_stream_user(
            STREAM_CALL_TYPE,
            str(meeting_id),
            user_id,
            target_id,
        )
    except Exception:
        logger.exception("kick_stream_user_failed meeting_id=%s", meeting_id)


@router.post("/{meeting_id}/mute-participant", status_code=status.HTTP_204_NO_CONTENT)
async def post_mute_participant(
    meeting_id: UUID,
    body: ParticipantActionIn,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(rate_limit_general),
) -> None:
    meeting = await get_meeting_by_id(session, meeting_id)
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found",
        )
    if not meeting.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Meeting is inactive",
        )
    if meeting.current_host_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the host can mute participants",
        )
    target_id = body.user_id
    try:
        await mute_stream_user(
            STREAM_CALL_TYPE,
            str(meeting_id),
            user_id,
            target_id,
        )
    except Exception:
        logger.exception("mute_stream_user_failed meeting_id=%s", meeting_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to mute participant",
        )


@router.post("/{meeting_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
async def post_leave_meeting(
    meeting_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    _: None = Depends(rate_limit_general),
) -> None:
    try:
        redis = await get_redis()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable",
        )
    await mark_user_left(redis, meeting_id, user_id)
    return None
