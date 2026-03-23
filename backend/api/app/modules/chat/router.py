from datetime import datetime, timezone
from uuid import UUID

import logging
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

from app.core.jwt import decode_access_token
from app.core.metrics import incr
from app.db.session import async_session_factory
from app.modules.chat.service import append_message
from app.modules.chat.websocket import _connections, _send_json
from app.modules.meetings.service import get_meeting_by_id
from app.state.client import get_redis


SYSTEM_USER_ID = "system:assistant"
SYSTEM_DISPLAY_NAME = "Assistant"

logger = logging.getLogger(__name__)

class AssistantMessageIn(BaseModel):
    text: str


router = APIRouter(prefix="/meetings", tags=["assistant"])


@router.post(
    "/{meeting_id}/assistant-message",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def post_assistant_message(
    meeting_id: UUID,
    body: AssistantMessageIn,
    request: Request,
):
    auth_header = request.headers.get("authorization") or ""
    prefix = "bearer "
    if not auth_header.lower().startswith(prefix):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid token",
        )
    token = auth_header[len(prefix) :].strip()
    try:
        payload = decode_access_token(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    sub = payload.get("sub")
    if sub != SYSTEM_USER_ID:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden",
        )
    async with async_session_factory() as session:
        meeting = await get_meeting_by_id(session, meeting_id)
    if not meeting or not meeting.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Meeting inactive",
        )
    try:
        redis = await get_redis()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable",
        )
    text = (body.text or "").strip()
    if not text:
        return
    ts = datetime.now(timezone.utc).isoformat()
    await append_message(
        redis,
        meeting_id,
        SYSTEM_USER_ID,
        SYSTEM_DISPLAY_NAME,
        ts,
        text,
    )
    incr("chat_messages_total")
    incr("assistant_responses_total")
    payload_out = {
        "type": "chat_message",
        "user_id": SYSTEM_USER_ID,
        "display_name": SYSTEM_DISPLAY_NAME,
        "timestamp": ts,
        "text": text,
    }
    for ws, _ in _connections.get(meeting_id, []):
        try:
            await _send_json(ws, payload_out)
        except Exception:
            logger.warning("chat_broadcast_send_failed", exc_info=True)

