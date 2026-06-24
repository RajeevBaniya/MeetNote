import json
import logging
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.modules.auth.deps import get_current_user_id
from app.state.client import get_redis

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

class WSTicketOut(BaseModel):
    ticket: str

WS_TICKET_PREFIX = "ws_ticket:"

@router.post("/ws-ticket", response_model=WSTicketOut)
async def generate_ws_ticket(user_id: UUID = Depends(get_current_user_id)) -> WSTicketOut:
    ticket = secrets.token_urlsafe(32)
    session_id = secrets.token_urlsafe(16)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=30)
    
    payload = {
        "user_id": str(user_id),
        "session_id": session_id,
        "issued_at": now.isoformat(),
        "expires_at": expires_at.isoformat()
    }
    
    redis = await get_redis()
    await redis.set(f"{WS_TICKET_PREFIX}{ticket}", json.dumps(payload), ex=30)
    
    return WSTicketOut(ticket=ticket)

async def validate_ws_ticket(ticket: str) -> UUID | None:
    if not ticket:
        return None
        
    redis = await get_redis()
    key = f"{WS_TICKET_PREFIX}{ticket}"
    raw = await redis.get(key)
    
    if not raw:
        logger.warning("ws_ticket_validation_failed: ticket not found or already used")
        return None
        
    # Single use: delete immediately
    await redis.delete(key)
    
    try:
        payload = json.loads(raw)
        expires_at = datetime.fromisoformat(payload["expires_at"])
        if expires_at < datetime.now(timezone.utc):
            logger.warning(f"ws_ticket_validation_failed: ticket expired for user {payload.get('user_id')}")
            return None
            
        return UUID(payload["user_id"])
    except Exception as e:
        logger.warning(f"ws_ticket_validation_failed: invalid payload format - {e}")
        return None
