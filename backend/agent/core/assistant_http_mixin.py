import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import httpx
from jose import jwt

from agent.config.agent_constants import AgentConstants
from agent.config.env_loader import get_jwt_secret
from agent.redis.assistant_redis_controls import set_cooldown_after_response


logger = logging.getLogger(__name__)


class AssistantHttpMixin:
    meeting_id: str
    api_base_url: str
    _token: Optional[str]

    async def _send_with_cooldown(self: Any, text: str) -> bool:
        await set_cooldown_after_response(self.redis, self.meeting_id)
        return await self.send_chat_message(text)

    async def send_chat_message(self: Any, text: str) -> bool:
        content = (text or "").strip()
        if not content:
            logger.debug("Skipping empty chat message")
            return False

        token = await self._ensure_token()
        if not token:
            logger.error("Cannot send chat message: token generation failed")
            return False

        url = f"{self.api_base_url}/meetings/{self.meeting_id}/assistant-message"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        payload = {"text": content}

        return await self._send_http_request(url, headers, payload)

    async def _send_http_request(
        self: Any,
        url: str,
        headers: Dict[str, str],
        payload: Dict[str, Any],
    ) -> bool:
        last_exception: Optional[Exception] = None

        for attempt in range(AgentConstants.HTTP_MAX_RETRIES):
            try:
                async with httpx.AsyncClient(
                    timeout=AgentConstants.HTTP_TIMEOUT_SECONDS
                ) as client:
                    response = await client.post(url, json=payload, headers=headers)
                    response.raise_for_status()
                    logger.debug("Chat message sent successfully")
                    return True
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
        return False

    async def _ensure_token(self: Any) -> Optional[str]:
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
