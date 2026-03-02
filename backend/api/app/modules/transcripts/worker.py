import asyncio
import hashlib
import json
import logging
from typing import Any
from uuid import UUID

from redis.asyncio import Redis
from app.modules.analytics.service import add_speaking_time
from app.modules.transcripts.service import append_transcript_segment
from app.state.client import get_redis
from app.core.metrics import incr


logger = logging.getLogger(__name__)

EVENT_QUEUE_KEY = "transcript_events"


async def _get_redis_client() -> Redis:
  return await get_redis()


async def run_transcript_worker() -> None:
  """
  Long-running task that blocks on BRPOP and processes transcript events.
  """
  while True:
    try:
      redis = await _get_redis_client()
      break
    except Exception:
      logger.exception("transcript_worker_redis_connect_failed")
      await asyncio.sleep(5)

  while True:
    try:
      item = await redis.brpop(EVENT_QUEUE_KEY, timeout=5)
      if not item:
        continue
      _, raw = item
      try:
        payload: dict[str, Any] = json.loads(raw)
      except Exception:
        logger.warning("transcript_worker_invalid_payload")
        continue

      meeting_id_raw = payload.get("meeting_id")
      text = payload.get("text") or ""
      speaker_id = payload.get("speaker_id")
      speaker_name = payload.get("speaker_name")
      timestamp = payload.get("timestamp")

      try:
        meeting_id = UUID(str(meeting_id_raw))
      except Exception:
        logger.warning("transcript_worker_invalid_meeting_id payload=%s", payload)
        continue

      await append_transcript_segment(
        redis,
        meeting_id,
        text,
        speaker_id=speaker_id,
        speaker_name=speaker_name,
        timestamp=timestamp,
      )
      incr("transcript_chunks_processed_total")
      if speaker_id and text.strip():
        segment_hash = hashlib.sha256(
          f"{meeting_id}|{speaker_id}|{text}|{timestamp or ''}".encode()
        ).hexdigest()
        key = f"analytics_segment_seen:{meeting_id}:{segment_hash}"
        if await redis.set(key, "1", ex=7200, nx=True):
          try:
            user_id = UUID(str(speaker_id))
            word_count = len(text.strip().split())
            await add_speaking_time(meeting_id, user_id, word_count)
          except (ValueError, TypeError):
            pass
    except asyncio.CancelledError:
      break
    except Exception:
      logger.exception("transcript_worker_loop_error")
      await asyncio.sleep(1)

