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


# --- Core Server & CORS Config ---
PORT = int(os.getenv("PORT", "8001"))
SENTRY_DSN = _require_env("SENTRY_DSN")
APP_BASE_URL = _require_env("APP_BASE_URL")
if APP_BASE_URL.endswith("/"):
    APP_BASE_URL = APP_BASE_URL[:-1]

FRONTEND_BASE_URL = APP_BASE_URL
FRONTEND_BASE_URL_REQUIRED = APP_BASE_URL

_origins_str = _require_env("CORS_ORIGINS")
CORS_ORIGINS = [origin.strip() for origin in _origins_str.split(",") if origin.strip()]

COOKIE_DOMAIN = os.getenv("COOKIE_DOMAIN")
if COOKIE_DOMAIN:
    COOKIE_DOMAIN = COOKIE_DOMAIN.strip() or None
else:
    COOKIE_DOMAIN = None


# --- Database & Redis Config ---
DATABASE_URL = _require_env("DATABASE_URL")
REDIS_URL = _require_env("REDIS_URL")


# --- Auth & JWT Config ---
JWT_SECRET = _require_env("JWT_SECRET")
JWT_EXPIRE_MINUTES = _get_int("JWT_EXPIRE_MINUTES")
REFRESH_TOKEN_DAYS = _get_int("REFRESH_TOKEN_DAYS")


# --- Stream Video API Config ---
STREAM_API_KEY = _require_env("STREAM_API_KEY")
STREAM_API_SECRET = _require_env("STREAM_API_SECRET")
STREAM_WEBHOOK_SECRET = _require_env("STREAM_WEBHOOK_SECRET")
STREAM_TOKEN_EXPIRY_SECONDS = _get_int("STREAM_TOKEN_EXPIRY_SECONDS")
STREAM_TOKEN_WINDOW_SECONDS = _get_int("STREAM_TOKEN_WINDOW_SECONDS")
STREAM_TOKEN_RATE_LIMIT_REQUESTS = _get_int("STREAM_TOKEN_RATE_LIMIT_REQUESTS")


# --- AI Models & Assistant Config ---
GEMINI_API_KEY = _require_env("GEMINI_API_KEY")
GEMINI_EMBEDDING_MODEL_NAME = _require_env("GEMINI_EMBEDDING_MODEL_NAME")
ASSISTANT_DISPLAY_NAME = _require_env("ASSISTANT_DISPLAY_NAME")

GROQ_API_KEY_CHUNK = _require_env("GROQ_API_KEY_CHUNK")
GROQ_TRANSCRIPT_CORRECTION = _require_env("GROQ_TRANSCRIPT_CORRECTION")
GROQ_CHUNK_MODEL = os.getenv("GROQ_CHUNK_MODEL") or _require_env("GROQ_MODEL")

GEMINI_CORRECTION_MODEL_NAME = (
    os.getenv("GEMINI_CORRECTION_MODEL_NAME")
    or _require_env("GEMINI_MODEL_SUMMEREASE")
)

# --- Speech Gateway Config ---
DEEPGRAM_API_KEY_1 = os.getenv("DEEPGRAM_API_KEY_1", "").strip()
DEEPGRAM_API_KEY_2 = os.getenv("DEEPGRAM_API_KEY_2", "").strip()
DEEPGRAM_API_KEY_3 = os.getenv("DEEPGRAM_API_KEY_3", "").strip()
GLADIA_API_KEY = os.getenv("GLADIA_API_KEY", "").strip()
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY", "").strip()
SPEECHMATICS_API_KEY = os.getenv("SPEECHMATICS_API_KEY", "").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()

try:
    DEEPGRAM_COOLDOWN_SECONDS = int(os.getenv("DEEPGRAM_COOLDOWN_SECONDS", "300"))
except ValueError:
    DEEPGRAM_COOLDOWN_SECONDS = 300

try:
    GLADIA_COOLDOWN_SECONDS = int(os.getenv("GLADIA_COOLDOWN_SECONDS", "300"))
except ValueError:
    GLADIA_COOLDOWN_SECONDS = 300

try:
    ASSEMBLYAI_COOLDOWN_SECONDS = int(os.getenv("ASSEMBLYAI_COOLDOWN_SECONDS", "300"))
except ValueError:
    ASSEMBLYAI_COOLDOWN_SECONDS = 300

try:
    SPEECHMATICS_COOLDOWN_SECONDS = int(os.getenv("SPEECHMATICS_COOLDOWN_SECONDS", "300"))
except ValueError:
    SPEECHMATICS_COOLDOWN_SECONDS = 300

try:
    GROQ_COOLDOWN_SECONDS = int(os.getenv("GROQ_COOLDOWN_SECONDS", "300"))
except ValueError:
    GROQ_COOLDOWN_SECONDS = 300



# --- RAG Ingestion Config ---
ENABLE_RAG = _get_bool("ENABLE_RAG")
MAX_CHUNKS_PER_QUERY = _get_int("MAX_CHUNKS_PER_QUERY")
MAX_EMBEDDING_CALLS_PER_MINUTE = _get_int("MAX_EMBEDDING_CALLS_PER_MINUTE")

TRANSCRIPT_SIMILARITY_THRESHOLD = _get_float("TRANSCRIPT_SIMILARITY_THRESHOLD")
SUMMARY_SIMILARITY_THRESHOLD = _get_float("SUMMARY_SIMILARITY_THRESHOLD")
DOCUMENT_SIMILARITY_THRESHOLD = _get_float("DOCUMENT_SIMILARITY_THRESHOLD")


# --- Meeting Limits & Host Management ---
MEETING_JOIN_LIMIT = _get_int("MEETING_JOIN_LIMIT")
MEETING_JOIN_WINDOW_SECONDS = _get_int("MEETING_JOIN_WINDOW_SECONDS")
HOST_TRANSFER_DEBOUNCE_SECONDS = _get_int("HOST_TRANSFER_DEBOUNCE_SECONDS")
HOST_TRANSFER_LOCK_TTL_SECONDS = _get_int("HOST_TRANSFER_LOCK_TTL_SECONDS")


# --- Cache & Buffers Config ---
CHAT_BUFFER_MAX_LEN = _get_int("CHAT_BUFFER_MAX_LEN")
CHAT_BUFFER_TTL_SECONDS = _get_int("CHAT_BUFFER_TTL_SECONDS")
TRANSCRIPT_SEGMENT_THRESHOLD = _get_int("TRANSCRIPT_SEGMENT_THRESHOLD")
MUTEX_LOCK_TTL_SECONDS = _get_int("MUTEX_LOCK_TTL_SECONDS")
ACTIVE_MEETING_CACHE_TTL = _get_int("ACTIVE_MEETING_CACHE_TTL")
ENDED_MEETING_CACHE_TTL = _get_int("ENDED_MEETING_CACHE_TTL")

TRANSCRIPT_BUFFER_MAX_SEGMENTS = _get_int("TRANSCRIPT_BUFFER_MAX_SEGMENTS")
TRANSCRIPT_COMMIT_WINDOW_SECONDS = _get_float("TRANSCRIPT_COMMIT_WINDOW_SECONDS")


# --- Rate Limits & Workers Config ---
RATE_LIMIT_REQUESTS = _get_int("RATE_LIMIT_REQUESTS")
RATE_LIMIT_WINDOW_SECONDS = _get_int("RATE_LIMIT_WINDOW_SECONDS")
MEETING_STALE_CLEANUP_HOURS = _get_int("MEETING_STALE_CLEANUP_HOURS")
MEETING_CLEANUP_INTERVAL_SECONDS = _get_int("MEETING_CLEANUP_INTERVAL_SECONDS")


# --- Meeting Chat LLM Config ---
MEETING_CHAT_PRIMARY_PROVIDER = os.getenv("MEETING_CHAT_PRIMARY_PROVIDER", "gemini").strip()
MEETING_CHAT_GEMINI_API_KEY = os.getenv("MEETING_CHAT_GEMINI_API_KEY")
MEETING_CHAT_GEMINI_MODEL = os.getenv("MEETING_CHAT_GEMINI_MODEL")
MEETING_CHAT_GROQ_API_KEY = os.getenv("MEETING_CHAT_GROQ_API_KEY")
MEETING_CHAT_GROQ_MODEL = os.getenv("MEETING_CHAT_GROQ_MODEL")

if MEETING_CHAT_GEMINI_API_KEY:
    MEETING_CHAT_GEMINI_API_KEY = MEETING_CHAT_GEMINI_API_KEY.strip()
if MEETING_CHAT_GEMINI_MODEL:
    MEETING_CHAT_GEMINI_MODEL = MEETING_CHAT_GEMINI_MODEL.strip()
if MEETING_CHAT_GROQ_API_KEY:
    MEETING_CHAT_GROQ_API_KEY = MEETING_CHAT_GROQ_API_KEY.strip()
if MEETING_CHAT_GROQ_MODEL:
    MEETING_CHAT_GROQ_MODEL = MEETING_CHAT_GROQ_MODEL.strip()

if MEETING_CHAT_PRIMARY_PROVIDER == "gemini":
    if not MEETING_CHAT_GEMINI_API_KEY:
        raise ValueError("MEETING_CHAT_GEMINI_API_KEY is required when gemini is the primary provider")
    if not MEETING_CHAT_GEMINI_MODEL:
        raise ValueError("MEETING_CHAT_GEMINI_MODEL is required when gemini is the primary provider")
elif MEETING_CHAT_PRIMARY_PROVIDER == "groq":
    if not MEETING_CHAT_GROQ_API_KEY:
        raise ValueError("MEETING_CHAT_GROQ_API_KEY is required when groq is the primary provider")
    if not MEETING_CHAT_GROQ_MODEL:
        raise ValueError("MEETING_CHAT_GROQ_MODEL is required when groq is the primary provider")
else:
    raise ValueError(f"Unknown MEETING_CHAT_PRIMARY_PROVIDER: {MEETING_CHAT_PRIMARY_PROVIDER}")

try:
    MAX_TRANSCRIPT_CHUNKS_PER_QUERY = int(os.getenv("MAX_TRANSCRIPT_CHUNKS_PER_QUERY", "5"))
except ValueError:
    MAX_TRANSCRIPT_CHUNKS_PER_QUERY = 5

try:
    MAX_SUMMARY_CHUNKS_PER_QUERY = int(os.getenv("MAX_SUMMARY_CHUNKS_PER_QUERY", "3"))
except ValueError:
    MAX_SUMMARY_CHUNKS_PER_QUERY = 3

try:
    TRANSCRIPT_NEIGHBOR_WINDOW = int(os.getenv("TRANSCRIPT_NEIGHBOR_WINDOW", "2"))
except ValueError:
    TRANSCRIPT_NEIGHBOR_WINDOW = 2

try:
    MAX_EXPANDED_TRANSCRIPT_SEGMENTS = int(os.getenv("MAX_EXPANDED_TRANSCRIPT_SEGMENTS", "15"))
except ValueError:
    MAX_EXPANDED_TRANSCRIPT_SEGMENTS = 15

try:
    TRANSCRIPT_CHUNK_OVERLAP = int(os.getenv("TRANSCRIPT_CHUNK_OVERLAP", "1"))
except ValueError:
    TRANSCRIPT_CHUNK_OVERLAP = 1


