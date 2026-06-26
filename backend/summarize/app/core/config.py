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
    return int(_require_env(name))


def _get_float(name: str) -> float:
    return float(_require_env(name))


# --- Core Server & CORS Config ---
PORT = int(os.getenv("PORT", "8002"))

_origins_str = _require_env("CORS_ORIGINS")
CORS_ORIGINS = [origin.strip() for origin in _origins_str.split(",") if origin.strip()]


# --- Database & Auth Config ---
DATABASE_URL_SUMMEREASE = _require_env("DATABASE_URL_SUMMEREASE")
JWT_SECRET = _require_env("JWT_SECRET")


# --- S3 Storage Config ---
S3_ENDPOINT_URL = _require_env("S3_ENDPOINT_URL")
S3_ACCESS_KEY_ID = _require_env("S3_ACCESS_KEY_ID")
S3_SECRET_ACCESS_KEY = _require_env("S3_SECRET_ACCESS_KEY")
S3_BUCKET_NAME = _require_env("S3_BUCKET_NAME")


# --- Gmail & Redirect Config ---
GMAIL_USER_EMAIL = _require_env("GMAIL_USER_EMAIL")
GOOGLE_REDIRECT_URI = _require_env("GOOGLE_REDIRECT_URI")


# --- AI Provider Config ---
AI_PROVIDER_PRIMARY = os.getenv("AI_PROVIDER_PRIMARY", "gemini").strip()
AI_PROVIDER_HEALTH_CHECK_INTERVAL_SECONDS = int(os.getenv("AI_PROVIDER_HEALTH_CHECK_INTERVAL_SECONDS", "300"))

GEMINI_API_KEY_SUMMEREASE = os.getenv("GEMINI_API_KEY_SUMMEREASE")
GEMINI_MODEL_SUMMEREASE = os.getenv("GEMINI_MODEL_SUMMEREASE")

GROQ_API_KEY_SUMMEREASE = os.getenv("GROQ_API_KEY_SUMMEREASE")
GROQ_MODEL_SUMMEREASE = os.getenv("GROQ_MODEL_SUMMEREASE")

if AI_PROVIDER_PRIMARY == "gemini":
    if not GEMINI_API_KEY_SUMMEREASE or not GEMINI_API_KEY_SUMMEREASE.strip():
        raise ValueError("GEMINI_API_KEY_SUMMEREASE is required when gemini is the primary provider")
    if not GEMINI_MODEL_SUMMEREASE or not GEMINI_MODEL_SUMMEREASE.strip():
        raise ValueError("GEMINI_MODEL_SUMMEREASE is required when gemini is the primary provider")
elif AI_PROVIDER_PRIMARY == "groq":
    if not GROQ_API_KEY_SUMMEREASE or not GROQ_API_KEY_SUMMEREASE.strip():
        raise ValueError("GROQ_API_KEY_SUMMEREASE is required when groq is the primary provider")
    if not GROQ_MODEL_SUMMEREASE or not GROQ_MODEL_SUMMEREASE.strip():
        raise ValueError("GROQ_MODEL_SUMMEREASE is required when groq is the primary provider")
else:
    raise ValueError(f"Unknown AI_PROVIDER_PRIMARY: {AI_PROVIDER_PRIMARY}")

if GEMINI_API_KEY_SUMMEREASE:
    GEMINI_API_KEY_SUMMEREASE = GEMINI_API_KEY_SUMMEREASE.strip()
if GEMINI_MODEL_SUMMEREASE:
    GEMINI_MODEL_SUMMEREASE = GEMINI_MODEL_SUMMEREASE.strip()
if GROQ_API_KEY_SUMMEREASE:
    GROQ_API_KEY_SUMMEREASE = GROQ_API_KEY_SUMMEREASE.strip()
if GROQ_MODEL_SUMMEREASE:
    GROQ_MODEL_SUMMEREASE = GROQ_MODEL_SUMMEREASE.strip()

if GROQ_API_KEY_SUMMEREASE or GROQ_MODEL_SUMMEREASE:
    if not GROQ_API_KEY_SUMMEREASE:
        raise ValueError("GROQ_API_KEY_SUMMEREASE is required when Groq is configured")
    if not GROQ_MODEL_SUMMEREASE:
        raise ValueError("GROQ_MODEL_SUMMEREASE is required when Groq is configured")

if GEMINI_API_KEY_SUMMEREASE or GEMINI_MODEL_SUMMEREASE:
    if not GEMINI_API_KEY_SUMMEREASE:
        raise ValueError("GEMINI_API_KEY_SUMMEREASE is required when Gemini is configured")
    if not GEMINI_MODEL_SUMMEREASE:
        raise ValueError("GEMINI_MODEL_SUMMEREASE is required when Gemini is configured")



# --- Summerease Specific Settings ---
_supported_exts_raw = _require_env("SUMMEREASE_SUPPORTED_EXTENSIONS")
SUMMEREASE_SUPPORTED_EXTENSIONS = [ext.strip() for ext in _supported_exts_raw.split(",") if ext.strip()]

SUMMEREASE_MAX_FILE_SIZE = _get_int("SUMMEREASE_MAX_FILE_SIZE")
SUMMEREASE_INGESTION_INTERVAL_SECONDS = _get_float("SUMMEREASE_INGESTION_INTERVAL_SECONDS")
SUMMEREASE_RECOVERY_INTERVAL_SECONDS = _get_float("SUMMEREASE_RECOVERY_INTERVAL_SECONDS")
SUMMEREASE_TOKEN_REFRESH_INTERVAL = _get_float("SUMMEREASE_TOKEN_REFRESH_INTERVAL")

SUMMEREASE_MAX_RETRIES = _get_int("SUMMEREASE_MAX_RETRIES")
SUMMEREASE_THROTTLE_DELAY = float(os.getenv("SUMMEREASE_THROTTLE_DELAY", "0.5"))

# ---------------------------------------------------------------------------
# AI Output Token Limits
# These control how many tokens Gemini may produce at each pipeline stage.
# Raising these increases output completeness but also increases cost and latency.
# ---------------------------------------------------------------------------

# Tokens allowed for each individual chunk summary (covers ~80 pages of dense text)
SUMMEREASE_CHUNK_SUMMARY_MAX_TOKENS = int(os.getenv("SUMMEREASE_CHUNK_SUMMARY_MAX_TOKENS", "4000"))

# Tokens allowed for each merge call output (final or intermediate)
SUMMEREASE_MERGE_MAX_TOKENS = int(os.getenv("SUMMEREASE_MERGE_MAX_TOKENS", "6000"))

# Tokens allowed for the direct single-pass summary (live meetings, small uploads)
SUMMEREASE_DIRECT_SUMMARY_MAX_TOKENS = int(os.getenv("SUMMEREASE_DIRECT_SUMMARY_MAX_TOKENS", "4000"))

# ---------------------------------------------------------------------------
# Chunk Sizing — Token-Aware with Character Approximation
#
# English prose averages approximately 4 characters per token.
# This is a known approximation; exact tokenization requires model-specific
# libraries (e.g. tiktoken) which are not present in this service.
# The constant is isolated here so it can be updated when a tokenizer is
# introduced without touching chunking or AI logic.
# ---------------------------------------------------------------------------

# Approximate characters per token for the current model family
SUMMEREASE_CHARS_PER_TOKEN = int(os.getenv("SUMMEREASE_CHARS_PER_TOKEN", "4"))

# Target tokens per document chunk (50,000 tokens ≈ ~80 pages of prose)
SUMMEREASE_CHUNK_TARGET_TOKENS = int(os.getenv("SUMMEREASE_CHUNK_TARGET_TOKENS", "50000"))

# Derived character limit for chunker — keep this computed, not hardcoded
SUMMEREASE_CHUNK_SIZE_CHARS = SUMMEREASE_CHUNK_TARGET_TOKENS * SUMMEREASE_CHARS_PER_TOKEN

# Overlap between consecutive chunks in characters (10 % of chunk size)
SUMMEREASE_CHUNK_OVERLAP_CHARS = SUMMEREASE_CHUNK_SIZE_CHARS // 10

# ---------------------------------------------------------------------------
# Merge Strategy Configuration
# ---------------------------------------------------------------------------

# Maximum summaries merged in one Gemini call (controls recursion fan-in)
SUMMEREASE_MERGE_GROUP_SIZE = int(os.getenv("SUMMEREASE_MERGE_GROUP_SIZE", "8"))

# Estimated input token threshold above which a merge call is split into groups.
# At 4 chars/token, 80,000 tokens ≈ 320,000 characters of summary text input.
SUMMEREASE_MERGE_INPUT_TOKEN_THRESHOLD = int(
    os.getenv("SUMMEREASE_MERGE_INPUT_TOKEN_THRESHOLD", "80000")
)

