import logging
from typing import Any, Optional

from agent.config.agent_constants import AgentConstants


logger = logging.getLogger(__name__)


class AssistantIntentMixin:
    pending_question: Optional[str]
    assistant_active: bool

    async def _handle_pending_question_response(
        self: Any,
        text_lower: str,
        speaker_id: str,
    ) -> bool:
        if not self.redis:
            return False

        pending_q_key = f"assistant:pending_q:{self.meeting_id}"
        try:
            pending = await self.redis.get(pending_q_key)
        except Exception:
            return False  # Fail closed on Redis exception

        if not pending:
            return False

        is_yes = text_lower in ["yes", "yeah", "yep", "sure", "okay", "ok", "go ahead"]
        is_no = text_lower in ["no", "nope", "nah", "don't", "dont"]

        if not is_yes and not is_no:
            return False

        # Reload host ID from Redis (cache) or PostgreSQL (DB source of truth) on cache miss
        host_id = await self.reload_host_id()
        if not host_id:
            logger.warning("Host verification failed: host ID missing or lookup failed for meeting %s", self.meeting_id)
            return False  # Fail closed on host ID lookup failure

        if not speaker_id or speaker_id == "unknown":
            logger.debug("ext_knowledge_approval_ignored_non_host: speaker_id is unknown")
            return False  # Fail closed on unknown speaker

        if speaker_id != str(host_id):
            logger.debug(
                "ext_knowledge_approval_ignored_non_host meeting_id=%s speaker_id=%s host_id=%s",
                self.meeting_id,
                speaker_id,
                host_id,
            )
            return False  # Silently ignore non-host approval attempts

        if is_yes:
            try:
                await self.redis.delete(pending_q_key)
            except Exception:
                pass

            ext_approved_key = f"assistant:ext_approved:{self.meeting_id}"
            try:
                await self.redis.set(ext_approved_key, "1", ex=300)
            except Exception as exc:
                logger.warning("Failed to set ext_approved in Redis for meeting %s: %s", self.meeting_id, exc)

            reply = await self._build_reply_async(pending, external_approved=True)
            await self._send_with_cooldown(reply)
            logger.info("ext_knowledge_approved meeting_id=%s speaker_id=%s ttl_seconds=300", self.meeting_id, speaker_id)
            return True

        if is_no:
            try:
                await self.redis.delete(pending_q_key)
                await self.redis.delete(f"assistant:ext_approved:{self.meeting_id}")
            except Exception:
                pass

            reply = "Understood. I will only use what has been said in this meeting."
            await self._send_with_cooldown(reply)
            logger.info("ext_knowledge_rejected meeting_id=%s speaker_id=%s", self.meeting_id, speaker_id)
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
                
                if self.redis:
                    try:
                        await self.redis.delete(f"assistant:pending_q:{self.meeting_id}")
                        await self.redis.delete(f"assistant:ext_approved:{self.meeting_id}")
                    except Exception as exc:
                        logger.warning("Failed to clear assistant approvals in Redis on deactivation: %s", exc)
                
                logger.info("ext_knowledge_deactivation_cleanup meeting_id=%s", self.meeting_id)
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
