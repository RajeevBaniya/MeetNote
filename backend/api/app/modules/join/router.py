import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import rate_limit_meeting_join
from app.db.session import get_session
from app.modules.auth.deps import get_current_user_id
from app.modules.join.schemas import JoinMeetingIn, JoinMeetingOut
from app.modules.meetings.service import get_meeting_by_id, get_meeting_by_join_code
from app.modules.stream_tokens.service import is_user_removed
from app.state.client import get_redis

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/meetings", tags=["join"])


@router.post("/join", response_model=JoinMeetingOut)
async def join_meeting(
    body: JoinMeetingIn,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(rate_limit_meeting_join),
):
    if not body.join_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="join_code is required",
        )
    cleaned_code = body.join_code.strip().replace(" ", "").replace("-", "")
    if not cleaned_code.isdigit() or len(cleaned_code) != 12:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid join code format. Must be 12 digits.",
        )
    meeting = await get_meeting_by_join_code(session, cleaned_code)
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found",
        )
    meeting_id = meeting.id
    if meeting.scheduled_start_at:
        now_utc = datetime.now(timezone.utc)
        delta_seconds = (meeting.scheduled_start_at - now_utc).total_seconds()
        if delta_seconds > 60:
            logger.info(
                "join_rejected",
                extra={"reason": "not_started", "meeting_id": str(meeting_id)},
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This meeting is scheduled and has not started yet.",
            )
    if not meeting.is_active:
        logger.info(
            "join_rejected",
            extra={"reason": "inactive_meeting", "meeting_id": str(meeting_id)},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Meeting is inactive",
        )
    is_host = meeting.host_id == user_id
    if not is_host:
        raw_passcode = (body.passcode or "").strip() if body and body.passcode else ""
        if not raw_passcode:
            logger.info(
                "join_rejected",
                extra={"reason": "missing_passcode", "meeting_id": str(meeting_id)},
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Passcode required",
            )
        if meeting.passcode != raw_passcode:
            logger.info(
                "join_rejected",
                extra={"reason": "invalid_passcode", "meeting_id": str(meeting_id)},
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Incorrect passcode",
            )
    try:
        redis = await get_redis()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable",
        )
    try:
        removed = await is_user_removed(redis, meeting_id, user_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable",
        )
    if removed:
        logger.info(
            "join_rejected",
            extra={"reason": "removed_from_meeting", "meeting_id": str(meeting_id)},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You were removed from this meeting",
        )
    return JoinMeetingOut(
        status="joined",
        meeting_id=meeting_id,
        user_id=user_id,
    )
