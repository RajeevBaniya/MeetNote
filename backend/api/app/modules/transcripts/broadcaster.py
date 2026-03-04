import json
from uuid import UUID

from redis.asyncio import Redis


def _pub_channel(meeting_id: UUID) -> str:
    return f"transcript_channel:{meeting_id}"


async def publish_segment(
    redis: Redis,
    meeting_id: UUID,
    segment: dict,
) -> None:
    channel = _pub_channel(meeting_id)
    await redis.publish(channel, json.dumps(segment))
