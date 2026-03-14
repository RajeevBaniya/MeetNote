import asyncio
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx
from jose import jwt
from redis.asyncio import Redis

from agent.config.agent_constants import AgentConstants
from agent.config.env_loader import get_jwt_secret


logger = logging.getLogger(__name__)


class ActivationPhrase(str, Enum):
    HEY = "hey assistant"
    HI = "hi assistant"
    HELLO = "hello assistant"


class DeactivationPhrase(str, Enum):
    STOP = "stop assistant"
    BYE = "bye assistant"
    DEACTIVATE = "deactivate assistant"
    TURN_OFF = "turn off assistant"


class ConfirmationPhrase(str, Enum):
    YES = "yes"
    YEAH = "yeah"
    YEP = "yep"
    SURE = "sure"
    OKAY = "okay"
    OK = "ok"
    GO_AHEAD = "go ahead"


class RejectionPhrase(str, Enum):
    NO = "no"
    NOPE = "nope"
    NAH = "nah"
    DONT = "don't"
    DONT_ALT = "dont"


@dataclass
class TranscriptEntry:
    speaker: str
    text: str
    timestamp: Optional[Any] = None


class _AgentLogFilter(logging.Filter):
    BENIGN_ERROR_PATTERNS: List[str] = [
        "Already subscribed to track",
        "Timeout waiting for pending track",
        "TimeoutError",
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        if record.levelno != logging.ERROR:
            return True

        msg = record.getMessage() or ""

        if any(pattern in msg for pattern in self.BENIGN_ERROR_PATTERNS):
            record.levelno = logging.DEBUG
            record.levelname = "DEBUG"

        if (
            "Error calling handler" in msg
            and "stream_edge_transport" in msg
            and "TrackPublished" in msg
        ):
            record.levelno = logging.DEBUG
            record.levelname = "DEBUG"

        return True


def install_agent_log_filters() -> None:
    target_loggers = [
        "vision_agents.core.events.manager",
        "getstream.video.rtc.tracks",
    ]

    for logger_name in target_loggers:
        log = logging.getLogger(logger_name)
        log.addFilter(_AgentLogFilter())


class AssistantCore:
    def __init__(
        self,
        meeting_id: str,
        api_base_url: str,
        redis: Optional[Redis] = None,
    ) -> None:
        self.meeting_id = meeting_id
        self.api_base_url = api_base_url.rstrip("/")
        self.redis = redis

        self.transcript: List[TranscriptEntry] = []
        self.is_active: bool = False
        self.pending_question: Optional[str] = None
        self.assistant_active: bool = False
        self._token: Optional[str] = None

    def set_call_active(self, active: bool) -> None:
        self.is_active = active

    async def is_assistant_enabled(self) -> bool:
        if self.redis is None:
            return True

        try:
            key = f"{AgentConstants.ASSISTANT_ENABLED_KEY_PREFIX}{self.meeting_id}"
            value = await self.redis.get(key)
            return value != "0"
        except Exception as exc:
            logger.debug(
                "Redis assistant-enabled check failed for meeting_id=%s: %s",
                self.meeting_id,
                exc,
                exc_info=True,
            )
            return True

    async def send_chat_message(self, text: str) -> None:
        content = (text or "").strip()
        if not content:
            logger.debug("Skipping empty chat message")
            return

        token = await self._ensure_token()
        if not token:
            logger.error("Cannot send chat message: token generation failed")
            return

        url = f"{self.api_base_url}/meetings/{self.meeting_id}/assistant-message"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        payload = {"text": content}

        await self._send_http_request(url, headers, payload)

    async def _send_http_request(
        self,
        url: str,
        headers: Dict[str, str],
        payload: Dict[str, Any],
    ) -> None:
        last_exception: Optional[Exception] = None

        for attempt in range(AgentConstants.HTTP_MAX_RETRIES):
            try:
                async with httpx.AsyncClient(
                    timeout=AgentConstants.HTTP_TIMEOUT_SECONDS
                ) as client:
                    response = await client.post(url, json=payload, headers=headers)
                    response.raise_for_status()
                    logger.debug("Chat message sent successfully")
                    return
            except httpx.HTTPStatusError as exc:
                logger.warning(
                    "HTTP error sending chat (attempt %d/%d): %s",
                    attempt + 1,
                    AgentConstants.HTTP_MAX_RETRIES,
                    exc.response.status_code,
                )
                last_exception = exc
            except httpx.RequestError as exc:
                logger.warning(
                    "Network error sending chat (attempt %d/%d): %s",
                    attempt + 1,
                    AgentConstants.HTTP_MAX_RETRIES,
                    exc,
                )
                last_exception = exc

            if attempt < AgentConstants.HTTP_MAX_RETRIES - 1:
                await asyncio.sleep(0.5 * (attempt + 1))

        logger.error(
            "Failed to send chat message after %d attempts: %s",
            AgentConstants.HTTP_MAX_RETRIES,
            last_exception,
            exc_info=last_exception,
        )

    async def _ensure_token(self) -> Optional[str]:
        if self._token:
            return self._token

        try:
            secret = get_jwt_secret()
            expire = datetime.now(timezone.utc) + timedelta(
                minutes=AgentConstants.JWT_EXPIRY_MINUTES
            )
            payload = {
                "sub": AgentConstants.SYSTEM_USER_ID,
                "exp": int(expire.timestamp()),
            }
            token = jwt.encode(payload, secret, algorithm="HS256")
            self._token = token
            return token
        except Exception as exc:
            logger.error("Failed to generate assistant token: %s", exc, exc_info=exc)
            return None

    async def handle_transcript(
        self,
        speaker: str,
        text: str,
        timestamp: Optional[Any] = None,
    ) -> None:
        if not await self.is_assistant_enabled():
            logger.info(
                "Assistant disabled for meeting %s, skipping transcript",
                self.meeting_id,
            )
            return

        cleaned_text = self._validate_and_clean_text(text)
        if not cleaned_text:
            return

        speaker_id = speaker or "unknown"

        if self._is_assistant_speaker(speaker_id):
            logger.debug("Ignoring assistant's own message")
            return

        self._append_to_transcript(speaker_id, cleaned_text, timestamp)
        logger.info("[%s]: %s", speaker_id, cleaned_text)

        transcript_lower = cleaned_text.lower().strip()

        if await self._handle_pending_question_response(transcript_lower):
            return

        if await self._handle_deactivation(transcript_lower):
            return

        question = await self._handle_activation(transcript_lower, cleaned_text)

        if not self.assistant_active:
            return

        if question and len(question) >= AgentConstants.MIN_QUESTION_LENGTH:
            await self._process_question(question)

    def _validate_and_clean_text(self, text: str) -> str:
        if not text or not isinstance(text, str):
            return ""

        cleaned = text.strip()
        if len(cleaned) == 0:
            return ""

        return cleaned

    def _is_assistant_speaker(self, speaker_id: str) -> bool:
        return speaker_id in (
            AgentConstants.SYSTEM_USER_ID,
            AgentConstants.SYSTEM_DISPLAY_NAME,
        )

    def _append_to_transcript(
        self,
        speaker: str,
        text: str,
        timestamp: Optional[Any],
    ) -> None:
        entry = TranscriptEntry(
            speaker=speaker,
            text=text,
            timestamp=timestamp,
        )
        self.transcript.append(entry)

    async def _handle_pending_question_response(self, text_lower: str) -> bool:
        if not self.pending_question:
            return False

        if text_lower in [phrase.value for phrase in ConfirmationPhrase]:
            question = self.pending_question
            self.pending_question = None
            reply = f"I will answer this question now: {question}"
            await self.send_chat_message(reply)
            return True

        if text_lower in [phrase.value for phrase in RejectionPhrase]:
            self.pending_question = None
            reply = "Understood. I will only use what has been said in this meeting."
            await self.send_chat_message(reply)
            return True

        return False

    async def _handle_deactivation(self, text_lower: str) -> bool:
        deactivation_phrases = [phrase.value for phrase in DeactivationPhrase]

        for phrase in deactivation_phrases:
            if phrase in text_lower:
                self.assistant_active = False
                self.pending_question = None
                return True

        return False

    async def _handle_activation(
        self,
        text_lower: str,
        raw_text: str,
    ) -> Optional[str]:
        activation_phrases = [phrase.value for phrase in ActivationPhrase]

        for phrase in activation_phrases:
            if not text_lower.startswith(phrase):
                continue

            activated_now = False
            if not self.assistant_active:
                self.assistant_active = True
                activated_now = True
                logger.info("Assistant activated for meeting %s", self.meeting_id)

            question_after_activation = raw_text[len(phrase) :].strip()

            if (
                not question_after_activation
                or len(question_after_activation) < AgentConstants.MIN_QUESTION_LENGTH
            ):
                if activated_now:
                    await self.send_chat_message(
                        "Assistant is active. Ask a question about this meeting."
                    )
                return None

            return question_after_activation

        if self.assistant_active:
            return raw_text

        return None

    async def _process_question(self, question: str) -> None:
        logger.info(
            "Processing question for meeting %s: %s",
            self.meeting_id,
            question[:100],
        )

        if not self._has_sufficient_context():
            self.pending_question = None
            await self.send_chat_message(
                "There is not enough meeting history yet to answer that."
            )
            return

        reply = self._build_reply_from_transcript(question)
        await self.send_chat_message(reply)

    def _has_sufficient_context(self) -> bool:
        if not self.transcript:
            return False

        total_text = " ".join(entry.text for entry in self.transcript)
        return len(total_text) >= AgentConstants.MIN_TRANSCRIPT_LENGTH

    def _build_reply_from_transcript(self, question: str) -> str:
        recent_entries = self.transcript[-AgentConstants.RECENT_TRANSCRIPT_LIMIT :]
        history = " ".join(entry.text for entry in recent_entries)

        if not history:
            return "I do not have enough context from this meeting yet."

        history_lower = history.lower()
        question_lower = question.lower()

        words = re.findall(r"\w+", question_lower)
        stop_words = {
            "the",
            "is",
            "are",
            "was",
            "were",
            "what",
            "where",
            "who",
            "when",
            "how",
            "a",
            "an",
            "of",
            "for",
            "in",
            "to",
            "about",
            "this",
            "that",
            "did",
            "do",
            "we",
            "you",
            "i",
            "and",
            "or",
            "on",
            "at",
            "from",
            "our",
            "your",
            "meeting",
        }
        keywords = [w for w in words if w not in stop_words]

        if keywords and not any(k in history_lower for k in keywords):
            return "That was not discussed in this meeting."

        short_question = question.strip()
        if len(short_question) > AgentConstants.MAX_QUESTION_LENGTH:
            short_question = (
                short_question[: AgentConstants.MAX_QUESTION_LENGTH] + "..."
            )

        if len(history) > AgentConstants.MAX_HISTORY_LENGTH:
            history = history[: AgentConstants.MAX_HISTORY_LENGTH] + "..."

        return (
            "Based strictly on what was said in this meeting, "
            f"here is a focused answer to your question '{short_question}'. "
            f"Relevant context: {history}"
        )

