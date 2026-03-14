import os
from pathlib import Path
from typing import Tuple

from dotenv import load_dotenv


def load_and_validate_env() -> Tuple[str, str]:
    backend_root = Path(__file__).resolve().parent.parent.parent
    load_dotenv(dotenv_path=backend_root / ".env")

    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        raise ValueError("GEMINI_API_KEY is required in backend/.env")

    api_base_url = os.getenv("MEETING_API_URL", "http://127.0.0.1:8001")
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        raise ValueError("REDIS_URL is required in backend/.env")

    return api_base_url.rstrip("/"), redis_url


def get_jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET")
    if not secret or not secret.strip():
        raise ValueError("JWT_SECRET is required in backend/.env")
    return secret.strip()

