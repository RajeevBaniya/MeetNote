import asyncio
import json
import logging
from urllib.parse import unquote
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect

from app.core.metrics import incr
from app.core.rate_limit import rate_limit_ws_for_user
from app.core.ws_message_rate_limiter import allow_ws_message
from app.modules.auth.ws_ticket import validate_ws_ticket
from app.modules.transcripts.broadcaster import _pub_channel
from app.modules.transcripts.service import (
    get_transcript_segments,
    has_user_left,
)
from app.state.client import get_redis

logger = logging.getLogger(__name__)

WS_CLOSE_UNAUTHORIZED = 4401


def _get_ticket_from_query(websocket: WebSocket) -> str | None:
    raw = websocket.scope.get("query_string")
    if not raw:
        return None
    qs = raw.decode("utf-8") if isinstance(raw, bytes) else raw
    for part in qs.split("&"):
        if "=" in part:
            k, v = part.split("=", 1)
            if k.strip().lower() == "ticket":
                return unquote(v.strip())
    return None


async def transcript_websocket(websocket: WebSocket, meeting_id: UUID) -> None:
    await websocket.accept()

    ticket = _get_ticket_from_query(websocket)
    if not ticket:
        await websocket.close(code=WS_CLOSE_UNAUTHORIZED, reason="Missing ticket")
        return

    user_id = await validate_ws_ticket(ticket)
    if not user_id:
        await websocket.close(code=WS_CLOSE_UNAUTHORIZED, reason="Invalid ticket")
        return
    registered = False
    client_ip = (
        websocket.client.host
        if websocket.client and websocket.client.host
        else "unknown"
    )

    allowed = await rate_limit_ws_for_user(user_id)
    if not allowed:
        await websocket.close(code=4408, reason="rate_limit_exceeded")
        return

    registered = True
    incr("active_ws_connections")

    try:
        try:
            redis = await get_redis()
        except Exception:
            await websocket.close(code=1011, reason="Service unavailable")
            return

        try:
            left = await has_user_left(redis, meeting_id, user_id)
        except Exception:
            await websocket.close(code=1011, reason="Service unavailable")
            return

        if left:
            await websocket.send_text(
                json.dumps({"type": "history", "segments": []})
            )
            incr("transcript_restore_requests_total")
            incr("transcript_user_blocked_total")
            try:
                while True:
                    await websocket.receive_text()
            except WebSocketDisconnect:
                return
            except Exception:
                logger.warning(
                    "transcript_blocked_ws_receive_error",
                    exc_info=True,
                )
                return

        history_items = await get_transcript_segments(redis, meeting_id)
        history_segments = [
            {
                "segment_id": item.get("segment_id"),
                "text": item.get("corrected_text") or item.get("text"),
                "original_text": item.get("text"),
                "speaker_id": item.get("speaker_id"),
                "speaker": item.get("speaker_name"),
                "timestamp": item.get("start_time"),
                "sequence": item.get("sequence"),
            }
            for item in history_items
        ]
        await websocket.send_text(
            json.dumps({"type": "history", "segments": history_segments})
        )
        incr("transcript_restore_requests_total")
        if history_segments:
            incr(
                "transcript_segments_streamed_total",
                amount=len(history_segments),
            )
            incr("transcript_segments_total", amount=len(history_segments))

        pubsub = redis.pubsub()
        channel = _pub_channel(meeting_id)
        user_channel = f"user_events:{user_id}"
        await pubsub.subscribe(channel, user_channel)

        stop_event = asyncio.Event()

        async def _receive_loop() -> None:
            try:
                while True:
                    # Only rate-limit client messages; server broadcasts are sent in broadcast loop.
                    await websocket.receive_text()
                    allowed = await allow_ws_message(user_id, client_ip)
                    if not allowed:
                        continue
            except WebSocketDisconnect:
                stop_event.set()
            except Exception:
                logger.warning(
                    "transcript_receive_loop_error",
                    exc_info=True,
                )
                stop_event.set()

        async def _broadcast_loop() -> None:
            try:
                while not stop_event.is_set():
                    msg = await pubsub.get_message(
                        ignore_subscribe_messages=True, timeout=0.01
                    )
                    if msg and msg.get("type") == "message":
                        try:
                            payload = json.loads(msg["data"])
                        except (json.JSONDecodeError, TypeError, KeyError):
                            continue
                        if payload.get("event") == "force_disconnect":
                            try:
                                await websocket.close(code=1008, reason="Session terminated")
                            except Exception:
                                pass
                            stop_event.set()
                            break
                        try:
                            if payload.get("type"):
                                await websocket.send_text(json.dumps(payload))
                            else:
                                await websocket.send_text(
                                    json.dumps(
                                        {"type": "transcript", "segment": payload}
                                    )
                                )
                            incr("transcript_segments_streamed_total")
                            incr("transcript_segments_total")
                        except Exception:
                            logger.warning(
                                "transcript_send_segment_failed",
                                exc_info=True,
                            )
                            stop_event.set()
                            break
            except Exception:
                logger.warning(
                    "transcript_broadcast_loop_error",
                    exc_info=True,
                )
                stop_event.set()

        recv_task = asyncio.create_task(_receive_loop())
        bc_task = asyncio.create_task(_broadcast_loop())

        try:
            await asyncio.wait(
                [recv_task, bc_task], return_when=asyncio.FIRST_COMPLETED
            )
        finally:
            recv_task.cancel()
            bc_task.cancel()
            try:
                await pubsub.unsubscribe(channel)
                await pubsub.aclose()
            except Exception:
                logger.warning(
                    "transcript_ws_cleanup_failed",
                    exc_info=True,
                )
    finally:
        if registered:
            incr("active_ws_connections", amount=-1)
