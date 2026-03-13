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
    raw = os.getenv("JWT_EXPIRE_MINUTES", "15")
    try:
        return int(raw)
    except ValueError:
        return 15


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


def get_stream_webhook_secret() -> str:
    secret = os.getenv("STREAM_WEBHOOK_SECRET")
    if not secret or not secret.strip():
        raise ValueError("STREAM_WEBHOOK_SECRET is required")
    return secret.strip()


def get_groq_chunk_api_key() -> str:
    key = os.getenv("GROQ_API_KEY_CHUNK")
    if not key or not key.strip():
        raise ValueError("GROQ_API_KEY_CHUNK is required")
    return key.strip()


def get_groq_chunk_model() -> str:
    model = os.getenv("GROQ_CHUNK_MODEL", "llama-3.1-8b-instant")
    return model.strip() or "llama-3.1-8b-instant"


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


def get_refresh_token_days() -> int:
    raw = os.getenv("REFRESH_TOKEN_DAYS", "14")
    try:
        days = int(raw)
    except ValueError:
        days = 14
    return max(7, min(days, 30))


def get_cookie_domain() -> str | None:
    raw = os.getenv("COOKIE_DOMAIN")
    if not raw:
        return None
    domain = raw.strip()
    return domain or None
