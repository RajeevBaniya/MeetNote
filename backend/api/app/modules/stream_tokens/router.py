import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import rate_limit_stream_token
from app.db.session import get_session
from app.modules.auth.deps import get_current_user_id
from app.modules.meetings.service import get_meeting_by_id, ensure_host_started
from app.modules.stream_tokens.schemas import StreamTokenIn, StreamTokenOut
from app.modules.stream_tokens.service import (
    STREAM_TOKEN_EXPIRY_SECONDS,
    create_stream_token,
    is_user_removed,
)
from app.state.client import get_redis

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/meetings", tags=["stream-tokens"])


@router.post("/{meeting_id}/stream-token", response_model=StreamTokenOut)
async def stream_token(
    meeting_id: UUID,
    body: StreamTokenIn | None = Body(None),
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(rate_limit_stream_token),
) -> StreamTokenOut:
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
    if meeting.scheduled_start_at:
        now_utc = datetime.now(timezone.utc)
        delta_seconds = (meeting.scheduled_start_at - now_utc).total_seconds()
        if delta_seconds > 60:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This meeting is scheduled and has not started yet.",
            )
    is_host = meeting.host_id == user_id
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
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You were removed from this meeting",
        )
    if not is_host:
        raw_passcode = ""
        if body and isinstance(body.passcode, str):
            raw_passcode = body.passcode.strip()
        if not raw_passcode:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Passcode required",
            )
        if meeting.passcode != raw_passcode:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Incorrect passcode",
            )
        try:
            ensure_host_started(meeting, user_id)
        except ValueError as exc:
            if str(exc) == "HOST_NOT_STARTED":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Host has not started the meeting yet",
                ) from exc
            raise
    display_name = None
    if body and body.display_name and isinstance(body.display_name, str):
        display_name = body.display_name.strip() or None
    if is_host and not meeting.host_joined:
        meeting.host_joined = True
        await session.commit()
    token = create_stream_token(user_id, name=display_name)
    return StreamTokenOut(
        token=token,
        user_id=str(user_id),
        expires_in_seconds=STREAM_TOKEN_EXPIRY_SECONDS,
    )
