import os


def get_redis_url() -> str | None:
    raw = os.getenv("REDIS_URL")
    if not raw or not raw.strip():
        return None
    return raw.strip()
