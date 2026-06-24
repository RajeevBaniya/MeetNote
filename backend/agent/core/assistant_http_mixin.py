import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import httpx
from agent.config.agent_constants import AgentConstants
from agent.config.env_loader import JWT_SECRET
from agent.redis.assistant_redis_controls import set_cooldown_after_response
from jose import jwt

logger = logging.getLogger(__name__)


class AssistantHttpMixin:
    meeting_id: str
    api_base_url: str
    _token: Optional[str]

    async def _send_with_cooldown(self: Any, text: str) -> bool:
        await set_cooldown_after_response(self.redis, self.meeting_id)
        return bool(await self.send_chat_message(text))

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

        return bool(await self._send_http_request(url, headers, payload))

    async def get_host_id_from_db(self: Any) -> Optional[str]:
        token = await self._ensure_token()
        if not token:
            logger.error("Cannot fetch host ID: token generation failed")
            return None

        url = f"{self.api_base_url}/meetings/{self.meeting_id}/host-id"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        
        last_exception: Optional[Exception] = None
        for attempt in range(AgentConstants.HTTP_MAX_RETRIES):
            try:
                async with httpx.AsyncClient(
                    timeout=AgentConstants.HTTP_TIMEOUT_SECONDS
                ) as client:
                    response = await client.get(url, headers=headers)
                    if response.status_code == 200:
                        host_id = response.text.strip().replace('"', '')
                        logger.debug("Successfully fetched host ID from DB: %s", host_id)
                        return host_id
                    response.raise_for_status()
            except Exception as exc:
                logger.warning(
                    "Error fetching host ID from DB (attempt %d/%d): %s",
                    attempt + 1,
                    AgentConstants.HTTP_MAX_RETRIES,
                    exc,
                )
                last_exception = exc

            if attempt < AgentConstants.HTTP_MAX_RETRIES - 1:
                await asyncio.sleep(0.5 * (attempt + 1))

        logger.error(
            "Failed to fetch host ID from DB after %d attempts: %s",
            AgentConstants.HTTP_MAX_RETRIES,
            last_exception,
        )
        return None

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
            try:
                secret = JWT_SECRET
                payload = jwt.decode(self._token, secret, algorithms=["HS256"])
                exp = payload.get("exp")
                if exp:
                    now_ts = int(datetime.now(timezone.utc).timestamp())
                    if exp - now_ts > 300:
                        return str(self._token)
            except Exception as exc:
                logger.warning("Failed to decode cached assistant token, regenerating: %s", exc)
                self._token = None

        try:
            secret = JWT_SECRET
            expire = datetime.now(timezone.utc) + timedelta(
                minutes=AgentConstants.JWT_EXPIRY_MINUTES
            )
            payload = {
                "sub": AgentConstants.SYSTEM_USER_ID,
                "exp": int(expire.timestamp()),
            }
            token = jwt.encode(payload, secret, algorithm="HS256")
            self._token = token
            return str(token)
        except Exception as exc:
            logger.error("Failed to generate assistant token: %s", exc, exc_info=exc)
            return None
