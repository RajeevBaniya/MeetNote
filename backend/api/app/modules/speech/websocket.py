import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Optional, Any
from collections import deque
from urllib.parse import unquote
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect

from app.db.session import async_session_factory
from app.modules.auth.service import get_user_by_id
from app.modules.auth.ws_ticket import validate_ws_ticket
from app.modules.speech.provider_manager import ProviderManager
from app.modules.speech.providers import BaseSpeechProvider, TranscriptionResult
from app.modules.transcripts.transcript_event_payload import (
    TRANSCRIPT_EVENTS_QUEUE,
    build_transcript_event_payload,
)
from app.state.client import get_redis
from app.state.redis_client import redis_rpush

logger = logging.getLogger(__name__)

WS_CLOSE_UNAUTHORIZED = 4401
WS_CLOSE_SERVER_ERROR = 1011
IDLE_TIMEOUT_SECONDS = 60.0  # Close connection if no audio received for 1 minute


class AudioBuffer:
    """Rolling memory buffer to store recent audio chunks for replay during failover."""

    def __init__(self, max_age_seconds: float = 5.0) -> None:
        self._buffer = deque()  # stores tuples of (timestamp, chunk)
        self.max_age_seconds = max_age_seconds

    def push(self, chunk: bytes) -> None:
        now = time.time()
        self._buffer.append((now, chunk))
        self.prune()

    def prune(self) -> None:
        now = time.time()
        cutoff = now - self.max_age_seconds
        while self._buffer and self._buffer[0][0] < cutoff:
            self._buffer.popleft()

    def get_all_chunks(self) -> bytes:
        return b"".join(chunk for _, chunk in self._buffer)


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


async def _resolve_user_name(user_id: UUID) -> str:
    """Look up the user's display name from the database. Falls back to 'Participant'."""
    try:
        async with async_session_factory() as session:
            user = await get_user_by_id(session, user_id)
            if user and user.name:
                return user.name
    except Exception as exc:
        logger.warning("Failed to resolve speaker name for user_id=%s", user_id, exc_info=exc)
    return "Participant"


def _resolve_provider_timestamp(result: TranscriptionResult) -> str:
    """Convert provider timestamps to ISO-8601 strings for pipeline compatibility."""
    ts = result.end_time or result.start_time
    if ts is not None:
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
    return datetime.now(timezone.utc).isoformat()


async def _push_to_transcript_pipeline(
    meeting_id: UUID,
    text: str,
    speaker_id: str,
    speaker_name: str,
    result: TranscriptionResult,
) -> None:
    """Push a final transcription to the transcript_events queue for downstream processing."""
    try:
        timestamp_str = _resolve_provider_timestamp(result)
        event_payload = build_transcript_event_payload(
            meeting_id=str(meeting_id),
            text=text,
            speaker_id=speaker_id,
            speaker_name=speaker_name,
            timestamp=timestamp_str,
            confidence=result.confidence,
        )
        redis = await get_redis()
        await redis_rpush(redis, TRANSCRIPT_EVENTS_QUEUE, json.dumps(event_payload))
    except Exception as exc:
        logger.warning("Failed to push transcription to pipeline: %s", exc)


async def _incr_gateway_counter(redis: Any, meeting_id: UUID) -> None:
    count_key = f"speech:meeting:{meeting_id}:active_gateway_count"
    active_key = f"speech:meeting:{meeting_id}:gateway_active"
    count = await redis.incr(count_key)
    await redis.expire(count_key, 28800)
    if count == 1:
        await redis.set(active_key, "1", ex=28800)
        logger.info("Speech Gateway marked ACTIVE for meeting_id=%s", meeting_id)
    else:
        await redis.expire(active_key, 28800)


async def _decr_gateway_counter(redis: Any, meeting_id: UUID) -> None:
    count_key = f"speech:meeting:{meeting_id}:active_gateway_count"
    active_key = f"speech:meeting:{meeting_id}:gateway_active"
    count = await redis.decr(count_key)
    if count <= 0:
        await redis.delete(count_key)
        await redis.delete(active_key)
        logger.info("Speech Gateway marked INACTIVE for meeting_id=%s", meeting_id)
    else:
        await redis.expire(count_key, 28800)
        await redis.expire(active_key, 28800)


async def speech_gateway_websocket(websocket: WebSocket, meeting_id: UUID) -> None:
    """WebSocket endpoint for raw audio streaming, dynamic failover, and transcription routing."""
    await websocket.accept()

    ticket = _get_ticket_from_query(websocket)
    if not ticket:
        await websocket.close(code=WS_CLOSE_UNAUTHORIZED, reason="Missing ticket")
        return

    user_id = await validate_ws_ticket(ticket)
    if not user_id:
        await websocket.close(code=WS_CLOSE_UNAUTHORIZED, reason="Invalid ticket")
        return

    session_id = f"{meeting_id}:{user_id}"
    manager = ProviderManager()
    audio_buffer = AudioBuffer(max_age_seconds=5.0)

    counter_incremented = False
    try:
        provider = await manager.allocate_provider(session_id)
        user_name = await _resolve_user_name(user_id)
        await provider.connect(session_id=session_id, user_id=str(user_id), user_name=user_name)
        if provider.name != "GetStream":
            redis = await get_redis()
            await _incr_gateway_counter(redis, meeting_id)
            counter_incremented = True
    except Exception as exc:
        logger.exception("Failed to allocate initial speech provider for session=%s", session_id)
        await websocket.close(code=WS_CLOSE_SERVER_ERROR, reason="Initial provider allocation failed")
        return

    # Background task to poll transcriptions from the active provider
    receive_task: Optional[asyncio.Task] = None
    last_activity_time = time.time()

    async def _handle_provider_switch(new_provider: BaseSpeechProvider):
        nonlocal provider, counter_incremented
        provider = new_provider
        await provider.connect(session_id=session_id, user_id=str(user_id), user_name=user_name)
        if provider.name == "GetStream" and counter_incremented:
            try:
                redis_client = await get_redis()
                await _decr_gateway_counter(redis_client, meeting_id)
                counter_incremented = False
            except Exception as switch_exc:
                logger.warning("Failed to decrement gateway counter on GetStream fallback", exc_info=switch_exc)

    async def provider_receive_loop():
        nonlocal provider
        try:
            while True:
                try:
                    res = await provider.receive_transcription()
                    if res:
                        resolved_speaker_id = res.speaker_id or str(user_id)
                        resolved_speaker_name = res.speaker_name or user_name

                        await websocket.send_json({
                            "type": "transcription",
                            "text": res.text,
                            "speaker_id": resolved_speaker_id,
                            "speaker_name": resolved_speaker_name,
                            "is_final": res.is_final,
                        })

                        if res.is_final and res.text.strip():
                            await _push_to_transcript_pipeline(
                                meeting_id=meeting_id,
                                text=res.text,
                                speaker_id=resolved_speaker_id,
                                speaker_name=resolved_speaker_name,
                                result=res,
                            )
                except Exception as loop_exc:
                    logger.warning("Provider receive error, triggering failover: %s", loop_exc)
                    # Trigger failover transition
                    new_p = await manager.fail_provider(session_id)
                    await _handle_provider_switch(new_p)
                    # Replay rolling audio buffer
                    replay_audio = audio_buffer.get_all_chunks()
                    if replay_audio:
                        await provider.send_audio_chunk(replay_audio)
                await asyncio.sleep(0.05)
        except asyncio.CancelledError:
            pass

    receive_task = asyncio.create_task(provider_receive_loop())

    try:
        while True:
            # Idle timeout monitor
            if time.time() - last_activity_time > IDLE_TIMEOUT_SECONDS:
                logger.warning("Speech gateway connection idle timeout for session=%s", session_id)
                break

            # Accept binary frame audio chunk or text heartbeat
            message = await websocket.receive()

            if message.get("type") == "websocket.disconnect":
                break

            if "bytes" in message:
                last_activity_time = time.time()
                chunk = message["bytes"]
                if not chunk:
                    continue

                audio_buffer.push(chunk)

                # Send chunk to active provider, handle failover transparently
                try:
                    await provider.send_audio_chunk(chunk)
                except Exception as send_exc:
                    logger.warning("Failed to send chunk to provider, failing over: %s", send_exc)
                    # Cancel existing loop to prevent race conditions
                    if receive_task:
                        receive_task.cancel()
                        await asyncio.gather(receive_task, return_exceptions=True)

                    # Trigger failover
                    new_p = await manager.fail_provider(session_id)
                    await _handle_provider_switch(new_p)

                    # Replay audio buffer
                    replay_audio = audio_buffer.get_all_chunks()
                    if replay_audio:
                        await provider.send_audio_chunk(replay_audio)

                    # Restart receive loop
                    receive_task = asyncio.create_task(provider_receive_loop())

            elif "text" in message:
                last_activity_time = time.time()
                text_data = message["text"]
                # Parse text client commands (e.g., custom heartbeats or pings)
                try:
                    data = json.loads(text_data)
                    if data.get("type") == "ping":
                        await websocket.send_json({"type": "pong"})
                except json.JSONDecodeError:
                    pass

    except WebSocketDisconnect:
        logger.info("Speech gateway WebSocket disconnected for session=%s", session_id)
    except Exception as exc:
        logger.exception("Error in speech gateway WebSocket loop for session=%s", session_id)
    finally:
        # Graceful cleanup
        if receive_task:
            receive_task.cancel()
            await asyncio.gather(receive_task, return_exceptions=True)

        try:
            await provider.close()
        except Exception:
            pass

        await manager.release_provider(session_id)

        if counter_incremented:
            try:
                redis_client = await get_redis()
                await _decr_gateway_counter(redis_client, meeting_id)
            except Exception as decr_exc:
                logger.warning("Failed to decrement active gateway counter on cleanup", exc_info=decr_exc)
