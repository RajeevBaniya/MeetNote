from datetime import datetime, timezone
from uuid import UUID

import logging

from app.modules.analytics.service import (
    record_participant_join,
    record_participant_leave,
)
from app.state.client import get_redis

logger = logging.getLogger(__name__)


async def record_join_if_new(
    meeting_id: UUID,
    event_id_str: str,
    user_id_str: str,
    now_utc: datetime | None = None,
) -> None:
    if not event_id_str:
        return
    try:
        redis_client = await get_redis()
    except Exception:
        logger.warning("call_analytics_redis_unavailable", exc_info=True)
        return
    key = f"analytics_event_seen:{meeting_id}:{event_id_str}"
    if not await redis_client.set(key, "1", ex=3600, nx=True):
        return
    try:
        uid = UUID(user_id_str)
        ts = now_utc or datetime.now(timezone.utc)
        await record_participant_join(meeting_id, uid, ts)
    except ValueError:
        return


async def record_leave_if_new(
    meeting_id: UUID,
    event_id_str: str,
    user_id: UUID,
    now_utc: datetime | None = None,
) -> None:
    if not event_id_str:
        return
    try:
        redis_client = await get_redis()
    except Exception:
        logger.warning("call_analytics_redis_unavailable", exc_info=True)
        return
    key = f"analytics_event_seen:{meeting_id}:{event_id_str}"
    if not await redis_client.set(key, "1", ex=3600, nx=True):
        return
    ts = now_utc or datetime.now(timezone.utc)
    await record_participant_leave(meeting_id, user_id, ts)
