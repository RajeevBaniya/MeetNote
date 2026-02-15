from redis.asyncio import Redis

from app.core.redis import get_redis_url

_client: Redis | None = None


async def get_redis() -> Redis:
    global _client
    url = get_redis_url()
    if not url:
        raise ValueError("REDIS_URL is required")
    if _client is None:
        _client = Redis.from_url(url, decode_responses=True)
    return _client


async def close_redis() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
