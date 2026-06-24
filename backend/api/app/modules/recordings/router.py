import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import rate_limit_general
from app.db.session import get_session
from app.modules.auth.deps import get_current_user_id
from app.modules.meetings.meeting_queries import (
    get_meeting_by_id,
    user_was_meeting_member,
)
from app.modules.recordings.schemas import (
    RecordingsListOut,
    RecordingStartOut,
    RecordingStopIn,
)
from app.modules.recordings.service import (
    create_recording_start,
    finalize_recording,
    list_recordings_for_meeting,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/meetings", tags=["recordings"])


@router.post("/{meeting_id}/recording/start", response_model=RecordingStartOut)
async def start_recording(
    meeting_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(rate_limit_general),
) -> RecordingStartOut:
    meeting = await get_meeting_by_id(session, meeting_id)
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")
    if meeting.current_host_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    recording_id, started_at = await create_recording_start(session, meeting_id)
    return RecordingStartOut(recording_id=str(recording_id), started_at=started_at)


@router.post("/{meeting_id}/recording/stop", status_code=status.HTTP_204_NO_CONTENT)
async def stop_recording(
    meeting_id: UUID,
    payload: RecordingStopIn,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(rate_limit_general),
) -> None:
    meeting = await get_meeting_by_id(session, meeting_id)
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")
    if meeting.current_host_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    ok = await finalize_recording(
        session=session,
        meeting_id=meeting_id,
        recording_id=payload.recording_id,
        file_name=payload.file_name,
        duration_seconds=payload.duration_seconds,
        started_at=payload.started_at,
        ended_at=payload.ended_at,
    )
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recording not found")
    return None


@router.get("/{meeting_id}/recordings", response_model=RecordingsListOut)
async def get_recordings(
    meeting_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(rate_limit_general),
) -> dict[str, Any]:
    allowed = await user_was_meeting_member(session, meeting_id, user_id)
    if not allowed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")
    rows = await list_recordings_for_meeting(session, meeting_id)
    return {"recordings": rows}

