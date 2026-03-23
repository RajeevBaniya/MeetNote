from uuid import UUID

from redis.asyncio import Redis

from app.modules.transcripts.redis_keys import chunks_key


async def fetch_summary_chunk_summaries(redis: Redis, meeting_id: UUID) -> list[str]:
    key = chunks_key(meeting_id)
    parts = await redis.lrange(key, 0, -1)
    return [str(p) for p in parts if p]
