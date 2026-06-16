import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any
from urllib.parse import unquote
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect

from app.core.jwt import get_user_id_from_token
from app.core.rate_limit import rate_limit_ws_for_user
from app.core.ws_message_rate_limiter import allow_ws_message
from app.db.session import async_session_factory
from app.modules.chat.service import (
    append_message,
    get_recent_messages,
    get_user_display_name,
)
from app.modules.meetings.service import (
    ensure_host_consistency,
    get_meeting_by_id,
    restore_original_host_if_rejoined,
)
from app.modules.stream_tokens.service import is_user_removed
from app.state.client import get_redis
from app.core.metrics import incr
from app.core.dependencies import get_service
from app.core.interfaces import ChatServiceInterface

WS_CLOSE_UNAUTHORIZED = 4401
WS_CLOSE_FORBIDDEN = 4403
WS_CLOSE_MEETING_ENDED = 4400

_connections: dict[UUID, list[tuple[WebSocket, UUID]]] = {}


logger = logging.getLogger(__name__)


def _get_bearer_token(websocket: WebSocket) -> str | None:
    for name, value in websocket.scope.get("headers", []):
        n = name.decode("utf-8").lower() if isinstance(name, bytes) else name.lower()
        if n == "authorization":
            v = value.decode("utf-8") if isinstance(value, bytes) else value
            if v.lower().startswith("bearer "):
                return v[7:].strip()
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


def _register(meeting_id: UUID, websocket: WebSocket, user_id: UUID) -> None:
    if meeting_id not in _connections:
        _connections[meeting_id] = []
    _connections[meeting_id].append((websocket, user_id))


def _unregister(meeting_id: UUID, websocket: WebSocket) -> None:
    if meeting_id not in _connections:
        return
    lst = _connections[meeting_id]
    _connections[meeting_id] = [(ws, uid) for ws, uid in lst if ws != websocket]
    if not _connections[meeting_id]:
        del _connections[meeting_id]


async def _send_json(websocket: WebSocket, obj: dict[str, Any]) -> None:
    await websocket.send_text(json.dumps(obj))


class ChatSubscriptionManager:
    def __init__(self) -> None:
        self._tasks: dict[UUID, asyncio.Task[None]] = {}
        self._pubsubs: dict[UUID, Any] = {}
        self._locks: dict[UUID, asyncio.Lock] = {}

    async def register_client(self, meeting_id: UUID, websocket: WebSocket, user_id: UUID) -> None:
        lock = self._locks.setdefault(meeting_id, asyncio.Lock())
        async with lock:
            _register(meeting_id, websocket, user_id)
            if meeting_id not in self._tasks:
                try:
                    redis = await get_redis()
                    pubsub = redis.pubsub()
                    channel = f"chat:broadcast:{meeting_id}"
                    await pubsub.subscribe(channel)
                    self._pubsubs[meeting_id] = pubsub
                    self._tasks[meeting_id] = asyncio.create_task(
                        self._broadcast_loop(meeting_id, pubsub)
                    )
                    logger.info("Created shared Redis PubSub subscriber task for meeting %s", meeting_id)
                except Exception as exc:
                    logger.error("Failed to initialize PubSub subscriber for meeting %s: %s", meeting_id, exc, exc_info=exc)

    async def unregister_client(self, meeting_id: UUID, websocket: WebSocket) -> None:
        lock = self._locks.setdefault(meeting_id, asyncio.Lock())
        async with lock:
            _unregister(meeting_id, websocket)
            if meeting_id not in _connections or not _connections[meeting_id]:
                task = self._tasks.pop(meeting_id, None)
                if task:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                pubsub = self._pubsubs.pop(meeting_id, None)
                if pubsub:
                    try:
                        channel = f"chat:broadcast:{meeting_id}"
                        await pubsub.unsubscribe(channel)
                        await pubsub.aclose()
                        logger.info("Cleaned up shared Redis PubSub subscriber for meeting %s", meeting_id)
                    except Exception as exc:
                        logger.warning("Failed to close pubsub during cleanup for meeting %s: %s", meeting_id, exc)

    async def _broadcast_loop(self, meeting_id: UUID, pubsub: Any) -> None:
        channel = f"chat:broadcast:{meeting_id}"
        current_pubsub = pubsub
        while True:
            try:
                msg = await current_pubsub.get_message(ignore_subscribe_messages=True, timeout=0.01)
                if msg and msg.get("type") == "message":
                    try:
                        data = json.loads(msg["data"])
                    except Exception:
                        continue

                    event = data.get("event")
                    payload = data.get("payload")

                    if event == "chat_message":
                        for ws, _ in _connections.get(meeting_id, []):
                            try:
                                await _send_json(ws, payload)
                            except Exception:
                                pass
                    elif event == "host_changed":
                        for ws, _ in _connections.get(meeting_id, []):
                            try:
                                await _send_json(ws, payload)
                            except Exception:
                                pass
                    elif event == "close_connections":
                        sockets = list(_connections.get(meeting_id, []))
                        for ws, _ in sockets:
                            try:
                                await ws.close(code=WS_CLOSE_MEETING_ENDED, reason="Meeting ended")
                            except Exception:
                                pass
                    elif event == "close_connections_for_user":
                        target_user_id = payload.get("user_id") if payload else None
                        if target_user_id:
                            user_sockets = [ws for ws, uid in _connections.get(meeting_id, []) if str(uid) == str(target_user_id)]
                            for ws in user_sockets:
                                try:
                                    await ws.close(code=WS_CLOSE_FORBIDDEN, reason="You were removed from this meeting")
                                except Exception:
                                    pass
                await asyncio.sleep(0.01)
            except asyncio.CancelledError:
                logger.info("Chat broadcast loop cancelled for meeting %s", meeting_id)
                break
            except Exception as exc:
                logger.error("Exception in chat broadcast loop for meeting %s: %s. Reconnecting pubsub...", meeting_id, exc)
                try:
                    await current_pubsub.aclose()
                except Exception:
                    pass
                await asyncio.sleep(1.0)
                try:
                    redis = await get_redis()
                    current_pubsub = redis.pubsub()
                    await current_pubsub.subscribe(channel)
                    self._pubsubs[meeting_id] = current_pubsub
                    logger.info("Successfully re-subscribed to channel %s", channel)
                except Exception as reconnect_exc:
                    logger.error("Failed to re-subscribe to channel %s: %s", channel, reconnect_exc)


subscription_manager = ChatSubscriptionManager()


async def close_chat_connections(meeting_id: UUID) -> None:
    try:
        redis = await get_redis()
        payload = {
            "event": "close_connections",
            "payload": {}
        }
        await redis.publish(f"chat:broadcast:{meeting_id}", json.dumps(payload))
        logger.info("Published close_connections event to Redis for meeting %s", meeting_id)
    except Exception as exc:
        logger.error("Failed to publish close_connections event to Redis for meeting %s: %s", meeting_id, exc)


try:
    get_service(ChatServiceInterface).register_close_handler(close_chat_connections)  # type: ignore[type-abstract]
except Exception as err:
    logger.warning("Failed to register close_chat_connections handler: %s", err)


async def close_chat_connections_for_user(meeting_id: UUID, user_id: UUID) -> None:
    try:
        redis = await get_redis()
        payload = {
            "event": "close_connections_for_user",
            "payload": {"user_id": str(user_id)}
        }
        await redis.publish(f"chat:broadcast:{meeting_id}", json.dumps(payload))
        logger.info("Published close_connections_for_user event to Redis for meeting %s, user %s", meeting_id, user_id)
    except Exception as exc:
        logger.error("Failed to publish close_connections_for_user event to Redis for meeting %s, user %s: %s", meeting_id, user_id, exc)


async def broadcast_host_changed(meeting_id: UUID, new_host_id: UUID) -> None:
    try:
        redis = await get_redis()
        # 1. Update host cache key in Redis
        await redis.set(f"meeting:host_id:{meeting_id}", str(new_host_id))
        
        # 2. Clear pending_q and ext_approved to prevent approval leakage
        await redis.delete(
            f"assistant:pending_q:{meeting_id}",
            f"assistant:ext_approved:{meeting_id}"
        )
        
        # 3. Broadcast to client chat socket
        payload = {
            "event": "host_changed",
            "payload": {"type": "host_changed", "new_host_id": str(new_host_id)}
        }
        await redis.publish(f"chat:broadcast:{meeting_id}", json.dumps(payload))
        
        # 4. Publish transfer event to agent channel
        transfer_payload = {
            "meeting_id": str(meeting_id),
            "new_host_id": str(new_host_id)
        }
        await redis.publish("meeting:host_transfer", json.dumps(transfer_payload))
        
        logger.info("Published host_changed event to Redis for meeting %s, new host %s", meeting_id, new_host_id)
    except Exception as exc:
        logger.error("Failed to publish host_changed event to Redis for meeting %s: %s", meeting_id, exc)


async def chat_websocket(websocket: WebSocket, meeting_id: UUID) -> None:
    await websocket.accept()
    token = _get_bearer_token(websocket)
    if not token:
        await websocket.close(code=WS_CLOSE_UNAUTHORIZED, reason="Missing or invalid token")
        return
    user_id = get_user_id_from_token(token)
    if not user_id:
        await websocket.close(code=WS_CLOSE_UNAUTHORIZED, reason="Invalid or expired token")
        return
    client_ip = (
        websocket.client.host
        if websocket.client and websocket.client.host
        else "unknown"
    )
    allowed = await rate_limit_ws_for_user(user_id)
    if not allowed:
        await websocket.close(code=4408, reason="rate_limit_exceeded")
        return
    async with async_session_factory() as session:
        meeting = await get_meeting_by_id(session, meeting_id)
    if not meeting:
        await websocket.close(code=WS_CLOSE_FORBIDDEN, reason="Meeting not found")
        return
    if not meeting.is_active:
        await websocket.close(code=WS_CLOSE_MEETING_ENDED, reason="Meeting ended")
        return
    try:
        redis = await get_redis()
    except Exception as exc:
        logger.warning(
            "ws_redis_unavailable",
            extra={"meeting_id": str(meeting_id), "user_id": str(user_id)},
            exc_info=exc,
        )
        await websocket.close(code=1011, reason="Service unavailable")
        return
    removed = await is_user_removed(redis, meeting_id, user_id)
    if removed:
        await websocket.close(code=WS_CLOSE_FORBIDDEN, reason="You were removed from this meeting")
        return
    registered = False

    initial_host_id = meeting.current_host_id
    try:
        guard_key = f"host_consistency_guard:{meeting_id}"
        got_guard = await redis.set(guard_key, "1", ex=3, nx=True)
        if got_guard:
            new_host = await ensure_host_consistency(meeting_id)
            if new_host is not None:
                initial_host_id = new_host
                await broadcast_host_changed(meeting_id, new_host)
    except Exception as exc:
        logger.error(
            "ensure_host_consistency_failed",
            extra={"meeting_id": str(meeting_id)},
            exc_info=exc,
        )
    incr("ws_connected_total")
    logger.info(
        "ws_connected",
        extra={"meeting_id": str(meeting_id), "user_id": str(user_id)},
    )
    try:
        restored = await restore_original_host_if_rejoined(meeting_id, user_id)
        if restored is not None:
            initial_host_id = restored
            await broadcast_host_changed(meeting_id, restored)
    except Exception:
        logger.warning("restore_original_host_failed", exc_info=True)

    await subscription_manager.register_client(meeting_id, websocket, user_id)
    registered = True
    incr("active_ws_connections")
    try:
        recent = await get_recent_messages(redis, meeting_id)
        await _send_json(websocket, {"type": "history", "messages": recent})
        await _send_json(
            websocket,
            {"type": "initial_state", "current_host_id": str(initial_host_id)},
        )
        while True:
            data = await websocket.receive_json()
            if data.get("type") != "message":
                continue
            text = (data.get("text") or "").strip()
            if not text:
                continue
            allowed = await allow_ws_message(user_id, client_ip)
            if not allowed:
                continue
            display_name = await get_user_display_name(user_id)
            ts = datetime.now(timezone.utc).isoformat()
            client_id = data.get("client_id")
            
            await append_message(redis, meeting_id, user_id, display_name, ts, text)
            incr("chat_messages_total")
            
            payload = {
                "type": "chat_message",
                "user_id": str(user_id),
                "display_name": display_name,
                "timestamp": ts,
                "text": text,
            }
            if client_id:
                payload["client_id"] = str(client_id)
                
            pub_data = {
                "event": "chat_message",
                "payload": payload
            }
            await redis.publish(f"chat:broadcast:{meeting_id}", json.dumps(pub_data))
    except WebSocketDisconnect:
        logger.info(
            "ws_disconnected",
            extra={"meeting_id": str(meeting_id), "user_id": str(user_id)},
        )
    except Exception:
        logger.exception("chat_websocket_error")
        try:
            await websocket.close(code=1011)
        except Exception:
            logger.warning("ws_close_on_error_failed", exc_info=True)
    finally:
        if registered:
            incr("active_ws_connections", amount=-1)
        await subscription_manager.unregister_client(meeting_id, websocket)
