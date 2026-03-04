import asyncio
import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict
from uuid import UUID

from fastapi import Request

from app.core.metrics import incr
from app.modules.transcripts.webhooks.call_analytics import (
    record_join_if_new,
    record_leave_if_new,
)
from app.modules.transcripts.webhooks.call_host_transfer import (
    run_debounced_host_transfer,
)
from app.modules.transcripts.webhooks.utils import parse_meeting_id


def _event_id_str(body: Dict[str, Any], request: Request) -> str:
    event_type = body.get("type")
    call_cid = str(body.get("call_cid") or "")
    raw = (
        request.headers.get("X-WEBHOOK-ID")
        or body.get("id")
        or body.get("event_id")
    )
    if raw is not None:
        return str(raw)
    payload = {
        "type": event_type,
        "call_cid": call_cid,
        "created_at": body.get("created_at"),
        "member": body.get("member"),
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode()
    ).hexdigest()
    return digest


def _user_id_from_member(member: Dict[str, Any]) -> str | None:
    if not member:
        return None
    user = member.get("user") or {}
    raw = user.get("id") or member.get("user_id")
    return str(raw) if isinstance(raw, str) else None


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

    event_id_str = _event_id_str(body, request)
    now_utc = datetime.now(timezone.utc)
    disconnected_user_id: UUID | None = None
    should_trigger = False

    if event_type == "call.member_added":
        uid = _user_id_from_member(body.get("member") or {})
        if uid:
            asyncio.create_task(
                record_join_if_new(meeting_id, event_id_str, uid, now_utc)
            )
        incr("webhook_processed_total")
        return {"accepted": True}

    if event_type == "call.session_participant_joined":
        member = body.get("member") or body.get("participant") or {}
        uid = _user_id_from_member(member)
        if uid:
            asyncio.create_task(
                record_join_if_new(meeting_id, event_id_str, uid, now_utc)
            )
        incr("webhook_processed_total")
        return {"accepted": True}

    if event_type == "call.session_participant_left":
        member = body.get("member") or body.get("participant") or {}
        uid = _user_id_from_member(member)
        if uid:
            try:
                asyncio.create_task(
                    record_leave_if_new(
                        meeting_id, event_id_str, UUID(uid), now_utc
                    )
                )
            except ValueError:
                pass
        incr("webhook_processed_total")
        return {"accepted": True}

    if event_type == "call.member_removed":
        uid = _user_id_from_member(body.get("member") or {})
        if uid:
            try:
                disconnected_user_id = UUID(uid)
                asyncio.create_task(
                    record_leave_if_new(
                        meeting_id, event_id_str, disconnected_user_id, now_utc
                    )
                )
            except ValueError:
                pass
        should_trigger = True
    elif event_type == "call.member_updated":
        member = body.get("member") or {}
        removed_flags = [
            member.get("removed"),
            member.get("deleted"),
            member.get("is_removed"),
        ]
        removed_flag = any(bool(f) for f in removed_flags)
        status = str(member.get("status") or "").strip().lower()
        inactive = status in {"left", "removed", "blocked"}
        if removed_flag or inactive:
            uid = _user_id_from_member(member)
            if uid:
                try:
                    disconnected_user_id = UUID(uid)
                    asyncio.create_task(
                        record_leave_if_new(
                            meeting_id,
                            event_id_str,
                            disconnected_user_id,
                            now_utc,
                        )
                    )
                    should_trigger = True
                except ValueError:
                    pass
    elif event_type == "call.session_ended":
        should_trigger = True

    if not should_trigger:
        incr("webhook_processed_total")
        return {"accepted": True}

    ran = await run_debounced_host_transfer(
        meeting_id, disconnected_user_id, event_type, start_time
    )
    if not ran:
        incr("webhook_processed_total")
    return {"accepted": True}
