import json
import logging
from typing import Any
from uuid import UUID

import httpx
from getstream import Stream
from getstream.models import UserRequest
from redis.asyncio import Redis

from app.core.config import (
    STREAM_API_KEY,
    STREAM_API_SECRET,
    STREAM_TOKEN_EXPIRY_SECONDS,
)

logger = logging.getLogger(__name__)
STREAM_VIDEO_BASE = "https://video.stream-io-api.com/api/v2/video"


def _removed_users_key(meeting_id: UUID) -> str:
    return f"meeting:{meeting_id}:removed_users"


async def add_removed_user(redis: Redis, meeting_id: UUID, user_id: UUID) -> None:
    key = _removed_users_key(meeting_id)
    await redis.sadd(key, str(user_id))


async def is_user_removed(redis: Redis, meeting_id: UUID, user_id: UUID) -> bool:
    key = _removed_users_key(meeting_id)
    return bool(await redis.sismember(key, str(user_id)))


def create_stream_token(user_id: UUID, name: str | None = None) -> str:
    api_key = STREAM_API_KEY
    api_secret = STREAM_API_SECRET
    client = Stream(api_key=api_key, api_secret=api_secret)
    uid = str(user_id)
    user_request = UserRequest(
        id=uid,
        role="user",
        name=name or uid,
    )
    client.upsert_users(user_request)
    token = client.create_token(uid, expiration=STREAM_TOKEN_EXPIRY_SECONDS)
    return str(token)


def _create_server_token(user_id: UUID, expiration_seconds: int = 60) -> str:
    api_key = STREAM_API_KEY
    api_secret = STREAM_API_SECRET
    client = Stream(api_key=api_key, api_secret=api_secret)
    return str(client.create_token(str(user_id), expiration=expiration_seconds))


async def end_stream_call(call_type: str, call_id: str, host_user_id: UUID) -> None:
    api_key = STREAM_API_KEY
    token = _create_server_token(host_user_id)
    url = f"{STREAM_VIDEO_BASE}/call/{call_type}/{call_id}/mark_ended"
    params = {"api_key": api_key}
    headers = {
        "Authorization": f"Bearer {token}",
        "stream-auth-type": "jwt",
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(url, params=params, headers=headers)
        if resp.status_code >= 400:
            logger.warning(
                "stream_mark_ended_failed",
                extra={"call_id": call_id, "status": resp.status_code, "body": resp.text},
            )
            raise RuntimeError("Failed to end Stream call")


async def kick_stream_user(
    call_type: str,
    call_id: str,
    host_user_id: UUID,
    target_user_id: UUID,
) -> None:
    api_key = STREAM_API_KEY
    token = _create_server_token(host_user_id)
    url = f"{STREAM_VIDEO_BASE}/call/{call_type}/{call_id}/kick"
    params = {"api_key": api_key}
    headers = {
        "Authorization": f"Bearer {token}",
        "stream-auth-type": "jwt",
        "Content-Type": "application/json",
    }
    payload = {"user_id": str(target_user_id)}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(url, params=params, headers=headers, json=payload)
        if resp.status_code >= 400:
            logger.warning(
                "stream_kick_failed",
                extra={
                    "call_id": call_id,
                    "target_user_id": str(target_user_id),
                    "status": resp.status_code,
                    "body": resp.text,
                },
            )
            return


async def mute_stream_user(
    call_type: str,
    call_id: str,
    host_user_id: UUID,
    target_user_id: UUID,
) -> None:
    api_key = STREAM_API_KEY
    token = _create_server_token(host_user_id)
    url = f"{STREAM_VIDEO_BASE}/call/{call_type}/{call_id}/mute_users"
    params = {"api_key": api_key}
    headers = {
        "Authorization": f"Bearer {token}",
        "stream-auth-type": "jwt",
        "Content-Type": "application/json",
    }
    payload = {
        "user_ids": [str(target_user_id)],
        "audio": True,
        "muted_by_id": str(host_user_id),
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(url, params=params, headers=headers, json=payload)
        if resp.status_code >= 400:
            logger.warning(
                "stream_mute_failed",
                extra={
                    "call_id": call_id,
                    "target_user_id": str(target_user_id),
                    "status": resp.status_code,
                    "body": resp.text,
                },
            )
            raise RuntimeError("Failed to mute participant in Stream call")


async def list_stream_transcriptions(
    call_type: str,
    call_id: str,
    user_id: UUID,
) -> list[dict[str, Any]]:
    api_key = STREAM_API_KEY
    token = _create_server_token(user_id)
    url = f"{STREAM_VIDEO_BASE}/call/{call_type}/{call_id}/transcriptions"
    params = {"api_key": api_key}
    headers = {
        "Authorization": f"Bearer {token}",
        "stream-auth-type": "jwt",
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, params=params, headers=headers)
        if resp.status_code >= 400:
            logger.warning(
                "stream_list_transcriptions_failed",
                extra={
                    "call_id": call_id,
                    "status": resp.status_code,
                    "body": resp.text,
                },
            )
            return []
        data = resp.json()
        items_data: Any = None
        if isinstance(data, list):
            items_data = data
        else:
            items_data = data.get("transcriptions") if isinstance(data, dict) else None
        if not isinstance(items_data, list):
            return []
        out: list[dict[str, Any]] = []
        for r in items_data:
            if not isinstance(r, dict):
                continue
            url_val = r.get("url")
            if not url_val or not isinstance(url_val, str):
                continue
            out.append(
                {
                    "url": url_val,
                    "filename": r.get("filename") or "transcript.jsonl",
                    "start_time": r.get("start_time") or "",
                    "end_time": r.get("end_time") or "",
                    "session_id": r.get("session_id") or "",
                }
            )
        return out


async def get_stream_transcript_segments(
    call_type: str,
    call_id: str,
    user_id: UUID,
) -> list[dict[str, Any]]:
    items = await list_stream_transcriptions(call_type, call_id, user_id)
    if not items:
        return []
    first = items[0]
    url = first.get("url")
    if not url or not isinstance(url, str):
        return []
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(url)
        if resp.status_code >= 400:
            logger.warning(
                "stream_fetch_transcript_failed",
                extra={
                    "call_id": call_id,
                    "status": resp.status_code,
                    "body": resp.text,
                },
            )
            return []
        text = resp.text
    segments: list[dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except Exception:
            continue  # skip malformed JSON line from transcript response
        if not isinstance(data, dict):
            continue
        if data.get("type") != "speech":
            continue
        segments.append(
            {
                "type": data.get("type") or "",
                "start_time": data.get("start_time") or "",
                "stop_time": data.get("stop_time") or "",
                "speaker_id": data.get("speaker_id"),
                "text": data.get("text") or "",
            }
        )
    return segments


async def query_stream_call_members(
    call_type: str,
    call_id: str,
    acting_user_id: UUID,
) -> list[dict[str, Any]]:
    api_key = STREAM_API_KEY
    token = _create_server_token(acting_user_id)
    url = f"{STREAM_VIDEO_BASE}/call/members"
    params = {"api_key": api_key}
    headers = {
        "Authorization": f"Bearer {token}",
        "stream-auth-type": "jwt",
        "Content-Type": "application/json",
    }
    payload = {
        "id": call_id,
        "type": call_type,
        "limit": 100,
        "sort": [{"field": "created_at", "direction": 1}],
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(url, params=params, headers=headers, json=payload)
        if resp.status_code >= 400:
            logger.warning(
                "stream_query_call_members_failed",
                extra={"call_id": call_id, "status": resp.status_code, "body": resp.text},
            )
            return []
        data = resp.json()
    members = data.get("members") if isinstance(data, dict) else None
    if not isinstance(members, list):
        return []
    out: list[dict[str, Any]] = []
    for m in members:
        if not isinstance(m, dict):
            continue
        user = m.get("user")
        if not isinstance(user, dict):
            user = {}
        uid = user.get("id") or m.get("user_id")
        if not uid or not isinstance(uid, str):
            continue
        name = user.get("name") if isinstance(user.get("name"), str) else None
        joined_at = m.get("created_at") or user.get("created_at")
        out.append(
            {
                "user_id": uid,
                "name": name,
                "joined_at": str(joined_at) if joined_at is not None else "",
            }
        )
    return out
