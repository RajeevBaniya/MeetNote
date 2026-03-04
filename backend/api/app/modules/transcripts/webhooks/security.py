import hashlib
import hmac
import json
import logging
from typing import Any, Dict, Tuple

from fastapi import HTTPException, Request, status

from app.core.config import get_stream_api_key, get_stream_webhook_secret
from app.core.metrics import incr
from app.state.client import get_redis

logger = logging.getLogger(__name__)


async def verify_and_dedupe_webhook(
    request: Request,
    x_signature: str | None,
    x_api_key: str | None,
) -> Tuple[Dict[str, Any], str] | None:
    incr("webhook_received_total")

    if not x_signature or not x_api_key:
        incr("webhook_rejected_signature_total")
        logger.warning("webhook_missing_auth_headers")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )

    expected_api_key = get_stream_api_key()
    if x_api_key != expected_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )

    raw_body = await request.body()
    secret = get_stream_webhook_secret().encode("utf-8")
    computed = hmac.new(secret, raw_body, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed, x_signature):
        incr("webhook_rejected_signature_total")
        logger.warning("webhook_invalid_signature")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )

    event_id_str: str | None = None
    header_event_id = request.headers.get("X-WEBHOOK-ID")
    if isinstance(header_event_id, str):
        trimmed = header_event_id.strip()
        if trimmed:
            event_id_str = trimmed

    try:
        body = json.loads(raw_body.decode("utf-8"))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON body",
        )

    if not isinstance(body, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Expected JSON object",
        )

    if event_id_str is None:
        body_event_id = body.get("id") or body.get("event_id")
        if isinstance(body_event_id, str):
            trimmed = body_event_id.strip()
            if trimmed:
                event_id_str = trimmed

    if event_id_str is None:
        logger.warning("webhook_missing_event_id")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook",
        )

    try:
        redis_client = await get_redis()
    except Exception as exc:
        incr("webhook_failures_total")
        logger.warning(
            "webhook_dedupe_redis_unavailable",
            extra={"event_id": event_id_str},
            exc_info=exc,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable",
        )

    dedupe_key = f"webhook:event:{event_id_str}"
    try:
        is_first = await redis_client.set(dedupe_key, "1", ex=86400, nx=True)
    except Exception as exc:
        incr("webhook_failures_total")
        logger.warning(
            "webhook_dedupe_redis_error",
            extra={"event_id": event_id_str},
            exc_info=exc,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable",
        )

    if not is_first:
        incr("webhook_duplicate_total")
        logger.info(
            "webhook_duplicate",
            extra={
                "event_id": event_id_str,
                "event_type": body.get("type"),
            },
        )
        return None

    return body, event_id_str

