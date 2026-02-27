import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Meeting
from app.db.session import async_session_factory
from app.modules.meetings.events import publish_meeting_ended
from app.modules.stream_tokens.service import (
    end_stream_call,
    query_stream_call_members,
)
from app.modules.meetings.service import STREAM_CALL_TYPE
from app.state.client import get_redis
from app.core.metrics import incr


logger = logging.getLogger(__name__)


async def reconcile_meeting_state(meeting_id: UUID, session: AsyncSession) -> None:
    should_mark_inactive = False
    should_force_end_stream = False
    member_count = 0

    # First snapshot: get Stream membership and a non-locking view of the meeting
    initial_meeting = None
    result = await session.execute(select(Meeting).where(Meeting.id == meeting_id))
    initial_meeting = result.scalar_one_or_none()
    if not initial_meeting:
        return

    members_first = await query_stream_call_members(
        call_type=STREAM_CALL_TYPE,
        call_id=str(meeting_id),
        acting_user_id=initial_meeting.original_host_id,
    )
    member_count = len(members_first)

    wants_mark_inactive = member_count == 0 and initial_meeting.is_active
    wants_force_end_stream = member_count > 0 and not initial_meeting.is_active

    # Second check: only if we plan a destructive action, re-query membership
    if wants_mark_inactive or wants_force_end_stream:
        members_second = await query_stream_call_members(
            call_type=STREAM_CALL_TYPE,
            call_id=str(meeting_id),
            acting_user_id=initial_meeting.original_host_id,
        )
        member_count = len(members_second)

    async with session.begin():
        result = await session.execute(
            select(Meeting).where(Meeting.id == meeting_id).with_for_update()
        )
        meeting = result.scalar_one_or_none()
        if not meeting:
            return

        now_utc = datetime.now(timezone.utc)

        if member_count == 0 and meeting.is_active:
            await session.execute(
                update(Meeting)
                .where(Meeting.id == meeting_id)
                .values(is_active=False, ended_at=now_utc)
            )
            should_mark_inactive = True
            logger.info(
                "meeting_auto_marked_inactive",
                extra={
                    "meeting_id": str(meeting_id),
                    "reason": "no_stream_members",
                },
            )
        elif member_count > 0 and not meeting.is_active:
            should_force_end_stream = True
            logger.info(
                "stream_call_force_ended",
                extra={
                    "meeting_id": str(meeting_id),
                    "member_count": member_count,
                },
            )

    if should_mark_inactive:
        try:
            await publish_meeting_ended(meeting_id)
        except Exception as exc:
            logger.warning(
                "publish_meeting_ended_failed",
                extra={"meeting_id": str(meeting_id)},
                exc_info=exc,
            )

    if should_force_end_stream:
        try:
            await end_stream_call(
                STREAM_CALL_TYPE,
                str(meeting_id),
                meeting.original_host_id,  # type: ignore[name-defined]
            )
        except Exception as exc:
            logger.warning(
                "stream_call_force_end_failed",
                extra={"meeting_id": str(meeting_id)},
                exc_info=exc,
            )

    logger.info(
        "meeting_reconciled",
        extra={
            "meeting_id": str(meeting_id),
            "member_count": member_count,
        },
    )
    incr("reconciliation_runs_total")


async def reconcile_meeting_state_with_guard(meeting_id: UUID) -> None:
    try:
        redis = await get_redis()
    except Exception as exc:
        logger.warning(
            "meeting_reconcile_redis_unavailable",
            extra={"meeting_id": str(meeting_id)},
            exc_info=exc,
        )
        return

    lock_key = f"meeting_reconcile_lock:{meeting_id}"
    got_lock = await redis.set(lock_key, "1", ex=3, nx=True)
    if not got_lock:
        return

    async with async_session_factory() as session:
        try:
            await reconcile_meeting_state(meeting_id, session)
        except Exception as exc:
            logger.error(
                "meeting_reconcile_failed",
                extra={"meeting_id": str(meeting_id)},
                exc_info=exc,
            )
