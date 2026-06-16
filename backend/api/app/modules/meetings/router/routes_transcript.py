import logging
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import rate_limit_general
from app.core.metrics import incr
from app.db.session import get_session
from app.modules.auth.deps import get_current_user_id
from app.modules.meetings.schemas import TranscriptOut, TranscriptSegmentOut
from app.modules.meetings.meeting_queries import user_was_meeting_member
from app.modules.meetings.service import get_meeting_by_id
from app.modules.stream_tokens.constants import STREAM_CALL_TYPE
from app.modules.stream_tokens.service import get_stream_transcript_segments
from app.state.client import get_redis
from app.modules.transcripts.summarization import ensure_summary_chunks_for_meeting_end
from app.modules.transcripts.summary_chunks_read import fetch_summary_chunk_summaries
from app.modules.transcripts.service import (
    append_transcript_segment,
    generate_final_summary,
    get_transcript_history_segments,
    get_transcript_segments,
    has_user_left,
    delete_transcript_state,
)


logger = logging.getLogger(__name__)

router = APIRouter()

ASSISTANT_SPEAKER_IDS = {"system:assistant", "meeting-assistant-bot", "Assistant"}


class TranscriptHistorySegmentOut(BaseModel):
    sequence: int
    speaker_id: str
    speaker_name: str
    text: str
    timestamp: str


class TranscriptHistoryOut(BaseModel):
    segments: list[TranscriptHistorySegmentOut]


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
    if not await user_was_meeting_member(session, meeting_id, user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this meeting transcript",
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
    chunk_summaries: list[str] = []
    try:
        redis = await get_redis()
        if redis:
            try:
                await ensure_summary_chunks_for_meeting_end(redis, meeting_id)
            except Exception:
                logger.debug(
                    "ensure_summary_chunks_lazy_failed meeting_id=%s",
                    meeting_id,
                    exc_info=True,
                )
            chunk_summaries = await fetch_summary_chunk_summaries(redis, meeting_id)
    except Exception:
        logger.debug(
            "summary_chunk_summaries_read_failed meeting_id=%s",
            meeting_id,
            exc_info=True,
        )
    segments_out = [TranscriptSegmentOut(**s) for s in segments]
    return TranscriptOut(segments=segments_out, chunk_summaries=chunk_summaries)


@router.post("/{meeting_id}/transcript/segment", status_code=status.HTTP_202_ACCEPTED)
async def ingest_transcript_segment(
    meeting_id: UUID,
    body: dict[str, Any] = Body(...),
    _user_id: UUID = Depends(get_current_user_id),
    _: None = Depends(rate_limit_general),
) -> dict[str, Any]:
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


async def _get_live_transcript_common(
    meeting_id: UUID,
    user_id: UUID,
) -> TranscriptOut:
    incr("transcript_restore_requests_total")
    try:
        redis = await get_redis()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable",
        )
    if await has_user_left(redis, meeting_id, user_id):
        incr("transcript_user_blocked_total")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="transcript_unavailable",
        )
    items = await get_transcript_segments(redis, meeting_id)
    segments = [
        {
            "type": "speech",
            "start_time": item.get("start_time", ""),
            "stop_time": item.get("end_time", ""),
            "speaker_id": item.get("speaker_id"),
            "text": item.get("text", ""),
        }
        for item in items
    ]
    segments_out = [TranscriptSegmentOut(**s) for s in segments]
    return TranscriptOut(segments=segments_out)


@router.get("/{meeting_id}/live-transcript", response_model=TranscriptOut)
async def get_live_transcript_api(
    meeting_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    _: None = Depends(rate_limit_general),
) -> TranscriptOut:
    return await _get_live_transcript_common(meeting_id, user_id)


@router.get("/{meeting_id}/transcript/live", response_model=TranscriptOut)
async def get_live_transcript_segments_api(
    meeting_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    _: None = Depends(rate_limit_general),
) -> TranscriptOut:
    return await _get_live_transcript_common(meeting_id, user_id)


@router.get("/{meeting_id}/transcript/history", response_model=TranscriptHistoryOut)
async def get_transcript_history_api(
    meeting_id: UUID,
    limit: int = Query(default=200),
    user_id: UUID = Depends(get_current_user_id),
    _: None = Depends(rate_limit_general),
) -> TranscriptHistoryOut:
    incr("transcript_restore_requests_total")
    try:
        segments = await get_transcript_history_segments(
            meeting_id,
            user_id=user_id,
            limit=limit,
        )
    except PermissionError:
        incr("transcript_user_blocked_total")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="transcript_unavailable",
        )
    except Exception:
        logger.exception("get_transcript_history_failed meeting_id=%s", meeting_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to load transcript history",
        )
    segments_out = []
    for s in segments:
        seq = s.get("sequence")
        spk_id = s.get("speaker_id")
        spk_name = s.get("speaker_name")
        txt = s.get("text")
        ts = s.get("timestamp")
        
        segments_out.append(
            TranscriptHistorySegmentOut(
                sequence=seq if isinstance(seq, int) else 0,
                speaker_id=spk_id if isinstance(spk_id, str) else "",
                speaker_name=spk_name if isinstance(spk_name, str) else "",
                text=txt if isinstance(txt, str) else "",
                timestamp=ts if isinstance(ts, str) else "",
            )
        )
    return TranscriptHistoryOut(segments=segments_out)


@router.post("/{meeting_id}/generate-final-summary")
async def post_generate_final_summary(
    meeting_id: UUID,
    _user_id: UUID = Depends(get_current_user_id),
    _: None = Depends(rate_limit_general),
) -> dict[str, Any]:
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


@router.post("/{meeting_id}/transcript/cleanup", status_code=status.HTTP_204_NO_CONTENT)
async def post_transcript_cleanup(
    meeting_id: UUID,
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
    if meeting.host_id != user_id and meeting.original_host_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden",
        )
    try:
        redis = await get_redis()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable",
        )
    await delete_transcript_state(redis, meeting_id)
    incr("transcript_cleanup_total")
    return None

