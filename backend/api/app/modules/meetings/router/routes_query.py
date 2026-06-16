"""Meeting query routes: GET /mine, /{id}, /{id}/status, /{id}/participants, /{id}/check-removed."""

from typing import Any
from uuid import UUID

from app.db.models import Meeting
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import rate_limit_general
from app.db.session import get_session
from app.modules.auth.deps import get_current_user_id
from app.modules.meetings.schemas import (
    CheckRemovedOut,
    MeetingListItemOut,
    MeetingMyItemOut,
    MeetingOut,
    MeetingParticipantsOut,
    MeetingStatusOut,
    MyMeetingsOut,
)
from app.modules.meetings.service import (
    get_meeting_by_id,
    get_my_meetings_dashboard_data,
    list_meetings_for_user_host_or_participant,
)
from app.modules.stream_tokens.constants import STREAM_CALL_TYPE
from app.modules.stream_tokens.service import (
    is_user_removed,
    query_stream_call_members,
)
from app.state.client import get_redis

router = APIRouter()


@router.get("/mine", response_model=MyMeetingsOut)
async def get_my_meetings(
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(rate_limit_general),
) -> MyMeetingsOut:
    data = await get_my_meetings_dashboard_data(session, user_id, ended_limit=20)
    upcoming_items = [
        MeetingListItemOut(
            id=m.id,
            title=m.title,
            is_active=m.is_active,
            created_at=m.created_at,
            scheduled_start_at=m.scheduled_start_at,
        )
        for m in data["upcoming"]
    ]
    active_items = [
        MeetingListItemOut(
            id=m.id,
            title=m.title,
            is_active=m.is_active,
            created_at=m.created_at,
            scheduled_start_at=m.scheduled_start_at,
        )
        for m in data["active"]
    ]
    ended_items = [
        MeetingListItemOut(
            id=m.id,
            title=m.title,
            is_active=m.is_active,
            created_at=m.created_at,
            scheduled_start_at=m.scheduled_start_at,
        )
        for m in data["ended"]
    ]
    return MyMeetingsOut(upcoming=upcoming_items, active=active_items, ended=ended_items)


@router.get("/my", response_model=list[MeetingMyItemOut])
async def list_my_meetings_host_or_participant(
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(rate_limit_general),
) -> list[MeetingMyItemOut]:
    rows = await list_meetings_for_user_host_or_participant(session, user_id)
    return [
        MeetingMyItemOut(
            id=m.id,
            title=m.title,
            created_at=m.created_at,
            ended_at=m.ended_at,
            is_active=m.is_active,
            participant_count=count,
            has_summary=False,
            scheduled_start_at=m.scheduled_start_at,
        )
        for m, count in rows
    ]


@router.get("/{meeting_id}", response_model=MeetingOut)
async def get_meeting(
    meeting_id: UUID,
    _user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(rate_limit_general),
) -> Meeting:
    meeting = await get_meeting_by_id(session, meeting_id)
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found",
        )
    return meeting


@router.get("/{meeting_id}/status", response_model=MeetingStatusOut)
async def get_meeting_status(
    meeting_id: UUID,
    _user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(rate_limit_general),
) -> MeetingStatusOut:
    meeting = await get_meeting_by_id(session, meeting_id)
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found",
        )
    return MeetingStatusOut(is_active=meeting.is_active, host_joined=meeting.host_joined)


@router.get("/{meeting_id}/participants", response_model=MeetingParticipantsOut)
async def get_meeting_participants(
    meeting_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(rate_limit_general),
) -> dict[str, Any]:
    meeting = await get_meeting_by_id(session, meeting_id)
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found",
        )
    try:
        members = await query_stream_call_members(
            STREAM_CALL_TYPE,
            str(meeting_id),
            user_id,
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable",
        )
    items: list[dict[str, Any]] = []
    for m in members:
        uid = m.get("user_id")
        if not isinstance(uid, str):
            continue
        try:
            user_uuid = UUID(uid)
        except Exception:
            continue
        is_host = user_uuid == meeting.current_host_id
        name = m.get("name") if isinstance(m.get("name"), str) else ""
        joined_at = m.get("joined_at") if isinstance(m.get("joined_at"), str) else ""
        items.append(
            {
                "user_id": user_uuid,
                "name": name,
                "joined_at": joined_at,
                "is_current_host": is_host,
            }
        )
    return {"participants": items}


@router.get("/{meeting_id}/check-removed", response_model=CheckRemovedOut)
async def get_check_removed(
    meeting_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(rate_limit_general),
) -> CheckRemovedOut:
    meeting = await get_meeting_by_id(session, meeting_id)
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found",
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
    return CheckRemovedOut(removed=removed)
