from uuid import UUID

from redis.asyncio import Redis

from app.modules.transcripts.redis_keys import chunks_key
from app.state.redis_client import redis_lrange


async def fetch_summary_chunk_summaries(redis: Redis, meeting_id: UUID) -> list[str]:
    key = chunks_key(meeting_id)
    return await redis_lrange(redis, key)
