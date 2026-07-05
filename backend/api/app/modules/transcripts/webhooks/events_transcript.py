import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import HTTPException, status

from app.core.config import ASSISTANT_DISPLAY_NAME
from app.core.metrics import incr
from app.modules.transcripts.transcript_event_payload import (
    TRANSCRIPT_EVENTS_QUEUE,
    build_transcript_event_payload,
)
from app.modules.transcripts.webhooks.utils import parse_meeting_id
from app.state.client import get_redis
from app.state.redis_client import redis_rpush

logger = logging.getLogger(__name__)


def get_assistant_speaker_ids() -> frozenset[str]:
    return frozenset({"system:assistant", "meeting-assistant-bot", ASSISTANT_DISPLAY_NAME})


def _is_final_caption(closed_caption: Dict[str, Any]) -> bool:
    if not isinstance(closed_caption, dict):
        return True
    flag = None
    if "is_final" in closed_caption:
        flag = closed_caption.get("is_final")
    elif "final" in closed_caption:
        flag = closed_caption.get("final")
    if flag is None:
        return True
    if isinstance(flag, str):
        return flag.strip().lower() == "true"
    return bool(flag)


async def handle_transcript_event(
    body: Dict[str, Any],
    start_time: datetime,
) -> Dict[str, bool]:
    call_cid = str(body.get("call_cid") or "")
    meeting_id = parse_meeting_id(call_cid)
    if meeting_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or missing call_cid",
        )

    cc = body.get("closed_caption") or {}
    if not _is_final_caption(cc):
        incr("webhook_processed_total")
        return {"accepted": True}

    text = (cc.get("text") or "").strip()
    if not text:
        incr("webhook_processed_total")
        return {"accepted": True}

    meeting_id_for_log = str(meeting_id)
    user = cc.get("user") or {}
    speaker_id: str | None = user.get("id") or None
    speaker_name: str | None = user.get("name") or None

    if speaker_id in get_assistant_speaker_ids() or speaker_name in get_assistant_speaker_ids():
        incr("webhook_processed_total")
        return {"accepted": True}

    timestamp_value = (
        cc.get("end_time")
        or cc.get("start_time")
        or body.get("created_at")
    )
    if timestamp_value is not None:
        timestamp_str = str(timestamp_value)
    else:
        timestamp_str = None

    try:
        redis = await get_redis()
    except Exception as exc:
        incr("webhook_failures_total")
        logger.warning(
            "webhook_redis_unavailable",
            extra={"meeting_id": meeting_id_for_log},
            exc_info=exc,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable",
        )

    # Check if Speech Gateway is active for this meeting
    gateway_active = False
    try:
        gateway_active_key = f"speech:meeting:{meeting_id}:gateway_active"
        gateway_active_val = await redis.get(gateway_active_key)
        gateway_active = bool(gateway_active_val == "1")
    except Exception as exc:
        logger.warning(
            "webhook_redis_check_failed_fallback_to_webhook",
            extra={"meeting_id": meeting_id_for_log},
            exc_info=exc,
        )

    if gateway_active:
        logger.info(
            "webhook_skipped_gateway_active",
            extra={"meeting_id": meeting_id_for_log},
        )
        incr("webhook_processed_total")
        return {"accepted": True}

    payload = build_transcript_event_payload(
        meeting_id=str(meeting_id),
        text=text,
        speaker_id=speaker_id,
        speaker_name=speaker_name,
        timestamp=timestamp_str,
    )
    await redis_rpush(redis, TRANSCRIPT_EVENTS_QUEUE, json.dumps(payload))

    processing_ms = int(
        (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
    )
    logger.info(
        "webhook_processed",
        extra={
            "meeting_id": meeting_id_for_log,
            "event_type": body.get("type"),
            "processing_time_ms": processing_ms,
        },
    )
    if processing_ms > 2000:
        logger.warning(
            "webhook_slow",
            extra={
                "meeting_id": meeting_id_for_log,
                "event_type": body.get("type"),
                "processing_time_ms": processing_ms,
            },
        )
    incr("webhook_processed_total")
    incr("transcript_segments_received_total")
    return {"accepted": True}

