from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from jose import JWTError, jwt

from app.core.config import JWT_EXPIRE_MINUTES, JWT_SECRET


def create_access_token(user_id: UUID, email: str) -> str:
    secret = JWT_SECRET
    expire_minutes = JWT_EXPIRE_MINUTES
    expire = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": expire,
    }
    return str(jwt.encode(payload, secret, algorithm="HS256"))


def decode_access_token(token: str) -> dict[str, Any]:
    secret = JWT_SECRET
    payload = jwt.decode(token, secret, algorithms=["HS256"])
    if not isinstance(payload, dict):
        raise JWTError("Invalid payload type")
    return payload


def get_user_id_from_token(token: str) -> UUID | None:
    try:
        payload = decode_access_token(token)
        sub = payload.get("sub")
        if not sub:
            return None
        return UUID(sub)
    except (JWTError, ValueError):
        return None
