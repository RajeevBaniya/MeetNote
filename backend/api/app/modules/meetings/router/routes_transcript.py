import logging
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import rate_limit_general
from app.db.session import get_session
from app.modules.auth.deps import get_current_user_id
from app.modules.meetings.schemas import TranscriptOut
from app.modules.meetings.service import get_meeting_by_id
from app.modules.stream_tokens.constants import STREAM_CALL_TYPE
from app.modules.stream_tokens.service import get_stream_transcript_segments
from app.state.client import get_redis
from app.modules.transcripts.service import (
    append_transcript_segment,
    generate_final_summary,
    get_live_transcript,
)


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


@router.post("/{meeting_id}/transcript/segment", status_code=status.HTTP_202_ACCEPTED)
async def ingest_transcript_segment(
    meeting_id: UUID,
    body: dict = Body(...),
    _user_id: UUID = Depends(get_current_user_id),
    _: None = Depends(rate_limit_general),
):
    text = ""
    if isinstance(body, dict):
        raw = body.get("text")
        if isinstance(raw, str):
            text = raw
    if not text or not text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="text is required",
        )
    try:
        redis = await get_redis()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable",
        )
    await append_transcript_segment(redis, meeting_id, text)
    return {"accepted": True}


@router.get("/{meeting_id}/live-transcript", response_model=TranscriptOut)
async def get_live_transcript_api(
    meeting_id: UUID,
    _user_id: UUID = Depends(get_current_user_id),
    _: None = Depends(rate_limit_general),
):
    try:
        redis = await get_redis()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable",
        )
    items = await get_live_transcript(redis, meeting_id)
    segments = [{"type": "speech", "text": item, "speaker_id": None} for item in items]
    return TranscriptOut(segments=segments)


@router.post("/{meeting_id}/generate-final-summary")
async def post_generate_final_summary(
    meeting_id: UUID,
    _user_id: UUID = Depends(get_current_user_id),
    _: None = Depends(rate_limit_general),
):
    try:
        redis = await get_redis()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable",
        )
    try:
        summary = await generate_final_summary(redis, meeting_id)
    except Exception:
        logger.exception("generate_final_summary_failed meeting_id=%s", meeting_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to generate final summary",
        )
    return {"summary": summary or ""}

