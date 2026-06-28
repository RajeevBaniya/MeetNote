import asyncio
import logging
import time

import httpx

from app.core.config import (
    MEETING_CHAT_PRIMARY_PROVIDER,
    MEETING_CHAT_GEMINI_API_KEY,
    MEETING_CHAT_GEMINI_MODEL,
    MEETING_CHAT_GROQ_API_KEY,
    MEETING_CHAT_GROQ_MODEL,
)
from app.modules.meeting_chat import gemini_client, groq_client  # noqa: F401
from app.modules.meeting_chat.llm_providers import get_llm_provider_class

logger = logging.getLogger(__name__)


class MeetingChatLLMGateway:
    """Gateway for Meeting Chat LLM calls, implementing retry and fallback providers."""

    def __init__(self) -> None:
        self.primary_name = MEETING_CHAT_PRIMARY_PROVIDER
        self.health_check_interval = 300.0  # 5 minutes

        primary_cls = get_llm_provider_class(self.primary_name)
        if self.primary_name == "gemini":
            self.primary_client = primary_cls(
                MEETING_CHAT_GEMINI_API_KEY or "",
                MEETING_CHAT_GEMINI_MODEL or ""
            )
        elif self.primary_name == "groq":
            self.primary_client = primary_cls(
                MEETING_CHAT_GROQ_API_KEY or "",
                MEETING_CHAT_GROQ_MODEL or ""
            )
        else:
            raise ValueError(f"Unknown primary provider: {self.primary_name}")

        self.fallback_name = "groq" if self.primary_name == "gemini" else "gemini"
        self.fallback_client = None

        if self.fallback_name == "groq" and MEETING_CHAT_GROQ_API_KEY and MEETING_CHAT_GROQ_MODEL:
            fallback_cls = get_llm_provider_class("groq")
            self.fallback_client = fallback_cls(
                MEETING_CHAT_GROQ_API_KEY,
                MEETING_CHAT_GROQ_MODEL
            )
        elif self.fallback_name == "gemini" and MEETING_CHAT_GEMINI_API_KEY and MEETING_CHAT_GEMINI_MODEL:
            fallback_cls = get_llm_provider_class("gemini")
            self.fallback_client = fallback_cls(
                MEETING_CHAT_GEMINI_API_KEY,
                MEETING_CHAT_GEMINI_MODEL
            )

        self.primary_healthy = True
        self.last_failure_time = 0.0

    def _is_transient_error(self, exc: Exception) -> bool:
        if isinstance(exc, httpx.TimeoutException):
            return True
        if isinstance(exc, httpx.ConnectError):
            return True
        if isinstance(exc, httpx.HTTPStatusError):
            return exc.response.status_code in {429, 500, 502, 503, 504}
        return False

    async def generate_content(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        timeout: float = 30.0,
    ) -> str:
        current_time = time.time()

        if not self.primary_healthy:
            time_since_failure = current_time - self.last_failure_time
            if time_since_failure >= self.health_check_interval:
                logger.info(
                    "attempting_primary_provider_recovery provider=%s time_since_failure=%.1fs",
                    self.primary_name,
                    time_since_failure,
                )
                try:
                    result = await self.primary_client.generate_content(
                        prompt, max_tokens, temperature, timeout
                    )
                    self.primary_healthy = True
                    logger.info("primary_provider_recovered provider=%s", self.primary_name)
                    return result
                except Exception as exc:
                    self.last_failure_time = current_time
                    logger.warning(
                        "primary_provider_recovery_failed provider=%s err=%s",
                        self.primary_name,
                        exc,
                    )

        if self.primary_healthy:
            max_retries = 3
            throttle_delay = 0.5
            for attempt in range(max_retries):
                try:
                    if attempt == 0:
                        await asyncio.sleep(throttle_delay)
                    else:
                        backoff = 2 ** attempt
                        logger.warning(
                            "primary_provider_retry provider=%s attempt=%d/%d backoff=%ds",
                            self.primary_name,
                            attempt + 1,
                            max_retries,
                            backoff,
                        )
                        await asyncio.sleep(backoff)
                    logger.info("routing_request_to_primary provider=%s", self.primary_name)
                    return await self.primary_client.generate_content(
                        prompt, max_tokens, temperature, timeout
                    )
                except Exception as exc:
                    if not self._is_transient_error(exc):
                        logger.error(
                            "primary_provider_permanent_failure provider=%s err=%s",
                            self.primary_name,
                            exc
                        )
                        raise
                    logger.warning(
                        "primary_provider_transient_failure provider=%s attempt=%d/%d err=%s",
                        self.primary_name,
                        attempt + 1,
                        max_retries,
                        exc,
                    )

            logger.warning(
                "primary_provider_exhausted_retries provider=%s. Switching to fallback provider=%s.",
                self.primary_name,
                self.fallback_name,
            )
            self.primary_healthy = False
            self.last_failure_time = time.time()

        if self.fallback_client:
            logger.info("routing_request_to_fallback provider=%s", self.fallback_name)
            try:
                return await self.fallback_client.generate_content(
                    prompt, max_tokens, temperature, timeout
                )
            except Exception as exc:
                logger.error(
                    "fallback_provider_failed provider=%s err=%s",
                    self.fallback_name,
                    exc
                )
                raise
        else:
            raise RuntimeError(
                f"Primary provider '{self.primary_name}' failed and no fallback provider is configured."
            )


llm_gateway = MeetingChatLLMGateway()
