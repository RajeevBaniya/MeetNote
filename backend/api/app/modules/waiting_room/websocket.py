import json
from urllib.parse import unquote
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.jwt import get_user_id_from_token
from app.db.session import async_session_factory
from app.modules.meetings.service import get_meeting_by_id
from app.modules.waiting_room.service import (
    approve_user,
    get_pending_user_ids,
    reject_user,
)
from app.state.client import get_redis

router = APIRouter()

_connections_by_meeting: dict[UUID, list[WebSocket]] = {}


def _register_connection(meeting_id: UUID, websocket: WebSocket) -> None:
    if meeting_id not in _connections_by_meeting:
        _connections_by_meeting[meeting_id] = []
    _connections_by_meeting[meeting_id].append(websocket)


def _unregister_connection(meeting_id: UUID, websocket: WebSocket) -> None:
    if meeting_id not in _connections_by_meeting:
        return
    lst = _connections_by_meeting[meeting_id]
    if websocket in lst:
        lst.remove(websocket)
    if not lst:
        del _connections_by_meeting[meeting_id]


async def close_waiting_room_connections(meeting_id: UUID) -> None:
    if meeting_id not in _connections_by_meeting:
        return
    sockets = list(_connections_by_meeting.pop(meeting_id))
    for ws in sockets:
        try:
            await ws.close(code=1000)
        except Exception:
            pass


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


async def _send_json(websocket: WebSocket, obj: dict) -> None:
    await websocket.send_text(json.dumps(obj))


@router.websocket("/meetings/{meeting_id}/waiting-room")
async def waiting_room_websocket(websocket: WebSocket, meeting_id: UUID):
    await websocket.accept()
    token = _get_bearer_token(websocket)
    if not token:
        await websocket.close(code=1008)
        return
    user_id = get_user_id_from_token(token)
    if not user_id:
        await websocket.close(code=1008)
        return
    async with async_session_factory() as session:
        meeting = await get_meeting_by_id(session, meeting_id)
    if not meeting:
        await websocket.close(code=1008)
        return
    if meeting.host_id != user_id:
        await websocket.close(code=1008)
        return
    if not meeting.is_active:
        await websocket.close(code=1000)
        return
    _register_connection(meeting_id, websocket)
    try:
        redis = await get_redis()
    except Exception:
        _unregister_connection(meeting_id, websocket)
        try:
            await websocket.close(code=1011)
        except Exception:
            pass
        return
    try:
        pending = await get_pending_user_ids(redis, meeting_id)
        await _send_json(websocket, {"type": "pending_list", "user_ids": pending})
        while True:
            data = await websocket.receive_json()
            action = data.get("action")
            uid_str = data.get("user_id")
            if not uid_str:
                continue
            try:
                uid = UUID(uid_str)
            except (ValueError, TypeError):
                continue
            if action == "approve":
                await approve_user(redis, meeting_id, uid)
            elif action == "reject":
                await reject_user(redis, meeting_id, uid)
            else:
                continue
            pending = await get_pending_user_ids(redis, meeting_id)
            await _send_json(websocket, {"type": "pending_list", "user_ids": pending})
    except WebSocketDisconnect:
        pass
    except Exception:
        try:
            await websocket.close(code=1011)
        except Exception:
            pass
    finally:
        _unregister_connection(meeting_id, websocket)
