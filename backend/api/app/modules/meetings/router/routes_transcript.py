import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import rate_limit_general
from app.db.session import get_session
from app.modules.auth.deps import get_current_user_id
from app.modules.meetings.schemas import TranscriptOut
from app.modules.meetings.service import get_meeting_by_id, STREAM_CALL_TYPE
from app.modules.stream_tokens.service import get_stream_transcript_segments


logger = logging.getLogger(__name__)

router = APIRouter()

ASSISTANT_SPEAKER_IDS = {"system:assistant", "meeting-assistant-bot", "Assistant"}


@router.get("/{meeting_id}/transcript", response_model=TranscriptOut)
async def get_meeting_transcript(
    meeting_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(rate_limit_general),
) -> TranscriptOut:
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
        raw_segments = await get_stream_transcript_segments(
            STREAM_CALL_TYPE,
            str(meeting_id),
            user_id,
        )
    except Exception:
        logger.exception("get_stream_transcript_segments_failed meeting_id=%s", meeting_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to load transcript",
        )
    segments = [
        segment
        for segment in raw_segments
        if (segment.get("speaker_id") or "") not in ASSISTANT_SPEAKER_IDS
    ]
    return TranscriptOut(segments=segments)

