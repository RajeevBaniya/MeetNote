from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import jwt

from agent.config.agent_constants import AgentConstants
from agent.config.env_loader import get_jwt_secret


def generate_system_jwt() -> Optional[str]:
    try:
        secret = get_jwt_secret()
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=AgentConstants.JWT_EXPIRY_MINUTES
        )
        payload = {
            "sub": AgentConstants.SYSTEM_USER_ID,
            "exp": int(expire.timestamp()),
        }
        token = jwt.encode(payload, secret, algorithm="HS256")
        return token
    except Exception:
        return None

