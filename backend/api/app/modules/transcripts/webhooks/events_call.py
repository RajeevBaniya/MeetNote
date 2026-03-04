import asyncio
import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict
from uuid import UUID

from fastapi import Request

from app.core.metrics import incr
from app.modules.analytics.service import (
    record_participant_join,
    record_participant_leave,
)
from app.modules.chat.websocket import broadcast_host_changed
from app.modules.meetings.service import transfer_host_if_current_disconnected
from app.modules.transcripts.webhooks.utils import parse_meeting_id
from app.state.client import get_redis

logger = logging.getLogger(__name__)


async def handle_call_event(
    body: Dict[str, Any],
    request: Request,
    start_time: datetime,
) -> Dict[str, bool]:
    event_type = body.get("type")
    call_cid = str(body.get("call_cid") or "")
    meeting_id = parse_meeting_id(call_cid)
    if meeting_id is None:
        incr("webhook_processed_total")
        return {"accepted": True}

    disconnected_user_id: UUID | None = None
    joined_user_id: UUID | None = None
    should_trigger = False
    now_utc = datetime.now(timezone.utc)

    event_id = (
        request.headers.get("X-WEBHOOK-ID")
        or body.get("id")
        or body.get("event_id")
        or hashlib.sha256(
            json.dumps(
                {
                    "type": event_type,
                    "call_cid": call_cid,
                    "created_at": body.get("created_at"),
                    "member": body.get("member"),
                },
                sort_keys=True,
            ).encode()
        ).hexdigest()
    )
    event_id_str = str(event_id) if event_id else ""

    async def _record_join_if_new(uid_str: str) -> None:
        if not event_id_str:
            return
        try:
            redis_client = await get_redis()
        except Exception:
            return
        key = f"analytics_event_seen:{meeting_id}:{event_id_str}"
        if not await redis_client.set(key, "1", ex=3600, nx=True):
            return
        try:
            uid = UUID(uid_str)
            await record_participant_join(meeting_id, uid, now_utc)
        except ValueError:
            return

    async def _record_leave_if_new(uid: UUID) -> None:
        if not event_id_str:
            return
        try:
            redis_client = await get_redis()
        except Exception:
            return
        key = f"analytics_event_seen:{meeting_id}:{event_id_str}"
        if not await redis_client.set(key, "1", ex=3600, nx=True):
            return
        await record_participant_leave(meeting_id, uid, now_utc)

    if event_type == "call.member_added":
        member = body.get("member") or {}
        user = member.get("user") or {}
        raw_user_id = user.get("id") or member.get("user_id")
        if isinstance(raw_user_id, str):
            asyncio.create_task(_record_join_if_new(raw_user_id))
        incr("webhook_processed_total")
        return {"accepted": True}

    if event_type == "call.session_participant_joined":
        member = body.get("member") or body.get("participant") or {}
        user = member.get("user") or {}
        raw_user_id = user.get("id") or member.get("user_id")
        if isinstance(raw_user_id, str):
            asyncio.create_task(_record_join_if_new(raw_user_id))
        incr("webhook_processed_total")
        return {"accepted": True}

    if event_type == "call.session_participant_left":
        member = body.get("member") or body.get("participant") or {}
        user = member.get("user") or {}
        raw_user_id = user.get("id") or member.get("user_id")
        if isinstance(raw_user_id, str):
            try:
                left_user_id = UUID(raw_user_id)
                asyncio.create_task(_record_leave_if_new(left_user_id))
            except ValueError:
                return {"accepted": True}
        incr("webhook_processed_total")
        return {"accepted": True}

    if event_type == "call.member_removed":
        member = body.get("member") or {}
        user = member.get("user") or {}
        raw_user_id = user.get("id") or member.get("user_id")
        if isinstance(raw_user_id, str):
            try:
                disconnected_user_id = UUID(raw_user_id)
                asyncio.create_task(_record_leave_if_new(disconnected_user_id))
            except ValueError:
                disconnected_user_id = None
        should_trigger = True
    elif event_type == "call.member_updated":
        member = body.get("member") or {}
        removed_flags = [
            member.get("removed"),
            member.get("deleted"),
            member.get("is_removed"),
        ]
        removed_flag = any(bool(flag) for flag in removed_flags)
        status = str(member.get("status") or "").strip().lower()
        inactive_status = status in {"left", "removed", "blocked"}
        if removed_flag or inactive_status:
            user = member.get("user") or {}
            raw_user_id = user.get("id") or member.get("user_id")
            if isinstance(raw_user_id, str):
                try:
                    disconnected_user_id = UUID(raw_user_id)
                    asyncio.create_task(_record_leave_if_new(disconnected_user_id))
                    should_trigger = True
                except ValueError:
                    disconnected_user_id = None
    elif event_type == "call.session_ended":
        should_trigger = True

    if not should_trigger:
        incr("webhook_processed_total")
        return {"accepted": True}

    try:
        redis = await get_redis()
    except Exception:
        return {"accepted": True}

    lock_key = f"host_transfer_lock:{meeting_id}"
    got_lock = await redis.set(lock_key, "1", ex=5, nx=True)
    if not got_lock:
        incr("webhook_processed_total")
        return {"accepted": True}

    async def _debounced_transfer() -> None:
        await asyncio.sleep(3)
        try:
            new_host = await transfer_host_if_current_disconnected(
                meeting_id,
                disconnected_user_id,
            )
        except Exception:
            return
        if new_host is None:
            return
        await broadcast_host_changed(meeting_id, new_host)

    asyncio.create_task(_debounced_transfer())

    processing_ms = int(
        (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
    )
    logger.info(
        "webhook_processed",
        extra={
            "meeting_id": str(meeting_id),
            "event_type": event_type,
            "processing_time_ms": processing_ms,
        },
    )
    if processing_ms > 2000:
        logger.warning(
            "webhook_slow",
            extra={
                "meeting_id": str(meeting_id),
                "event_type": event_type,
                "processing_time_ms": processing_ms,
            },
        )
    incr("webhook_processed_total")
    return {"accepted": True}

