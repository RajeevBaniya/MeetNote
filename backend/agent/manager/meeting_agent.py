import asyncio
import logging
from typing import Optional

from agent.core.assistant_core import AssistantCore
from vision_agents.core import agents

logger = logging.getLogger(__name__)


class MeetingAgent:
    def __init__(
        self,
        meeting_id: str,
        core: AssistantCore,
        agent: agents.Agent,
        task: Optional[asyncio.Task[None]],
    ) -> None:
        self.meeting_id = meeting_id
        self.core = core
        self.agent = agent
        self.task = task
        self.session_started: bool = False

    async def cleanup(self) -> None:
        if self.task and not self.task.done():
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                logger.debug("Agent task cancelled for meeting %s", self.meeting_id)

        logger.info("Cleaned up agent for meeting %s", self.meeting_id)

