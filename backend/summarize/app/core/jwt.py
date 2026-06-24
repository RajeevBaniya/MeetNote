from uuid import UUID

from jose import JWTError, jwt

from app.core.config import JWT_SECRET


def decode_access_token(token: str) -> dict:
    secret = JWT_SECRET
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

