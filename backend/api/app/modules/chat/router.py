import json
import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

from app.core.config import ASSISTANT_DISPLAY_NAME
from app.core.jwt import decode_access_token
from app.core.metrics import incr
from app.db.session import async_session_factory
from app.modules.chat.service import append_message
from app.modules.meetings.service import get_meeting_by_id
from app.state.client import get_redis

SYSTEM_USER_ID = "system:assistant"
SYSTEM_DISPLAY_NAME = ASSISTANT_DISPLAY_NAME

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
) -> None:
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
    try:
        pub_data = {
            "event": "chat_message",
            "payload": payload_out
        }
        await redis.publish(f"chat:broadcast:{meeting_id}", json.dumps(pub_data))
        logger.info("Published assistant message to Redis for meeting %s", meeting_id)
    except Exception as exc:
        logger.error("Failed to publish assistant message to Redis for meeting %s: %s", meeting_id, exc)

