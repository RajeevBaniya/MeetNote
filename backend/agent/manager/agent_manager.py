import asyncio
import json
import logging
from typing import Dict, Optional

from redis.asyncio import Redis

from agent.config.agent_constants import AgentConstants
from agent.core.assistant_core import AssistantCore
from agent.manager.meeting_agent import MeetingAgent
from agent.redis_client.redis_channels import (
    MEETING_ASSISTANT_PREFERENCE_CHANNEL,
    MEETING_CREATED_CHANNEL,
    MEETING_ENDED_CHANNEL,
    MEETING_SNAPSHOT_CHANNEL,
)
from agent.redis_client.redis_listener import listen_to_events
from agent.stream.stream_agent_factory import create_stream_agent
from agent.stream.stream_event_handlers import attach_stream_event_handlers


logger = logging.getLogger(__name__)


class AgentManager:
    def __init__(self, api_base_url: str, redis_url: str) -> None:
        self.api_base_url = api_base_url
        self.redis_url = redis_url
        self.agents: Dict[str, MeetingAgent] = {}
        self.redis: Optional[Redis] = None
        self._shutdown: bool = False
        self.assistant_enabled_by_user: Dict[str, bool] = {}

    async def initialize(self) -> None:
        self.redis = Redis.from_url(self.redis_url, decode_responses=True)
        logger.info("Agent manager initialized with Redis connection")

    async def attach_to_meeting(self, meeting_id: str) -> None:
        if meeting_id in self.agents:
            logger.debug("Already attached to meeting %s", meeting_id)
            return

        if not await self._is_meeting_assistant_enabled(meeting_id):
            logger.info(
                "Assistant disabled for meeting %s, skipping attach",
                meeting_id,
            )
            return

        logger.info("Attaching agent to meeting %s", meeting_id)

        core = AssistantCore(
            meeting_id=meeting_id,
            api_base_url=self.api_base_url,
            redis=self.redis,
        )

        agent = create_stream_agent(meeting_id)

        meeting_agent = MeetingAgent(
            meeting_id=meeting_id,
            core=core,
            agent=agent,
            task=None,
        )

        attach_stream_event_handlers(meeting_agent)

        task = asyncio.create_task(self._run_agent(meeting_agent))
        meeting_agent.task = task
        self.agents[meeting_id] = meeting_agent

    async def _is_meeting_assistant_enabled(self, meeting_id: str) -> bool:
        if self.redis is None:
            return True

        try:
            key = f"{AgentConstants.ASSISTANT_ENABLED_KEY_PREFIX}{meeting_id}"
            value = await self.redis.get(key)
            return value != "0"
        except Exception as exc:
            logger.debug(
                "Redis check failed for meeting %s: %s",
                meeting_id,
                exc,
                exc_info=exc,
            )
            return True

    async def detach_from_meeting(self, meeting_id: str) -> None:
        if meeting_id not in self.agents:
            logger.debug("Not attached to meeting %s", meeting_id)
            return

        logger.info("Detaching from meeting %s", meeting_id)
        meeting_agent = self.agents.pop(meeting_id)
        await meeting_agent.cleanup()

    async def _run_agent(self, meeting_agent: MeetingAgent) -> None:
        try:
            await meeting_agent.agent.create_user()
            call = meeting_agent.agent.edge.client.video.call(
                AgentConstants.STREAM_CALL_TYPE,
                meeting_agent.meeting_id,
            )

            logger.info(
                "Joining Stream call for meeting %s",
                meeting_agent.meeting_id,
            )

            async with meeting_agent.agent.join(call):
                await meeting_agent.agent.finish()

            logger.info("Agent finished for meeting %s", meeting_agent.meeting_id)

        except asyncio.CancelledError:
            logger.info("Agent cancelled for meeting %s", meeting_agent.meeting_id)
            raise

        except Exception as exc:
            logger.error(
                "Agent error for meeting %s: %s",
                meeting_agent.meeting_id,
                exc,
                exc_info=exc,
            )

        finally:
            if meeting_agent.meeting_id in self.agents:
                await self.detach_from_meeting(meeting_agent.meeting_id)

    async def listen_to_events(self) -> None:
        if self.redis is None:
            raise RuntimeError("Redis client not initialized")

        channels = [
            MEETING_CREATED_CHANNEL,
            MEETING_ENDED_CHANNEL,
            MEETING_SNAPSHOT_CHANNEL,
            MEETING_ASSISTANT_PREFERENCE_CHANNEL,
        ]

        async def handler(channel: str, data: str) -> None:
            await self._handle_pubsub_message(channel, data)

        await listen_to_events(
            redis_client=self.redis,
            channels=channels,
            should_shutdown=lambda: self._shutdown,
            handle_message=handler,
        )

    async def _handle_pubsub_message(self, channel: str, data: str) -> None:
        try:
            if channel == MEETING_CREATED_CHANNEL:
                await self._handle_meeting_created(data)

            elif channel == MEETING_ENDED_CHANNEL:
                await self._handle_meeting_ended(data)

            elif channel == MEETING_SNAPSHOT_CHANNEL:
                await self._handle_meeting_snapshot(data)

            elif channel == MEETING_ASSISTANT_PREFERENCE_CHANNEL:
                await self._handle_assistant_preference(data)

        except Exception as exc:
            logger.error(
                "Error handling pub/sub message from %s: %s",
                channel,
                exc,
                exc_info=exc,
            )

    async def _handle_meeting_created(self, meeting_id: str) -> None:
        if not meeting_id:
            logger.warning("Empty meeting_id in created event")
            return

        await self.attach_to_meeting(meeting_id)

    async def _handle_meeting_ended(self, meeting_id: str) -> None:
        if not meeting_id:
            logger.warning("Empty meeting_id in ended event")
            return

        await self.detach_from_meeting(meeting_id)

    async def _handle_meeting_snapshot(self, data: str) -> None:
        try:
            payload = json.loads(data)
            meeting_ids = payload.get("meeting_ids") or []
        except (json.JSONDecodeError, AttributeError) as exc:
            logger.warning("Invalid snapshot payload: %s (%s)", data, exc)
            return

        for meeting_id in meeting_ids:
            if not isinstance(meeting_id, str) or not meeting_id:
                continue

            await self.attach_to_meeting(meeting_id)

    async def _handle_assistant_preference(self, data: str) -> None:
        try:
            payload = json.loads(data)
            meeting_id = payload.get("meeting_id")
            enabled = payload.get("enabled", True)
        except (json.JSONDecodeError, AttributeError) as exc:
            logger.warning(
                "Invalid assistant preference payload: %s (%s)",
                data,
                exc,
            )
            return

        if not isinstance(meeting_id, str) or not meeting_id:
            logger.warning("Invalid meeting_id in preference payload")
            return

        self.assistant_enabled_by_user[meeting_id] = bool(enabled)

        if not enabled:
            await self.detach_from_meeting(meeting_id)
        else:
            await self.attach_to_meeting(meeting_id)

    async def start(self) -> None:
        await self.initialize()
        await self.listen_to_events()

    async def shutdown(self) -> None:
        self._shutdown = True
        logger.info("Shutting down agent manager...")

        for meeting_id in list(self.agents.keys()):
            await self.detach_from_meeting(meeting_id)

        if self.redis:
            await self.redis.aclose()

        logger.info("Agent manager shut down complete")

