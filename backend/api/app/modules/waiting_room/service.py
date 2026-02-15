from uuid import UUID

from redis.asyncio import Redis

WAITING_ROOM_TTL_SECONDS = 1200


def _join_queue_key(meeting_id: UUID) -> str:
    return f"meeting:{meeting_id}:join_queue"


def _approved_users_key(meeting_id: UUID) -> str:
    return f"meeting:{meeting_id}:approved_users"


def _rejected_users_key(meeting_id: UUID) -> str:
    return f"meeting:{meeting_id}:rejected_users"


async def get_pending_user_ids(redis: Redis, meeting_id: UUID) -> list[str]:
    key = _join_queue_key(meeting_id)
    raw = await redis.lrange(key, 0, -1)
    return [x if isinstance(x, str) else x.decode() for x in raw]


async def approve_user(redis: Redis, meeting_id: UUID, user_id: UUID) -> None:
    qkey = _join_queue_key(meeting_id)
    akey = _approved_users_key(meeting_id)
    uid = str(user_id)
    await redis.lrem(qkey, 0, uid)
    await redis.rpush(akey, uid)
    await redis.expire(akey, WAITING_ROOM_TTL_SECONDS)


async def reject_user(redis: Redis, meeting_id: UUID, user_id: UUID) -> None:
    qkey = _join_queue_key(meeting_id)
    rkey = _rejected_users_key(meeting_id)
    uid = str(user_id)
    await redis.lrem(qkey, 0, uid)
    await redis.rpush(rkey, uid)
    await redis.expire(rkey, WAITING_ROOM_TTL_SECONDS)
