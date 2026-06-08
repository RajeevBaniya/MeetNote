from uuid import UUID
import jwt
from app.core.config import get_jwt_secret


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
    except (jwt.PyJWTError, ValueError):
        return None

