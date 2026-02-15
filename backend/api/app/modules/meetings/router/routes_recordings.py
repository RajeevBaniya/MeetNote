import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import rate_limit_general
from app.db.session import get_session
from app.modules.auth.deps import get_current_user_id
from app.modules.meetings.schemas import RecordingActionOut, RecordingItemOut, RecordingsListOut
from app.modules.meetings.service import get_meeting_by_id, STREAM_CALL_TYPE
from app.modules.stream_tokens.service import (
    list_stream_recordings,
    start_stream_recording,
    stop_stream_recording,
)


logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/{meeting_id}/recording/start", response_model=RecordingActionOut)
async def post_start_recording(
    meeting_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(rate_limit_general),
) -> RecordingActionOut:
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
    if meeting.host_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the host can start recording",
        )
    try:
        await start_stream_recording(
            STREAM_CALL_TYPE,
            str(meeting_id),
            meeting.host_id,
        )
    except Exception:
        logger.exception("start_stream_recording_failed meeting_id=%s", meeting_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to start recording",
        )
    return RecordingActionOut(status="started")


@router.post("/{meeting_id}/recording/stop", response_model=RecordingActionOut)
async def post_stop_recording(
    meeting_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(rate_limit_general),
) -> RecordingActionOut:
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
    if meeting.host_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the host can stop recording",
        )
    try:
        await stop_stream_recording(
            STREAM_CALL_TYPE,
            str(meeting_id),
            meeting.host_id,
        )
    except Exception:
        logger.exception("stop_stream_recording_failed meeting_id=%s", meeting_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to stop recording",
        )
    return RecordingActionOut(status="stopped")


@router.get("/{meeting_id}/recordings", response_model=RecordingsListOut)
async def get_meeting_recordings(
    meeting_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(rate_limit_general),
) -> RecordingsListOut:
    meeting = await get_meeting_by_id(session, meeting_id)
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found",
        )
    if meeting.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Meeting has not ended",
        )
    try:
        raw = await list_stream_recordings(
            STREAM_CALL_TYPE,
            str(meeting_id),
            user_id,
        )
    except Exception:
        logger.exception("list_stream_recordings_failed meeting_id=%s", meeting_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to load recordings",
        )
    items = [RecordingItemOut(**record) for record in raw]
    return RecordingsListOut(recordings=items)

