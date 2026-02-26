import asyncio
import hashlib
import hmac
import json
import logging
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Request, status

from app.core.config import get_stream_api_key, get_stream_api_secret
from app.modules.chat.websocket import broadcast_host_changed
from app.modules.meetings.service import transfer_host_if_current_disconnected
from app.state.client import get_redis


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

ASSISTANT_SPEAKER_IDS: frozenset[str] = frozenset(
    {"system:assistant", "meeting-assistant-bot", "Assistant"}
)


def _parse_meeting_id(call_cid: str) -> UUID | None:
    """Extract UUID from Stream's `{type}:{id}` call identifier."""
    if ":" not in call_cid:
        return None
    _, raw_id = call_cid.split(":", 1)
    try:
        return UUID(raw_id)
    except ValueError:
        return None


def _is_final_caption(closed_caption: dict) -> bool:
    """Return True if the payload explicitly marks this caption as final.

    If the final flag is absent, we treat the segment as final to avoid
    silently dropping data on schema variations.
    """
    if not isinstance(closed_caption, dict):
        return True
    flag = None
    if "is_final" in closed_caption:
        flag = closed_caption.get("is_final")
    elif "final" in closed_caption:
        flag = closed_caption.get("final")
    if flag is None:
        return True
    if isinstance(flag, str):
        return flag.strip().lower() == "true"
    return bool(flag)


@router.post("/stream/transcript", status_code=status.HTTP_200_OK)
async def stream_transcript_webhook(
    request: Request,
    x_signature: str | None = Header(default=None, alias="X-Signature"),
    x_api_key: str | None = Header(default=None, alias="X-API-KEY"),
) -> dict:
    if not x_signature or not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )

    expected_api_key = get_stream_api_key()
    if x_api_key != expected_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )

    raw_body = await request.body()
    secret = get_stream_api_secret().encode("utf-8")
    computed = hmac.new(secret, raw_body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(computed, x_signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )

    try:
        body = json.loads(raw_body.decode("utf-8"))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON body",
        )

    if not isinstance(body, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Expected JSON object",
        )

    event_type = body.get("type")

    if event_type == "call.closed_caption":
        call_cid = str(body.get("call_cid") or "")
        meeting_id = _parse_meeting_id(call_cid)
        if meeting_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or missing call_cid",
            )

        cc = body.get("closed_caption") or {}
        if not _is_final_caption(cc):
            return {"accepted": True}

        text = (cc.get("text") or "").strip()
        if not text:
            return {"accepted": True}

        user = cc.get("user") or {}
        speaker_id: str | None = user.get("id") or None
        speaker_name: str | None = user.get("name") or None

        if speaker_id in ASSISTANT_SPEAKER_IDS or speaker_name in ASSISTANT_SPEAKER_IDS:
            return {"accepted": True}

        timestamp = cc.get("end_time") or cc.get("start_time") or body.get("created_at")
        if timestamp is not None:
            timestamp = str(timestamp)

        try:
            redis = await get_redis()
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service temporarily unavailable",
            )

        payload = {
            "meeting_id": str(meeting_id),
            "text": text,
            "speaker_id": speaker_id,
            "speaker_name": speaker_name,
            "timestamp": timestamp,
        }
        await redis.rpush("transcript_events", json.dumps(payload))
        return {"accepted": True}

    if event_type in {"call.member_removed", "call.member_updated", "call.session_ended"}:
        call_cid = str(body.get("call_cid") or "")
        meeting_id = _parse_meeting_id(call_cid)
        if meeting_id is None:
            return {"accepted": True}

        disconnected_user_id: UUID | None = None
        should_trigger = False

        if event_type == "call.member_removed":
            member = body.get("member") or {}
            user = member.get("user") or {}
            raw_user_id = user.get("id") or member.get("user_id")
            if isinstance(raw_user_id, str):
                try:
                    disconnected_user_id = UUID(raw_user_id)
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
                        should_trigger = True
                    except ValueError:
                        disconnected_user_id = None
        elif event_type == "call.session_ended":
            should_trigger = True

        if not should_trigger:
            return {"accepted": True}

        try:
            redis = await get_redis()
        except Exception:
            return {"accepted": True}

        lock_key = f"host_transfer_lock:{meeting_id}"
        got_lock = await redis.set(lock_key, "1", ex=5, nx=True)
        if not got_lock:
            return {"accepted": True}

        async def _debounced_transfer() -> None:
            await asyncio.sleep(3)
            try:
                new_host = await transfer_host_if_current_disconnected(
                    meeting_id, disconnected_user_id
                )
            except Exception:
                return
            if new_host is None:
                return
            await broadcast_host_changed(meeting_id, new_host)

        asyncio.create_task(_debounced_transfer())
        return {"accepted": True}

    return {"accepted": True}
