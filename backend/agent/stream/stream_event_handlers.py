import logging
from typing import Any

from vision_agents.core.events import (
    CallSessionEndedEvent,
    CallSessionParticipantJoinedEvent,
    CallSessionParticipantLeftEvent,
    CallSessionStartedEvent,
)
from vision_agents.core.llm.events import RealtimeUserSpeechTranscriptionEvent

from agent.manager.meeting_agent import MeetingAgent


logger = logging.getLogger(__name__)


AgentEvent = (
    CallSessionStartedEvent
    | CallSessionParticipantJoinedEvent
    | CallSessionParticipantLeftEvent
    | CallSessionEndedEvent
    | RealtimeUserSpeechTranscriptionEvent
)


def attach_stream_event_handlers(meeting_agent: MeetingAgent) -> None:
    core = meeting_agent.core
    agent = meeting_agent.agent

    @agent.events.subscribe
    async def handle_agent_event(event: Any) -> None:
        if isinstance(event, CallSessionStartedEvent):
            logger.info("Call session started for meeting %s", meeting_agent.meeting_id)
            meeting_agent.session_started = True
            core.set_call_active(True)
        elif isinstance(event, CallSessionParticipantJoinedEvent):
            participant_id = event.participant.user.id
            if participant_id != "meeting-assistant-bot":
                logger.info(
                    "Participant %s joined meeting %s",
                    event.participant.user.name,
                    meeting_agent.meeting_id,
                )
        elif isinstance(event, CallSessionParticipantLeftEvent):
            participant_id = event.participant.user.id
            if participant_id != "meeting-assistant-bot":
                logger.info(
                    "Participant %s left meeting %s",
                    event.participant.user.name,
                    meeting_agent.meeting_id,
                )
        elif isinstance(event, RealtimeUserSpeechTranscriptionEvent):
            await core.handle_transcript(
                speaker=getattr(event, "participant_id", "unknown"),
                text=event.text,
                timestamp=getattr(event, "timestamp", None),
            )
        elif isinstance(event, CallSessionEndedEvent):
            core.set_call_active(False)
            logger.info(
                "Call session ended for meeting %s (transcript entries: %d)",
                meeting_agent.meeting_id,
                len(core.transcript),
            )

