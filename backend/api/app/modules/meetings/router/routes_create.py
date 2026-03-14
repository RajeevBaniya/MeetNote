"""Meeting creation route: POST /."""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import rate_limit_general
from app.db.session import get_session
from app.modules.auth.deps import get_current_user_id
from app.modules.meetings.schemas import CreateMeetingIn, MeetingOut
from app.modules.meetings.service import create_meeting

router = APIRouter()


@router.post("/", response_model=MeetingOut, status_code=status.HTTP_201_CREATED)
async def post_meeting(
    body: CreateMeetingIn | None = Body(None),
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(rate_limit_general),
):
    title = (body.title if body else None) or ""
    scheduled_start_at = None
    if body and body.scheduled_start_at is not None:
        if body.scheduled_start_at.tzinfo is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="scheduled_start_at must include timezone and be in UTC.",
            )
        scheduled_start_at = body.scheduled_start_at.astimezone(timezone.utc)
        now_utc = datetime.now(timezone.utc)
        if scheduled_start_at <= now_utc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="scheduled_start_at must be in the future.",
            )
    meeting = await create_meeting(
        session=session,
        host_id=user_id,
        title=title or None,
        scheduled_start_at=scheduled_start_at,
        scheduled_end_at=None,
    )
    return meeting
