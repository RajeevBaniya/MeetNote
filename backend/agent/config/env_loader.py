import os
from pathlib import Path
from typing import Tuple

from dotenv import load_dotenv

backend_root = Path(__file__).resolve().parent.parent.parent
load_dotenv(dotenv_path=backend_root / ".env")


def _require_env(name: str) -> str:
    val = os.getenv(name)
    if not val or not val.strip():
        raise ValueError(f"{name} is required in backend/.env")
    return val.strip()


def _get_int(name: str) -> int:
    return int(_require_env(name))


def _get_float(name: str) -> float:
    return float(_require_env(name))


# --- Core Server & Redis Config ---
MEETING_API_URL = _require_env("MEETING_API_URL").rstrip("/")
MEETING_API_URL_OVERRIDE = os.getenv("MEETING_API_URL_OVERRIDE")
REDIS_URL = _require_env("REDIS_URL")


# --- Auth & JWT Config ---
JWT_SECRET = _require_env("JWT_SECRET")
JWT_EXPIRE_MINUTES = _get_int("JWT_EXPIRE_MINUTES")


# --- Gemini API Config ---
GEMINI_API_KEY = _require_env("GEMINI_API_KEY")
GEMINI_MODEL_SUMMEREASE = _require_env("GEMINI_MODEL_SUMMEREASE")
GEMINI_EMBEDDING_MODEL_NAME = _require_env("GEMINI_EMBEDDING_MODEL_NAME")


# --- HTTP Client Settings ---
HTTP_TIMEOUT_SECONDS = float(os.getenv("HTTP_TIMEOUT_SECONDS", "5.0"))
HTTP_MAX_RETRIES = int(os.getenv("HTTP_MAX_RETRIES", "2"))


# --- Assistant Settings ---
ASSISTANT_DISPLAY_NAME = _require_env("ASSISTANT_DISPLAY_NAME")
ASSISTANT_FALLBACK_REPLY_MESSAGE = _require_env("ASSISTANT_FALLBACK_REPLY_MESSAGE")
ASSISTANT_COOLDOWN_SECONDS = _get_int("ASSISTANT_COOLDOWN_SECONDS")
ASSISTANT_LAST_QUESTION_TTL_SECONDS = _get_int("ASSISTANT_LAST_QUESTION_TTL_SECONDS")
ASSISTANT_CONTEXT_TRANSCRIPT_SEGMENTS = _get_int("ASSISTANT_CONTEXT_TRANSCRIPT_SEGMENTS")


# --- Agent Limits & Cooldowns ---
CHAT_HISTORY_MAX_LEN = _get_int("CHAT_HISTORY_MAX_LEN")
TRANSCRIPT_SEGMENTS_LIMIT = _get_int("TRANSCRIPT_SEGMENTS_LIMIT")
AGENT_EXTERNAL_APPROVAL_TTL_SECONDS = _get_int("AGENT_EXTERNAL_APPROVAL_TTL_SECONDS")
AGENT_REPLY_TIMEOUT_SECONDS = _get_float("AGENT_REPLY_TIMEOUT_SECONDS")


def load_and_validate_env() -> Tuple[str, str]:
    api_url = MEETING_API_URL
    if MEETING_API_URL_OVERRIDE:
        api_url = MEETING_API_URL_OVERRIDE.rstrip("/")
    return api_url, REDIS_URL
