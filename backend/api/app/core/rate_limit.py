import logging
from uuid import UUID

from fastapi import Depends, HTTPException, Request
from redis.asyncio import Redis

from app.core.config import (
    MEETING_JOIN_LIMIT,
    MEETING_JOIN_WINDOW_SECONDS,
    RATE_LIMIT_REQUESTS,
    RATE_LIMIT_WINDOW_SECONDS,
    STREAM_TOKEN_RATE_LIMIT_REQUESTS,
    STREAM_TOKEN_WINDOW_SECONDS,
)
from app.modules.auth.deps import get_current_user_id, get_current_user_optional
from app.state.client import get_redis

logger = logging.getLogger(__name__)

KEY_PREFIX_GENERAL = "ratelimit"
KEY_PREFIX_STREAM_TOKEN = "ratelimit:streamtoken"
KEY_PREFIX_MEETING_JOIN = "ratelimit:join"
WS_CONNECTION_PREFIX = f"{KEY_PREFIX_GENERAL}:ws"



async def check_rate_limit(
    redis: Redis,
    key: str,
    limit: int,
    window_seconds: int,
) -> bool:
    full_key = f"{key}"
    pipe = redis.pipeline()
    pipe.incr(full_key)
    pipe.ttl(full_key)
    results = await pipe.execute()
    count = results[0]
    ttl = results[1]
    if ttl == -1:
        await redis.expire(full_key, window_seconds)
    if count > limit:
        return False
    return True


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def rate_limit_by_identifier(
    request: Request,
    user_id: UUID | None,
    limit: int | None = None,
    window_seconds: int | None = None,
    key_prefix: str = KEY_PREFIX_GENERAL,
) -> None:
    limit = limit or RATE_LIMIT_REQUESTS
    window_seconds = window_seconds or RATE_LIMIT_WINDOW_SECONDS
    if user_id is not None:
        identifier = f"user:{user_id}"
    else:
        identifier = f"ip:{_client_ip(request)}"
    key = f"{key_prefix}:{identifier}"
    try:
        redis = await get_redis()
    except Exception:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")
    try:
        allowed = await check_rate_limit(redis, key, limit, window_seconds)
    except Exception:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")
    if not allowed:
        logger.warning(
            "rate_limit_triggered",
            extra={"identifier_type": "user" if user_id else "ip", "path": request.url.path},
        )
        raise HTTPException(status_code=429, detail="Too many requests")


async def rate_limit_general(
    request: Request,
    user_id: UUID | None = Depends(get_current_user_optional),
) -> None:
    await rate_limit_by_identifier(
        request,
        user_id,
        limit=RATE_LIMIT_REQUESTS,
        window_seconds=RATE_LIMIT_WINDOW_SECONDS,
        key_prefix=KEY_PREFIX_GENERAL,
    )


async def rate_limit_stream_token(
    request: Request,
    user_id: UUID = Depends(get_current_user_id),
) -> None:
    await rate_limit_by_identifier(
        request,
        user_id,
        limit=STREAM_TOKEN_RATE_LIMIT_REQUESTS,
        window_seconds=STREAM_TOKEN_WINDOW_SECONDS,
        key_prefix=KEY_PREFIX_STREAM_TOKEN,
    )


async def rate_limit_meeting_join(
    request: Request,
) -> None:
    await rate_limit_by_identifier(
        request,
        user_id=None,
        limit=MEETING_JOIN_LIMIT,
        window_seconds=MEETING_JOIN_WINDOW_SECONDS,
        key_prefix=KEY_PREFIX_MEETING_JOIN,
    )


async def rate_limit_ws_for_user(user_id: UUID) -> bool:
    redis = await get_redis()
    key = f"{WS_CONNECTION_PREFIX}:user:{user_id}"
    return await check_rate_limit(
        redis,
        key,
        limit=RATE_LIMIT_REQUESTS,
        window_seconds=RATE_LIMIT_WINDOW_SECONDS,
    )
