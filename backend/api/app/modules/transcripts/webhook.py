import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Header, Request, status

from app.core.metrics import incr
from app.modules.transcripts.webhooks import (
    handle_call_event,
    handle_transcript_event,
    verify_and_dedupe_webhook,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/stream/transcript", status_code=status.HTTP_200_OK)
async def stream_transcript_webhook(
    request: Request,
    x_signature: str | None = Header(default=None, alias="X-Signature"),
    x_api_key: str | None = Header(default=None, alias="X-API-KEY"),
) -> dict[str, Any]:
    start_time = datetime.now(timezone.utc)
    result = await verify_and_dedupe_webhook(request, x_signature, x_api_key)
    if result is None:
        return {"accepted": True}

    body, _event_id = result
    event_type = body.get("type")
    meeting_id_for_log: str | None = None

    if event_type == "call.closed_caption":
        return await handle_transcript_event(body, start_time)

    if event_type in {
        "call.member_added",
        "call.member_removed",
        "call.member_updated",
        "call.session_ended",
        "call.session_participant_joined",
        "call.session_participant_left",
    }:
        return await handle_call_event(body, request, start_time)

    processing_ms = int(
        (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
    )
    logger.info(
        "webhook_processed",
        extra={
            "meeting_id": meeting_id_for_log,
            "event_type": event_type,
            "processing_time_ms": processing_ms,
        },
    )
    if processing_ms > 2000:
        logger.warning(
            "webhook_slow",
            extra={
                "meeting_id": meeting_id_for_log,
                "event_type": event_type,
                "processing_time_ms": processing_ms,
            },
        )
    incr("webhook_processed_total")
    return {"accepted": True}
