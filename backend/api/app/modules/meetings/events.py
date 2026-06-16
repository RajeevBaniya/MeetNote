import logging
from uuid import UUID
import json

from app.state.client import get_redis

logger = logging.getLogger(__name__)

MEETING_CREATED_CHANNEL = "meeting:created"
MEETING_ENDED_CHANNEL = "meeting:ended"
MEETING_SNAPSHOT_CHANNEL = "meeting:snapshot"
MEETING_ASSISTANT_PREFERENCE_CHANNEL = "meeting:assistant_preference"


async def publish_meeting_created(meeting_id: UUID, host_id: UUID) -> None:
    try:
        redis = await get_redis()
        await redis.set(f"meeting:host_id:{meeting_id}", str(host_id))
        await redis.publish(MEETING_CREATED_CHANNEL, str(meeting_id))
        logger.debug("Published meeting:created event for meeting_id=%s with host_id=%s", meeting_id, host_id)
    except Exception as exc:
        logger.warning("Failed to publish meeting:created event", exc_info=exc)


async def publish_meeting_ended(meeting_id: UUID) -> None:
    try:
        redis = await get_redis()
        await redis.publish(MEETING_ENDED_CHANNEL, str(meeting_id))
        logger.debug("Published meeting:ended event for meeting_id=%s", meeting_id)
    except Exception as exc:
        logger.warning("Failed to publish meeting:ended event", exc_info=exc)


async def publish_meeting_snapshot(meeting_ids: list[UUID]) -> None:
    try:
        redis = await get_redis()
        payload = {"meeting_ids": [str(mid) for mid in meeting_ids]}
        await redis.publish(MEETING_SNAPSHOT_CHANNEL, json.dumps(payload))
        logger.debug(
            "Published meeting:snapshot event with %d active meetings",
            len(meeting_ids),
        )
    except Exception as exc:
        logger.warning("Failed to publish meeting:snapshot event", exc_info=exc)


async def publish_meeting_assistant_preference(meeting_id: UUID, enabled: bool) -> None:
    try:
        redis = await get_redis()
        payload = json.dumps({"meeting_id": str(meeting_id), "enabled": enabled})
        await redis.publish(MEETING_ASSISTANT_PREFERENCE_CHANNEL, payload)
        logger.debug(
            "Published meeting:assistant_preference for meeting_id=%s enabled=%s",
            meeting_id,
            enabled,
        )
    except Exception as exc:
        logger.warning(
            "Failed to publish meeting:assistant_preference event", exc_info=exc
        )
