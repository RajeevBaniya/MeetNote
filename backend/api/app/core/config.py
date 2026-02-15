import os
from pathlib import Path

from dotenv import load_dotenv

_backend_dir = Path(__file__).resolve().parent.parent.parent.parent
_env_file = _backend_dir / ".env"
load_dotenv(_env_file)


def get_database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url or not url.strip():
        raise ValueError("DATABASE_URL is required")
    return url.strip()


def get_jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET")
    if not secret or not secret.strip():
        raise ValueError("JWT_SECRET is required")
    return secret.strip()


def get_jwt_expire_minutes() -> int:
    raw = os.getenv("JWT_EXPIRE_MINUTES", "30")
    try:
        return int(raw)
    except ValueError:
        return 30


def get_stream_api_key() -> str:
    key = os.getenv("STREAM_API_KEY")
    if not key or not key.strip():
        raise ValueError("STREAM_API_KEY is required")
    return key.strip()


def get_stream_api_secret() -> str:
    secret = os.getenv("STREAM_API_SECRET")
    if not secret or not secret.strip():
        raise ValueError("STREAM_API_SECRET is required")
    return secret.strip()


def get_rate_limit_requests() -> int:
    raw = os.getenv("RATE_LIMIT_REQUESTS", "60")
    try:
        return max(1, int(raw))
    except ValueError:
        return 60


def get_rate_limit_window_seconds() -> int:
    raw = os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60")
    try:
        return max(1, int(raw))
    except ValueError:
        return 60


def get_stream_token_rate_limit_requests() -> int:
    raw = os.getenv("STREAM_TOKEN_RATE_LIMIT_REQUESTS", "5")
    try:
        return max(1, int(raw))
    except ValueError:
        return 5


def get_app_base_url() -> str:
    raw = os.getenv("APP_BASE_URL")
    if not raw or not raw.strip():
        raise ValueError("APP_BASE_URL is required")
    base = raw.strip()
    return base[:-1] if base.endswith("/") else base
