"""
Redis pub/sub helpers for broadcasting live transcript segments.

Each meeting has a dedicated pub/sub channel.  When a transcript segment
arrives via the Stream webhook it is published here so all connected
WebSocket clients receive it in real-time.
"""

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
    """Publish a transcript segment dict to the meeting's pub/sub channel."""
    channel = _pub_channel(meeting_id)
    await redis.publish(channel, json.dumps(segment))
