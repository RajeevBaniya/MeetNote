import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from backend directory or parent directories if nested
_backend_dir = Path(__file__).resolve().parent.parent.parent.parent
_env_file = _backend_dir / ".env"
load_dotenv(_env_file)


def get_database_url() -> str:
    url = os.getenv("DATABASE_URL_SUMMEREASE")
    if not url or not url.strip():
        # Fallback to local test databases or throw
        raise ValueError("DATABASE_URL_SUMMEREASE is required")
    return url.strip()


def get_gemini_api_key() -> str:
    key = os.getenv("GEMINI_API_KEY_SUMMEREASE")
    if not key or not key.strip():
        raise ValueError("GEMINI_API_KEY_SUMMEREASE is required")
    return key.strip()


def get_gemini_model() -> str:
    model = os.getenv("GEMINI_MODEL_SUMMEREASE", "gemini-2.5-flash")
    return model.strip()


def get_gmail_user_email() -> str:
    email = os.getenv("GMAIL_USER_EMAIL")
    if not email or not email.strip():
        raise ValueError("GMAIL_USER_EMAIL is required")
    return email.strip()


def get_google_redirect_uri() -> str:
    uri = os.getenv("GOOGLE_REDIRECT_URI", "https://developers.google.com/oauthplayground")
    return uri.strip()


def get_jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET")
    if not secret or not secret.strip():
        raise ValueError("JWT_SECRET is required")
    return secret.strip()


def get_cors_origins() -> list[str]:
    origins_str = os.getenv("CORS_ORIGINS", "http://localhost:3000")
    return [origin.strip() for origin in origins_str.split(",") if origin.strip()]


def get_upload_dir() -> str:
    default_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "uploads",
    )
    path = os.getenv("SUMMEREASE_UPLOAD_DIR", default_dir)
    os.makedirs(path, exist_ok=True)
    return os.path.abspath(path)


def get_failed_retention_hours() -> int:
    raw = os.getenv("SUMMEREASE_FAILED_RETENTION_HOURS", "24")
    try:
        return max(1, int(raw))
    except ValueError:
        return 24
