"""
WebSocket handler for live transcript streaming.

Clients connect with a JWT token and immediately receive the full transcript
history stored in Redis.  New segments published via the webhook are forwarded
in real-time over the same connection.
"""

import asyncio
import json
from urllib.parse import unquote
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect

from app.core.jwt import get_user_id_from_token
from app.modules.transcripts.broadcaster import _pub_channel
from app.modules.transcripts.service import get_live_transcript
from app.state.client import get_redis


WS_CLOSE_UNAUTHORIZED = 4401


def _get_token(websocket: WebSocket) -> str | None:
    raw = websocket.scope.get("query_string")
    if not raw:
        return None
    qs = raw.decode("utf-8") if isinstance(raw, bytes) else raw
    for part in qs.split("&"):
        if "=" in part:
            k, v = part.split("=", 1)
            if k.strip().lower() == "token":
                return unquote(v.strip())
    return None


async def transcript_websocket(websocket: WebSocket, meeting_id: UUID) -> None:
    await websocket.accept()

    token = _get_token(websocket)
    if not token:
        await websocket.close(code=WS_CLOSE_UNAUTHORIZED, reason="Missing token")
        return

    user_id = get_user_id_from_token(token)
    if not user_id:
        await websocket.close(code=WS_CLOSE_UNAUTHORIZED, reason="Invalid token")
        return

    try:
        redis = await get_redis()
    except Exception:
        await websocket.close(code=1011, reason="Service unavailable")
        return

    history = await get_live_transcript(redis, meeting_id)
    history_segments = [
        {"text": item, "speaker_id": None, "speaker": None, "timestamp": None}
        for item in history
    ]
    await websocket.send_text(
        json.dumps({"type": "history", "segments": history_segments})
    )

    pubsub = redis.pubsub()
    channel = _pub_channel(meeting_id)
    await pubsub.subscribe(channel)

    stop_event = asyncio.Event()

    async def _receive_loop() -> None:
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            stop_event.set()
        except Exception:
            stop_event.set()

    async def _broadcast_loop() -> None:
        try:
            while not stop_event.is_set():
                msg = await pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=0.1
                )
                if msg and msg.get("type") == "message":
                    try:
                        segment = json.loads(msg["data"])
                    except (json.JSONDecodeError, TypeError, KeyError):
                        continue
                    try:
                        await websocket.send_text(
                            json.dumps({"type": "transcript", "segment": segment})
                        )
                    except Exception:
                        stop_event.set()
                        break
        except Exception:
            stop_event.set()

    recv_task = asyncio.create_task(_receive_loop())
    bc_task = asyncio.create_task(_broadcast_loop())

    try:
        await asyncio.wait([recv_task, bc_task], return_when=asyncio.FIRST_COMPLETED)
    finally:
        recv_task.cancel()
        bc_task.cancel()
        try:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()
        except Exception:
            pass
