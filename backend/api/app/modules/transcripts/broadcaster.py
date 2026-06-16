import json
from typing import Any
from uuid import UUID

from redis.asyncio import Redis

from app.state.redis_client import redis_publish


def _pub_channel(meeting_id: UUID) -> str:
    return f"transcript_channel:{meeting_id}"


async def publish_segment(
    redis: Redis,
    meeting_id: UUID,
    segment: dict[str, Any],
) -> None:
    await redis_publish(redis, _pub_channel(meeting_id), json.dumps(segment))


async def publish_correction(
    redis: Redis,
    meeting_id: UUID,
    correction: dict[str, Any],
) -> None:
    await redis_publish(redis, _pub_channel(meeting_id), json.dumps(correction))
