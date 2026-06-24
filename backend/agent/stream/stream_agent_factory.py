import logging

from agent.config.agent_constants import AgentConstants
from agent.utils.prompt_loader import get_agent_prompt
from vision_agents.core import agents
from vision_agents.core.edge.types import User
from vision_agents.plugins import gemini, getstream

logger = logging.getLogger(__name__)


def _create_llm_instance() -> gemini.Realtime:
    try:
        return gemini.Realtime(fps=0, language="en")
    except TypeError:
        logger.debug("Fallback to Realtime without language parameter")
        return gemini.Realtime(fps=0)


def create_stream_agent(meeting_id: str) -> agents.Agent:
    llm_instance = _create_llm_instance()
    instructions = get_agent_prompt("assistant_instructions.txt")

    return agents.Agent(
        edge=getstream.Edge(),
        agent_user=User(
            id="meeting-assistant-bot",
            name=AgentConstants.SYSTEM_DISPLAY_NAME,
        ),
        instructions=instructions,
        llm=llm_instance,
    )

