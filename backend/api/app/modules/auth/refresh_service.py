import hashlib
import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Tuple
from uuid import UUID

from fastapi import Response

from app.core.config import get_cookie_domain, get_refresh_token_days
from app.core.jwt import create_access_token
from app.core.metrics import incr
from app.state.client import get_redis


REFRESH_PREFIX = "refresh_token:"
REFRESH_COOKIE_NAME = "refresh_token"


def _refresh_ttl_seconds() -> int:
    days = get_refresh_token_days()
    return days * 24 * 60 * 60


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def _store_refresh_token(token: str, user_id: UUID) -> None:
    redis = await get_redis()
    ttl = _refresh_ttl_seconds()
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=ttl)
    payload = {
        "user_id": str(user_id),
        "created_at": now.isoformat(),
        "expires_at": expires_at.isoformat(),
    }
    token_hash = _hash_token(token)
    await redis.set(f"{REFRESH_PREFIX}{token_hash}", json.dumps(payload), ex=ttl)


def _new_refresh_token() -> str:
    # token_urlsafe(48) ~ 384 bits
    return secrets.token_urlsafe(48)


def set_refresh_cookie(response: Response, token: str) -> None:
    domain = get_cookie_domain()
    secure = bool(domain)
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/auth/refresh",
        domain=domain,
    )


def clear_refresh_cookie(response: Response) -> None:
    domain = get_cookie_domain()
    secure = bool(domain)
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path="/auth/refresh",
        domain=domain,
        samesite="lax",
        secure=secure,
    )


async def issue_session_tokens(user_id: UUID, email: str) -> Tuple[str, str]:
    access_token = create_access_token(user_id, email)
    refresh_token = _new_refresh_token()
    await _store_refresh_token(refresh_token, user_id)
    return access_token, refresh_token


async def _get_refresh_payload(token: str) -> dict[str, Any] | None:
    redis = await get_redis()
    token_hash = _hash_token(token)
    raw = await redis.get(f"{REFRESH_PREFIX}{token_hash}")
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    payload_dict: dict[str, Any] = data
    user_id = payload_dict.get("user_id")
    if not user_id:
        return None
    expires_at_raw = payload_dict.get("expires_at")
    if expires_at_raw:
        try:
            expires_at = datetime.fromisoformat(expires_at_raw)
            if expires_at <= datetime.now(timezone.utc):
                return None
        except Exception:
            return None
    return payload_dict


async def rotate_refresh_token(token: str) -> Tuple[UUID | None, str | None]:
    payload = await _get_refresh_payload(token)
    if not payload:
        incr("auth_refresh_failed_total")
        return None, None
    redis = await get_redis()
    await redis.delete(f"{REFRESH_PREFIX}{_hash_token(token)}")
    user_id = UUID(payload["user_id"])
    new_token = _new_refresh_token()
    await _store_refresh_token(new_token, user_id)
    incr("auth_refresh_rotation_total")
    return user_id, new_token


async def revoke_refresh_token(token: str) -> None:
    redis = await get_redis()
    await redis.delete(f"{REFRESH_PREFIX}{_hash_token(token)}")
    incr("auth_logout_total")


async def create_access_token_for_user(user_id: UUID, email: str) -> str:
    return create_access_token(user_id, email)

