import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

TRANSCRIPT_EVENTS_QUEUE = "transcript_events"


def build_transcript_event_payload(
    meeting_id: str,
    text: str,
    speaker_id: str | None,
    speaker_name: str | None,
    timestamp: str | None,
    confidence: float | None = None,
) -> dict[str, Any]:
    """Build the canonical payload for the transcript_events Redis queue.

    Both the GetStream webhook path and the Speech Gateway path must use this
    single builder to guarantee the payload contract never diverges.

    The downstream transcript worker expects these exact keys:
      meeting_id, text, speaker_id, speaker_name, timestamp, confidence (optional).
    """
    payload: dict[str, Any] = {
        "meeting_id": meeting_id,
        "text": text,
        "speaker_id": speaker_id,
        "speaker_name": speaker_name,
        "timestamp": timestamp,
    }
    if confidence is not None:
        payload["confidence"] = confidence
    return payload


def serialize_transcript_event(
    meeting_id: str,
    text: str,
    speaker_id: str | None,
    speaker_name: str | None,
    timestamp: str | None,
    confidence: float | None = None,
) -> str:
    """Build and JSON-serialize a transcript event payload in one step."""
    payload = build_transcript_event_payload(
        meeting_id=meeting_id,
        text=text,
        speaker_id=speaker_id,
        speaker_name=speaker_name,
        timestamp=timestamp,
        confidence=confidence,
    )
    return json.dumps(payload)
