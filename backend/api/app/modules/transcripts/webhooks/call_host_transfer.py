import asyncio
import logging
from datetime import datetime, timezone
from uuid import UUID

from app.core.config import (
    HOST_TRANSFER_DEBOUNCE_SECONDS,
    HOST_TRANSFER_LOCK_TTL_SECONDS,
)
from app.core.metrics import incr
from app.modules.chat.websocket import broadcast_host_changed
from app.modules.meetings.service import transfer_host_if_current_disconnected
from app.state.client import get_redis
from app.state.redis_client import redis_set

logger = logging.getLogger(__name__)


async def run_debounced_host_transfer(
    meeting_id: UUID,
    disconnected_user_id: UUID | None,
    event_type: str,
    start_time: datetime,
) -> bool:
    try:
        redis = await get_redis()
    except Exception:
        logger.warning("host_transfer_redis_unavailable", exc_info=True)
        return False

    lock_key = f"host_transfer_lock:{meeting_id}"
    got_lock = await redis_set(
        redis, lock_key, "1", ex=HOST_TRANSFER_LOCK_TTL_SECONDS, nx=True
    )
    if not got_lock:
        return False

    async def _debounced_transfer() -> None:
        await asyncio.sleep(HOST_TRANSFER_DEBOUNCE_SECONDS)
        try:
            new_host = await transfer_host_if_current_disconnected(
                meeting_id,
                disconnected_user_id,
            )
        except Exception:
            logger.exception("transfer_host_if_current_disconnected_failed")
            return
        if new_host is None:
            return
        await broadcast_host_changed(meeting_id, new_host)

    asyncio.create_task(_debounced_transfer())

    processing_ms = int(
        (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
    )
    logger.info(
        "webhook_processed",
        extra={
            "meeting_id": str(meeting_id),
            "event_type": event_type,
            "processing_time_ms": processing_ms,
        },
    )
    if processing_ms > 2000:
        logger.warning(
            "webhook_slow",
            extra={
                "meeting_id": str(meeting_id),
                "event_type": event_type,
                "processing_time_ms": processing_ms,
            },
        )
    incr("webhook_processed_total")
    return True
