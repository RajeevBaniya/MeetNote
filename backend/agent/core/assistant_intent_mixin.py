import logging
from typing import Any, Optional

from agent.config.agent_constants import AgentConstants


logger = logging.getLogger(__name__)


class AssistantIntentMixin:
    pending_question: Optional[str]
    assistant_active: bool

    async def _handle_pending_question_response(self: Any, text_lower: str) -> bool:
        if not self.pending_question:
            return False

        if text_lower in ["yes", "yeah", "yep", "sure", "okay", "ok", "go ahead"]:
            question = self.pending_question
            self.pending_question = None
            reply = f"I will answer this question now: {question}"
            await self._send_with_cooldown(reply)
            return True

        if text_lower in ["no", "nope", "nah", "don't", "dont"]:
            self.pending_question = None
            reply = "Understood. I will only use what has been said in this meeting."
            await self._send_with_cooldown(reply)
            return True

        return False

    async def _handle_deactivation(self: Any, text_lower: str) -> bool:
        deactivation_phrases = [
            "stop assistant",
            "bye assistant",
            "deactivate assistant",
            "turn off assistant",
        ]

        for phrase in deactivation_phrases:
            if phrase in text_lower:
                self.assistant_active = False
                self.pending_question = None
                return True

        return False

    async def _handle_activation(
        self: Any,
        text_lower: str,
        raw_text: str,
    ) -> Optional[str]:
        activation_phrases = ["hey assistant", "hi assistant", "hello assistant"]

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
                    await self._send_with_cooldown(
                        "Assistant is active. Ask a question about this meeting."
                    )
                return None

            return question_after_activation

        if self.assistant_active:
            return raw_text

        return None
