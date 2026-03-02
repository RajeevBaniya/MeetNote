import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import rate_limit_general
from app.db.session import get_session
from app.modules.auth.deps import get_current_user_id
from app.modules.meetings.schemas import (
    CreateMeetingIn,
    EndMeetingOut,
    MeetingOut,
    MeetingListItemOut,
    MyMeetingsOut,
    ParticipantActionIn,
    CheckRemovedOut,
    MeetingParticipantsOut,
    MeetingStatusOut,
)
from app.modules.meetings.service import (
    create_meeting,
    end_meeting,
    get_meeting_by_id,
    get_meetings_for_host,
)
from app.modules.stream_tokens.constants import STREAM_CALL_TYPE
from app.modules.stream_tokens.service import (
    add_removed_user,
    is_user_removed,
    kick_stream_user,
    mute_stream_user,
    query_stream_call_members,
)
from app.state.client import get_redis
from app.modules.chat.websocket import close_chat_connections_for_user


logger = logging.getLogger(__name__)

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


@router.get("/mine", response_model=MyMeetingsOut)
async def get_my_meetings(
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(rate_limit_general),
):
    active, ended = await get_meetings_for_host(session, user_id, ended_limit=20)
    now_utc = datetime.now(timezone.utc)
    upcoming_items: list[MeetingListItemOut] = []
    active_items: list[MeetingListItemOut] = []
    for meeting in active:
        item = MeetingListItemOut(
            id=meeting.id,
            title=meeting.title,
            is_active=meeting.is_active,
            created_at=meeting.created_at,
            scheduled_start_at=meeting.scheduled_start_at,
        )
        if meeting.scheduled_start_at and meeting.scheduled_start_at > now_utc:
            upcoming_items.append(item)
        else:
            active_items.append(item)
    ended_items = [
        MeetingListItemOut(
            id=meeting.id,
            title=meeting.title,
            is_active=meeting.is_active,
            created_at=meeting.created_at,
            scheduled_start_at=meeting.scheduled_start_at,
        )
        for meeting in ended
    ]
    upcoming_items.sort(key=lambda item: item.scheduled_start_at or item.created_at)
    return MyMeetingsOut(upcoming=upcoming_items, active=active_items, ended=ended_items)


@router.get("/{meeting_id}", response_model=MeetingOut)
async def get_meeting(
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
    return meeting


@router.get("/{meeting_id}/status", response_model=MeetingStatusOut)
async def get_meeting_status(
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
    return MeetingStatusOut(is_active=meeting.is_active, host_joined=meeting.host_joined)


@router.post("/{meeting_id}/end", response_model=EndMeetingOut)
async def post_end_meeting(
    meeting_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(rate_limit_general),
):
    try:
        meeting = await end_meeting(session, meeting_id, user_id)
    except ValueError as exc:
        message = str(exc)
        lower = message.lower()
        if "not found" in lower:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Meeting not found",
            )
        if "host" in lower:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the host can end the meeting",
            )
        if "already ended" in lower:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Meeting is already ended",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        )
    return EndMeetingOut(
        status="ended",
        meeting_id=meeting_id,
        ended_at=meeting.ended_at,
        ended_by=user_id,
    )


@router.get("/{meeting_id}/participants", response_model=MeetingParticipantsOut)
async def get_meeting_participants(
    meeting_id: UUID,
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
    items: list[dict] = []
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


@router.post("/{meeting_id}/remove-participant", status_code=status.HTTP_204_NO_CONTENT)
async def post_remove_participant(
    meeting_id: UUID,
    body: ParticipantActionIn,
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
            detail="Meeting is inactive",
        )
    if meeting.current_host_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the host can remove participants",
        )
    target_id = body.user_id
    if meeting.current_host_id == target_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Host cannot remove themselves this way",
        )
    try:
        redis = await get_redis()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable",
        )
    await add_removed_user(redis, meeting_id, target_id)
    try:
        await close_chat_connections_for_user(meeting_id, target_id)
    except Exception:
        logger.exception("close_chat_connections_for_user_failed meeting_id=%s", meeting_id)
    try:
        await kick_stream_user(
            STREAM_CALL_TYPE,
            str(meeting_id),
            user_id,
            target_id,
        )
    except Exception:
        logger.exception("kick_stream_user_failed meeting_id=%s", meeting_id)


@router.post("/{meeting_id}/mute-participant", status_code=status.HTTP_204_NO_CONTENT)
async def post_mute_participant(
    meeting_id: UUID,
    body: ParticipantActionIn,
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
            detail="Meeting is inactive",
        )
    if meeting.current_host_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the host can mute participants",
        )
    target_id = body.user_id
    try:
        await mute_stream_user(
            STREAM_CALL_TYPE,
            str(meeting_id),
            user_id,
            target_id,
        )
    except Exception:
        logger.exception("mute_stream_user_failed meeting_id=%s", meeting_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to mute participant",
        )


@router.get("/{meeting_id}/check-removed", response_model=CheckRemovedOut)
async def get_check_removed(
    meeting_id: UUID,
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

