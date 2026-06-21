import os
from pathlib import Path
from dotenv import load_dotenv

_backend_dir = Path(__file__).resolve().parent.parent.parent.parent
_env_file = _backend_dir / ".env"
load_dotenv(_env_file)


def _require_env(name: str) -> str:
    val = os.getenv(name)
    if not val or not val.strip():
        raise ValueError(f"{name} is required")
    return val.strip()


def _get_int(name: str) -> int:
    val = _require_env(name)
    return int(val)


def _get_float(name: str) -> float:
    val = _require_env(name)
    return float(val)


def _get_bool(name: str) -> bool:
    val = _require_env(name)
    return val.lower() in ("true", "1", "yes")


# --- Mandatory Configurations (No defaults in code, must exist in .env) ---
DATABASE_URL = _require_env("DATABASE_URL")
JWT_SECRET = _require_env("JWT_SECRET")
JWT_EXPIRE_MINUTES = _get_int("JWT_EXPIRE_MINUTES")

STREAM_API_KEY = _require_env("STREAM_API_KEY")
STREAM_API_SECRET = _require_env("STREAM_API_SECRET")
STREAM_WEBHOOK_SECRET = _require_env("STREAM_WEBHOOK_SECRET")

GROQ_API_KEY_CHUNK = _require_env("GROQ_API_KEY_CHUNK")
GROQ_TRANSCRIPT_CORRECTION = _require_env("GROQ_TRANSCRIPT_CORRECTION")
GEMINI_API_KEY = _require_env("GEMINI_API_KEY")

REDIS_URL = _require_env("REDIS_URL")

APP_BASE_URL = _require_env("APP_BASE_URL")
if APP_BASE_URL.endswith("/"):
    APP_BASE_URL = APP_BASE_URL[:-1]

FRONTEND_BASE_URL = APP_BASE_URL
FRONTEND_BASE_URL_REQUIRED = APP_BASE_URL

# CORS Origins loaded exclusively from env
_origins_str = _require_env("CORS_ORIGINS")
CORS_ORIGINS = [origin.strip() for origin in _origins_str.split(",") if origin.strip()]

# RAG Ingestion and Core Settings
ENABLE_RAG = _get_bool("ENABLE_RAG")
MAX_CHUNKS_PER_QUERY = _get_int("MAX_CHUNKS_PER_QUERY")
MAX_EMBEDDING_CALLS_PER_MINUTE = _get_int("MAX_EMBEDDING_CALLS_PER_MINUTE")

TRANSCRIPT_SIMILARITY_THRESHOLD = _get_float("TRANSCRIPT_SIMILARITY_THRESHOLD")
SUMMARY_SIMILARITY_THRESHOLD = _get_float("SUMMARY_SIMILARITY_THRESHOLD")
DOCUMENT_SIMILARITY_THRESHOLD = _get_float("DOCUMENT_SIMILARITY_THRESHOLD")

# Stream API Settings
STREAM_TOKEN_EXPIRY_SECONDS = _get_int("STREAM_TOKEN_EXPIRY_SECONDS")
STREAM_TOKEN_WINDOW_SECONDS = _get_int("STREAM_TOKEN_WINDOW_SECONDS")
STREAM_TOKEN_RATE_LIMIT_REQUESTS = _get_int("STREAM_TOKEN_RATE_LIMIT_REQUESTS")

# Meeting Limitations
MEETING_JOIN_LIMIT = _get_int("MEETING_JOIN_LIMIT")
MEETING_JOIN_WINDOW_SECONDS = _get_int("MEETING_JOIN_WINDOW_SECONDS")

# Chat Buffers and Cache TTLs
CHAT_BUFFER_MAX_LEN = _get_int("CHAT_BUFFER_MAX_LEN")
CHAT_BUFFER_TTL_SECONDS = _get_int("CHAT_BUFFER_TTL_SECONDS")
TRANSCRIPT_SEGMENT_THRESHOLD = _get_int("TRANSCRIPT_SEGMENT_THRESHOLD")
MUTEX_LOCK_TTL_SECONDS = _get_int("MUTEX_LOCK_TTL_SECONDS")
ACTIVE_MEETING_CACHE_TTL = _get_int("ACTIVE_MEETING_CACHE_TTL")
ENDED_MEETING_CACHE_TTL = _get_int("ENDED_MEETING_CACHE_TTL")

# Ingestion buffering and timing
TRANSCRIPT_BUFFER_MAX_SEGMENTS = _get_int("TRANSCRIPT_BUFFER_MAX_SEGMENTS")
TRANSCRIPT_COMMIT_WINDOW_SECONDS = _get_float("TRANSCRIPT_COMMIT_WINDOW_SECONDS")

# Host transfer locks and delays
HOST_TRANSFER_DEBOUNCE_SECONDS = _get_int("HOST_TRANSFER_DEBOUNCE_SECONDS")
HOST_TRANSFER_LOCK_TTL_SECONDS = _get_int("HOST_TRANSFER_LOCK_TTL_SECONDS")

# Meeting cleanup background workers
MEETING_STALE_CLEANUP_HOURS = _get_int("MEETING_STALE_CLEANUP_HOURS")
MEETING_CLEANUP_INTERVAL_SECONDS = _get_int("MEETING_CLEANUP_INTERVAL_SECONDS")

# Rate Limiting
RATE_LIMIT_REQUESTS = _get_int("RATE_LIMIT_REQUESTS")
RATE_LIMIT_WINDOW_SECONDS = _get_int("RATE_LIMIT_WINDOW_SECONDS")
REFRESH_TOKEN_DAYS = _get_int("REFRESH_TOKEN_DAYS")

# Assistant displays and embedding models
ASSISTANT_DISPLAY_NAME = _require_env("ASSISTANT_DISPLAY_NAME")
GEMINI_EMBEDDING_MODEL_NAME = _require_env("GEMINI_EMBEDDING_MODEL_NAME")

# Error monitoring
SENTRY_DSN = _require_env("SENTRY_DSN")


# --- Optional Configurations (Kept fallback defaults only for truly optional configuration) ---
COOKIE_DOMAIN = os.getenv("COOKIE_DOMAIN")
if COOKIE_DOMAIN:
    COOKIE_DOMAIN = COOKIE_DOMAIN.strip() or None
else:
    COOKIE_DOMAIN = None

PORT = int(os.getenv("PORT", "8001"))

# Fallbacks to other environment variables which exist in .env
GROQ_CHUNK_MODEL = os.getenv("GROQ_CHUNK_MODEL") or _require_env("GROQ_MODEL")
GEMINI_CORRECTION_MODEL_NAME = (
    os.getenv("GEMINI_CORRECTION_MODEL_NAME")
    or _require_env("GEMINI_MODEL_SUMMEREASE")
)
