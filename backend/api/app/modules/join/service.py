from uuid import UUID

from redis.asyncio import Redis

JOIN_QUEUE_TTL_SECONDS = 1200


def _join_queue_key(meeting_id: UUID) -> str:
    return f"meeting:{meeting_id}:join_queue"


async def enqueue_join_request(redis: Redis, meeting_id: UUID, user_id: UUID) -> None:
    key = _join_queue_key(meeting_id)
    await redis.rpush(key, str(user_id))
    await redis.expire(key, JOIN_QUEUE_TTL_SECONDS)
