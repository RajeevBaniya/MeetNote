import logging
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import rate_limit_general
from app.db.session import get_session
from app.modules.auth.deps import get_current_user_id
from app.modules.meetings.schemas import AssistantPreferenceIn, AssistantPreferenceOut
from app.modules.meetings.service import get_meeting_by_id
from app.modules.meetings.events import publish_meeting_assistant_preference
from app.state.client import get_redis


logger = logging.getLogger(__name__)

router = APIRouter()

ASSISTANT_ENABLED_KEY_PREFIX = "assistant_enabled:"


@router.get("/{meeting_id}/assistant-preference", response_model=AssistantPreferenceOut)
async def get_assistant_preference(
    meeting_id: UUID,
    _user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(rate_limit_general),
):
    meeting = await get_meeting_by_id(session, meeting_id)
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found",
        )
    try:
        redis = await get_redis()
        raw = await redis.get(f"{ASSISTANT_ENABLED_KEY_PREFIX}{meeting_id}")
    except Exception:
        raw = None
    enabled = raw != "0"
    return AssistantPreferenceOut(enabled=enabled)


@router.put("/{meeting_id}/assistant-preference", response_model=AssistantPreferenceOut)
async def put_assistant_preference(
    meeting_id: UUID,
    body: AssistantPreferenceIn,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(rate_limit_general),
):
    meeting = await get_meeting_by_id(session, meeting_id)
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found",
        )
    if not meeting.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Meeting is not active",
        )
    if meeting.current_host_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the host can change assistant preference",
        )
    try:
        redis = await get_redis()
        value = "1" if body.enabled else "0"
        await redis.set(f"{ASSISTANT_ENABLED_KEY_PREFIX}{meeting_id}", value)
    except Exception as exc:
        logger.warning("Failed to set assistant preference", exc_info=exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable",
        )
    await publish_meeting_assistant_preference(meeting_id, body.enabled)
    return AssistantPreferenceOut(enabled=body.enabled)

