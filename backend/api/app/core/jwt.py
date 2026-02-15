from datetime import datetime, timezone, timedelta
from uuid import UUID

from jose import JWTError, jwt

from app.core.config import get_jwt_expire_minutes, get_jwt_secret


def create_access_token(user_id: UUID, email: str) -> str:
    secret = get_jwt_secret()
    expire_minutes = get_jwt_expire_minutes()
    expire = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": expire,
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    secret = get_jwt_secret()
    return jwt.decode(token, secret, algorithms=["HS256"])


def get_user_id_from_token(token: str) -> UUID | None:
    try:
        payload = decode_access_token(token)
        sub = payload.get("sub")
        if not sub:
            return None
        return UUID(sub)
    except (JWTError, ValueError):
        return None
