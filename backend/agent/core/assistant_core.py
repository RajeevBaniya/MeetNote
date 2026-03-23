import logging
from typing import Any, List, Optional

from redis.asyncio import Redis

from agent.config.agent_constants import AgentConstants
from agent.core.assistant_context import (
    build_reply_from_context,
    build_transcript_history_text,
    fetch_summary_chunks_text,
)
from agent.core.assistant_http_mixin import AssistantHttpMixin
from agent.core.assistant_intent_mixin import AssistantIntentMixin
from agent.core.transcript_types import TranscriptEntry
from agent.redis.assistant_redis_controls import (
    is_cooldown_active,
    remember_last_question,
    should_skip_duplicate_question,
)
from agent.utils.question_normalization import normalize_question_text


logger = logging.getLogger(__name__)


class AssistantCore(AssistantHttpMixin, AssistantIntentMixin):
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

    async def _process_question(self, question: str) -> None:
        logger.info(
            "Processing question for meeting %s: %s",
            self.meeting_id,
            question[:100],
        )

        if await is_cooldown_active(self.redis, self.meeting_id):
            logger.debug("Assistant cooldown active, ignoring question trigger")
            return

        normalized = normalize_question_text(question)
        if await should_skip_duplicate_question(self.redis, self.meeting_id, normalized):
            logger.debug("Duplicate question ignored for meeting %s", self.meeting_id)
            return

        try:
            if not self._has_sufficient_context():
                self.pending_question = None
                ok = await self._send_with_cooldown(
                    "There is not enough meeting history yet to answer that."
                )
                if ok and normalized:
                    await remember_last_question(
                        self.redis, self.meeting_id, normalized
                    )
                return

            reply = await self._build_reply_async(question)
            ok = await self._send_with_cooldown(reply)
            if ok and normalized:
                await remember_last_question(self.redis, self.meeting_id, normalized)
            elif not ok:
                await self._send_with_cooldown(AgentConstants.FALLBACK_REPLY_MESSAGE)
        except Exception:
            logger.exception("Assistant response failed for meeting %s", self.meeting_id)
            try:
                await self._send_with_cooldown(AgentConstants.FALLBACK_REPLY_MESSAGE)
            except Exception:
                pass

    def _has_sufficient_context(self) -> bool:
        if not self.transcript:
            return False

        total_text = " ".join(entry.text for entry in self.transcript)
        return len(total_text) >= AgentConstants.MIN_TRANSCRIPT_LENGTH

    async def _build_reply_async(self, question: str) -> str:
        transcript_history = build_transcript_history_text(self.transcript)
        chunks_text = await fetch_summary_chunks_text(self.redis, self.meeting_id)
        return build_reply_from_context(
            question,
            transcript_history,
            chunks_text,
            len(self.transcript),
        )
