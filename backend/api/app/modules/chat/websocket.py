import json
from datetime import datetime, timezone
from urllib.parse import unquote
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect

from app.core.jwt import get_user_id_from_token
from app.db.session import async_session_factory
from app.modules.chat.service import (
    append_message,
    get_recent_messages,
    get_user_display_name,
)
from app.modules.meetings.service import get_meeting_by_id
from app.modules.stream_tokens.service import is_user_removed
from app.state.client import get_redis

WS_CLOSE_UNAUTHORIZED = 4401
WS_CLOSE_FORBIDDEN = 4403
WS_CLOSE_MEETING_ENDED = 4400

_connections: dict[UUID, list[tuple[WebSocket, UUID]]] = {}


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


async def close_chat_connections(meeting_id: UUID) -> None:
    if meeting_id not in _connections:
        return
    sockets = list(_connections.pop(meeting_id))
    for ws, _ in sockets:
        try:
            await ws.close(code=WS_CLOSE_MEETING_ENDED, reason="Meeting ended")
        except Exception:
            pass


async def close_chat_connections_for_user(meeting_id: UUID, user_id: UUID) -> None:
    if meeting_id not in _connections:
        return
    sockets: list[WebSocket] = []
    remaining: list[tuple[WebSocket, UUID]] = []
    for ws, uid in _connections[meeting_id]:
        if uid == user_id:
            sockets.append(ws)
        else:
            remaining.append((ws, uid))
    if remaining:
        _connections[meeting_id] = remaining
    else:
        del _connections[meeting_id]
    for ws in sockets:
        try:
            await ws.close(
                code=WS_CLOSE_FORBIDDEN,
                reason="You were removed from this meeting",
            )
        except Exception:
            pass


async def _send_json(websocket: WebSocket, obj: dict) -> None:
    await websocket.send_text(json.dumps(obj))


async def chat_websocket(websocket: WebSocket, meeting_id: UUID):
    await websocket.accept()
    token = _get_bearer_token(websocket)
    if not token:
        await websocket.close(code=WS_CLOSE_UNAUTHORIZED, reason="Missing or invalid token")
        return
    user_id = get_user_id_from_token(token)
    if not user_id:
        await websocket.close(code=WS_CLOSE_UNAUTHORIZED, reason="Invalid or expired token")
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
    except Exception:
        await websocket.close(code=1011, reason="Service unavailable")
        return
    removed = await is_user_removed(redis, meeting_id, user_id)
    if removed:
        await websocket.close(code=WS_CLOSE_FORBIDDEN, reason="You were removed from this meeting")
        return
    _register(meeting_id, websocket, user_id)
    try:
        recent = await get_recent_messages(redis, meeting_id)
        await _send_json(websocket, {"type": "history", "messages": recent})
        while True:
            data = await websocket.receive_json()
            if data.get("type") != "message":
                continue
            text = (data.get("text") or "").strip()
            if not text:
                continue
            display_name = await get_user_display_name(user_id)
            ts = datetime.now(timezone.utc).isoformat()
            payload = {
                "type": "chat_message",
                "user_id": str(user_id),
                "display_name": display_name,
                "timestamp": ts,
                "text": text,
            }
            await append_message(redis, meeting_id, user_id, display_name, ts, text)
            for ws, _ in _connections.get(meeting_id, []):
                try:
                    await _send_json(ws, payload)
                except Exception:
                    pass
    except WebSocketDisconnect:
        pass
    except Exception:
        try:
            await websocket.close(code=1011)
        except Exception:
            pass
    finally:
        _unregister(meeting_id, websocket)
