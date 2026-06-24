import json
from typing import Any
from uuid import UUID

from redis.asyncio import Redis

from app.core.config import CHAT_BUFFER_MAX_LEN, CHAT_BUFFER_TTL_SECONDS
from app.db.session import async_session_factory
from app.modules.auth.service import get_user_by_id

CHAT_BUFFER_KEY_PREFIX = "meeting:"
CHAT_BUFFER_KEY_SUFFIX = ":chat_messages"


def _chat_buffer_key(meeting_id: UUID) -> str:
    return f"{CHAT_BUFFER_KEY_PREFIX}{meeting_id}{CHAT_BUFFER_KEY_SUFFIX}"


async def get_user_display_name(user_id: UUID) -> str:
    async with async_session_factory() as session:
        user = await get_user_by_id(session, user_id)
    if not user or not user.name or not str(user.name).strip():
        return str(user_id)
    return str(user.name).strip()


async def append_message(
    redis: Redis,
    meeting_id: UUID,
    user_id: UUID | str,
    display_name: str,
    timestamp: str,
    text: str,
) -> None:
    key = _chat_buffer_key(meeting_id)
    payload = json.dumps({
        "user_id": str(user_id),
        "display_name": display_name,
        "timestamp": timestamp,
        "text": text,
    })
    await redis.rpush(key, payload)
    await redis.ltrim(key, -CHAT_BUFFER_MAX_LEN, -1)
    await redis.expire(key, CHAT_BUFFER_TTL_SECONDS)


async def get_recent_messages(redis: Redis, meeting_id: UUID) -> list[dict[str, Any]]:
    key = _chat_buffer_key(meeting_id)
    raw = await redis.lrange(key, -CHAT_BUFFER_MAX_LEN, -1)
    out = []
    for x in raw:
        s = x if isinstance(x, str) else x.decode()
        try:
            out.append(json.loads(s))
        except (json.JSONDecodeError, TypeError):
            continue
    return out
