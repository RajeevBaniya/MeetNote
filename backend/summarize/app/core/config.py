import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from backend directory or parent directories if nested
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


# --- Mandatory Configurations (No defaults in code, must exist in .env) ---
DATABASE_URL_SUMMEREASE = _require_env("DATABASE_URL_SUMMEREASE")
GEMINI_API_KEY_SUMMEREASE = _require_env("GEMINI_API_KEY_SUMMEREASE")
GEMINI_MODEL_SUMMEREASE = _require_env("GEMINI_MODEL_SUMMEREASE")
GMAIL_USER_EMAIL = _require_env("GMAIL_USER_EMAIL")
GOOGLE_REDIRECT_URI = _require_env("GOOGLE_REDIRECT_URI")
JWT_SECRET = _require_env("JWT_SECRET")

# S3 Configurations
S3_ENDPOINT_URL = _require_env("S3_ENDPOINT_URL")
S3_ACCESS_KEY_ID = _require_env("S3_ACCESS_KEY_ID")
S3_SECRET_ACCESS_KEY = _require_env("S3_SECRET_ACCESS_KEY")
S3_BUCKET_NAME = _require_env("S3_BUCKET_NAME")

# CORS Origins (loaded exclusively from env)
_origins_str = _require_env("CORS_ORIGINS")
CORS_ORIGINS = [origin.strip() for origin in _origins_str.split(",") if origin.strip()]

# Summerease Specific Configurations (loaded exclusively from env)
_supported_exts_raw = _require_env("SUMMEREASE_SUPPORTED_EXTENSIONS")
SUMMEREASE_SUPPORTED_EXTENSIONS = [ext.strip() for ext in _supported_exts_raw.split(",") if ext.strip()]

SUMMEREASE_MAX_FILE_SIZE = _get_int("SUMMEREASE_MAX_FILE_SIZE")
SUMMEREASE_POLL_INTERVAL = _get_float("SUMMEREASE_POLL_INTERVAL")
SUMMEREASE_RECOVERY_INTERVAL = _get_float("SUMMEREASE_RECOVERY_INTERVAL")
SUMMEREASE_ERROR_INTERVAL = _get_float("SUMMEREASE_ERROR_INTERVAL")

SUMMEREASE_MAX_RETRIES = _get_int("SUMMEREASE_MAX_RETRIES")
SUMMEREASE_THROTTLE_DELAY = _get_float("SUMMEREASE_THROTTLE_DELAY")

# --- Optional Configurations (Kept fallback defaults only for truly optional configuration) ---
PORT = int(os.getenv("PORT", "8002"))
