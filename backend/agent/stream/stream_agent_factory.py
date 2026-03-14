import logging

from vision_agents.core import agents
from vision_agents.core.edge.types import User
from vision_agents.plugins import gemini, getstream

from agent.config.agent_constants import AgentConstants


logger = logging.getLogger(__name__)


def _create_llm_instance() -> gemini.Realtime:
    try:
        return gemini.Realtime(fps=0, language="en")
    except TypeError:
        logger.debug("Fallback to Realtime without language parameter")
        return gemini.Realtime(fps=0)


def create_stream_agent(meeting_id: str) -> agents.Agent:
    llm_instance = _create_llm_instance()

    return agents.Agent(
        edge=getstream.Edge(),
        agent_user=User(
            id="meeting-assistant-bot",
            name=AgentConstants.SYSTEM_DISPLAY_NAME,
        ),
        instructions=(
            "You are a meeting assistant. You will get activated by the user when they say 'hey assistant' until then you will remain silent."
            "You understand multilingual speech from participants, but you always respond in clear, professional English. "
            "Your responses must be in English only, regardless of the language used in questions or discussions. "
            "You may ONLY answer using information explicitly stated in the meeting transcript available to you. "
            "Do NOT use any external or general knowledge beyond what was said in this meeting."
            "To use external or general knowledge you will need to ask permission from the user. "
            'If the user says "Yes" then you can use external or general knowledge to answer the question, '
            'but if the user says "No" then you must not use external or general knowledge to answer the question. '
            "If the answer cannot be found in the transcript context, respond exactly with: 'That was not discussed in this meeting.' "
            "Do not infer beyond what is explicitly stated. "
            "Do not fabricate missing details. "
            "If the user says 'stop assistant', 'bye assistant', 'deactivate assistant' or 'turn off assistant', do not respond at all; remain silent."
        ),
        llm=llm_instance,
    )

