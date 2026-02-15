import asyncio
import json
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import httpx
from dotenv import load_dotenv
from jose import jwt
from redis.asyncio import Redis

from vision_agents.core import agents
from vision_agents.core.edge.types import User
from vision_agents.core.events import (
    CallSessionEndedEvent,
    CallSessionParticipantJoinedEvent,
    CallSessionParticipantLeftEvent,
    CallSessionStartedEvent,
)
from vision_agents.core.llm.events import RealtimeUserSpeechTranscriptionEvent
from vision_agents.plugins import gemini, getstream

AgentEvent = Union[
    CallSessionStartedEvent,
    CallSessionParticipantJoinedEvent,
    CallSessionParticipantLeftEvent,
    CallSessionEndedEvent,
    RealtimeUserSpeechTranscriptionEvent,
]


backend_dir = Path(__file__).resolve().parent.parent
api_dir = backend_dir / "api"
if str(api_dir) not in sys.path:
    sys.path.insert(0, str(api_dir))

from app.core.config import get_jwt_secret


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AgentConstants:
    """Configuration constants for the meeting assistant agent."""
    
    SYSTEM_USER_ID: str = "system:assistant"
    SYSTEM_DISPLAY_NAME: str = "Assistant"
    
    MEETING_CREATED_CHANNEL: str = "meeting:created"
    MEETING_ENDED_CHANNEL: str = "meeting:ended"
    MEETING_SNAPSHOT_CHANNEL: str = "meeting:snapshot"
    MEETING_ASSISTANT_PREFERENCE_CHANNEL: str = "meeting:assistant_preference"
    
    STREAM_CALL_TYPE: str = "default"
    ASSISTANT_ENABLED_KEY_PREFIX: str = "assistant_enabled:"
    
    JWT_EXPIRY_MINUTES: int = 60
    HTTP_TIMEOUT_SECONDS: float = 5.0
    HTTP_MAX_RETRIES: int = 2
    
    MIN_QUESTION_LENGTH: int = 3
    MIN_TRANSCRIPT_LENGTH: int = 50
    MAX_QUESTION_LENGTH: int = 200
    MAX_HISTORY_LENGTH: int = 500
    RECENT_TRANSCRIPT_LIMIT: int = 10


class ActivationPhrase(str, Enum):
    """Phrases that activate the assistant."""
    
    HEY = "hey assistant"
    HI = "hi assistant"
    HELLO = "hello assistant"


class DeactivationPhrase(str, Enum):
    """Phrases that deactivate the assistant."""
    
    STOP = "stop assistant"
    BYE = "bye assistant"
    DEACTIVATE = "deactivate assistant"
    TURN_OFF = "turn off assistant"


class ConfirmationPhrase(str, Enum):
    """Phrases indicating user confirmation."""
    
    YES = "yes"
    YEAH = "yeah"
    YEP = "yep"
    SURE = "sure"
    OKAY = "okay"
    OK = "ok"
    GO_AHEAD = "go ahead"


class RejectionPhrase(str, Enum):
    """Phrases indicating user rejection."""
    
    NO = "no"
    NOPE = "nope"
    NAH = "nah"
    DONT = "don't"
    DONT_ALT = "dont"


@dataclass
class TranscriptEntry:
    """A single transcript entry from a meeting participant."""
    
    speaker: str
    text: str
    timestamp: Optional[Any] = None


class _AgentLogFilter(logging.Filter):
    """Filter SDK error logs to reduce noise."""
    
    BENIGN_ERROR_PATTERNS: List[str] = [
        "Already subscribed to track",
        "Timeout waiting for pending track",
        "TimeoutError",
    ]
    
    def filter(self, record: logging.LogRecord) -> bool:
        if record.levelno != logging.ERROR:
            return True
        
        msg = record.getMessage() or ""
        
        if any(pattern in msg for pattern in self.BENIGN_ERROR_PATTERNS):
            record.levelno = logging.DEBUG
            record.levelname = "DEBUG"
        
        if "Error calling handler" in msg and "stream_edge_transport" in msg and "TrackPublished" in msg:
            record.levelno = logging.DEBUG
            record.levelname = "DEBUG"
        
        return True


def _install_agent_log_filters() -> None:
    target_loggers = [
        "vision_agents.core.events.manager",
        "getstream.video.rtc.tracks"
    ]
    
    for logger_name in target_loggers:
        log = logging.getLogger(logger_name)
        log.addFilter(_AgentLogFilter())


def _load_environment() -> None:
    env_path = backend_dir / ".env"
    load_dotenv(dotenv_path=env_path)
    
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        raise ValueError("GEMINI_API_KEY is required in backend/.env")


class AssistantCore:
    """
    Core assistant logic. Transcript is read-only input.
    Responses sent via chat/audio only.
    """
    
    def __init__(
        self,
        meeting_id: str,
        api_base_url: str,
        redis: Optional[Redis] = None
    ) -> None:
        self.meeting_id = meeting_id
        self.api_base_url = api_base_url.rstrip("/")
        self.redis = redis
        
        self.transcript: List[TranscriptEntry] = []
        self.is_active: bool = False
        self.pending_question: Optional[str] = None
        self.assistant_active: bool = False
        self._token: Optional[str] = None
    
    def set_call_active(self, active: bool) -> None:
        self.is_active = active
    
    async def is_assistant_enabled(self) -> bool:
        if self.redis is None:
            return True
        
        try:
            key = f"{AgentConstants.ASSISTANT_ENABLED_KEY_PREFIX}{self.meeting_id}"
            value = await self.redis.get(key)
            return value != "0"
        except Exception as exc:
            logger.debug(
                "Redis assistant-enabled check failed for meeting_id=%s: %s",
                self.meeting_id,
                exc,
                exc_info=True
            )
            return True
    
    async def send_chat_message(self, text: str) -> None:
        content = (text or "").strip()
        if not content:
            logger.debug("Skipping empty chat message")
            return
        
        token = await self._ensure_token()
        if not token:
            logger.error("Cannot send chat message: token generation failed")
            return
        
        url = f"{self.api_base_url}/meetings/{self.meeting_id}/assistant-message"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        payload = {"text": content}
        
        await self._send_http_request(url, headers, payload)
    
    async def _send_http_request(
        self,
        url: str,
        headers: Dict[str, str],
        payload: Dict[str, Any]
    ) -> None:
        last_exception: Optional[Exception] = None
        
        for attempt in range(AgentConstants.HTTP_MAX_RETRIES):
            try:
                async with httpx.AsyncClient(
                    timeout=AgentConstants.HTTP_TIMEOUT_SECONDS
                ) as client:
                    response = await client.post(url, json=payload, headers=headers)
                    response.raise_for_status()
                    logger.debug("Chat message sent successfully")
                    return
            except httpx.HTTPStatusError as exc:
                logger.warning(
                    "HTTP error sending chat (attempt %d/%d): %s",
                    attempt + 1,
                    AgentConstants.HTTP_MAX_RETRIES,
                    exc.response.status_code
                )
                last_exception = exc
            except httpx.RequestError as exc:
                logger.warning(
                    "Network error sending chat (attempt %d/%d): %s",
                    attempt + 1,
                    AgentConstants.HTTP_MAX_RETRIES,
                    exc
                )
                last_exception = exc
            
            if attempt < AgentConstants.HTTP_MAX_RETRIES - 1:
                await asyncio.sleep(0.5 * (attempt + 1))
        
        logger.error(
            "Failed to send chat message after %d attempts: %s",
            AgentConstants.HTTP_MAX_RETRIES,
            last_exception,
            exc_info=last_exception
        )
    
    async def _ensure_token(self) -> Optional[str]:
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
    
    async def handle_transcript(
        self,
        speaker: str,
        text: str,
        timestamp: Optional[Any] = None
    ) -> None:
        if not await self.is_assistant_enabled():
            logger.info(
                "Assistant disabled for meeting %s, skipping transcript",
                self.meeting_id
            )
            return
        
        cleaned_text = self._validate_and_clean_text(text)
        if not cleaned_text:
            return
        
        speaker_id = speaker or "unknown"
        
        if self._is_assistant_speaker(speaker_id):
            logger.debug("Ignoring assistant's own message")
            return
        
        self._append_to_transcript(speaker_id, cleaned_text, timestamp)
        logger.info("[%s]: %s", speaker_id, cleaned_text)
        
        transcript_lower = cleaned_text.lower().strip()
        
        if await self._handle_pending_question_response(transcript_lower):
            return
        
        if await self._handle_deactivation(transcript_lower):
            return
        
        question = await self._handle_activation(transcript_lower, cleaned_text)
        
        if not self.assistant_active:
            return
        
        if question and len(question) >= AgentConstants.MIN_QUESTION_LENGTH:
            await self._process_question(question)
    
    def _validate_and_clean_text(self, text: str) -> str:
        if not text or not isinstance(text, str):
            return ""
        
        cleaned = text.strip()
        if len(cleaned) == 0:
            return ""
        
        return cleaned
    
    def _is_assistant_speaker(self, speaker_id: str) -> bool:
        return speaker_id in (
            AgentConstants.SYSTEM_USER_ID,
            AgentConstants.SYSTEM_DISPLAY_NAME
        )
    
    def _append_to_transcript(
        self,
        speaker: str,
        text: str,
        timestamp: Optional[Any]
    ) -> None:
        entry = TranscriptEntry(
            speaker=speaker,
            text=text,
            timestamp=timestamp
        )
        self.transcript.append(entry)
    
    async def _handle_pending_question_response(self, text_lower: str) -> bool:
        if not self.pending_question:
            return False
        
        if text_lower in [phrase.value for phrase in ConfirmationPhrase]:
            question = self.pending_question
            self.pending_question = None
            reply = f"I will answer this question now: {question}"
            await self.send_chat_message(reply)
            return True
        
        if text_lower in [phrase.value for phrase in RejectionPhrase]:
            self.pending_question = None
            reply = "Understood. I will only use what has been said in this meeting."
            await self.send_chat_message(reply)
            return True
        
        return False
    
    async def _handle_deactivation(self, text_lower: str) -> bool:
        deactivation_phrases = [phrase.value for phrase in DeactivationPhrase]
        
        for phrase in deactivation_phrases:
            if phrase in text_lower:
                self.assistant_active = False
                return True
        
        return False
    
    async def _handle_activation(
        self,
        text_lower: str,
        raw_text: str
    ) -> Optional[str]:
        activation_phrases = [phrase.value for phrase in ActivationPhrase]
        
        for phrase in activation_phrases:
            if not text_lower.startswith(phrase):
                continue
            
            activated_now = False
            if not self.assistant_active:
                self.assistant_active = True
                activated_now = True
                logger.info("Assistant activated for meeting %s", self.meeting_id)
            
            question_after_activation = raw_text[len(phrase):].strip()
            
            if (not question_after_activation or
                len(question_after_activation) < AgentConstants.MIN_QUESTION_LENGTH):
                if activated_now:
                    await self.send_chat_message(
                        "Assistant is active. Ask a question about this meeting."
                    )
                return None
            
            return question_after_activation
        
        if self.assistant_active:
            return raw_text
        
        return None
    
    async def _process_question(self, question: str) -> None:
        logger.info(
            "Processing question for meeting %s: %s",
            self.meeting_id,
            question[:100]
        )
        
        if not self._has_sufficient_context():
            self.pending_question = None
            await self.send_chat_message(
                "There is not enough meeting history yet to answer that."
            )
            return
        
        reply = self._build_reply_from_transcript(question)
        await self.send_chat_message(reply)
    
    def _has_sufficient_context(self) -> bool:
        if not self.transcript:
            return False
        
        total_text = " ".join(entry.text for entry in self.transcript)
        return len(total_text) >= AgentConstants.MIN_TRANSCRIPT_LENGTH
    
    def _build_reply_from_transcript(self, question: str) -> str:
        recent_entries = self.transcript[-AgentConstants.RECENT_TRANSCRIPT_LIMIT:]
        history = " ".join(entry.text for entry in recent_entries)
        
        if not history:
            return "I do not have enough context from this meeting yet."
        
        short_question = question.strip()
        if len(short_question) > AgentConstants.MAX_QUESTION_LENGTH:
            short_question = short_question[:AgentConstants.MAX_QUESTION_LENGTH] + "..."
        
        if len(history) > AgentConstants.MAX_HISTORY_LENGTH:
            history = history[:AgentConstants.MAX_HISTORY_LENGTH] + "..."
        
        return (
            "Based on the recent part of this meeting, here is a focused answer. "
            f"Question: {short_question} "
            f"Context: {history}"
        )


class MeetingAgent:
    """Container for agent instance and task."""
    
    def __init__(
        self,
        meeting_id: str,
        core: AssistantCore,
        agent: agents.Agent,
        task: Optional[asyncio.Task]
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


class AgentManager:
    """Manages meeting agent lifecycle via Redis pub/sub."""
    
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
                meeting_id
            )
            return
        
        logger.info("Attaching agent to meeting %s", meeting_id)
        
        core = AssistantCore(
            meeting_id=meeting_id,
            api_base_url=self.api_base_url,
            redis=self.redis,
        )
        
        llm_instance = self._create_llm_instance()
        
        agent = agents.Agent(
            edge=getstream.Edge(),
            agent_user=User(
                id="meeting-assistant-bot",
                name=AgentConstants.SYSTEM_DISPLAY_NAME,
            ),
            instructions=(
                "You are a meeting assistant. "
                "You understand multilingual speech from participants, "
                "but you always respond in clear, professional English. "
                "Your responses must be in English only, regardless of "
                "the language used in questions or discussions. "
                "If the user says 'stop assistant', 'bye assistant', 'deactivate assistant', "
                "or 'turn off assistant', do not respond at all; remain silent."
            ),
            llm=llm_instance,
        )
        
        meeting_agent = MeetingAgent(
            meeting_id=meeting_id,
            core=core,
            agent=agent,
            task=None,
        )
        
        self._setup_agent_handlers(meeting_agent)
        
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
                exc_info=True
            )
            return True
    
    def _create_llm_instance(self) -> gemini.Realtime:
        try:
            return gemini.Realtime(fps=0, language="en")
        except TypeError:
            logger.debug("Fallback to Realtime without language parameter")
            return gemini.Realtime(fps=0)
    
    async def detach_from_meeting(self, meeting_id: str) -> None:
        if meeting_id not in self.agents:
            logger.debug("Not attached to meeting %s", meeting_id)
            return
        
        logger.info("Detaching from meeting %s", meeting_id)
        meeting_agent = self.agents.pop(meeting_id)
        await meeting_agent.cleanup()
    
    def _setup_agent_handlers(self, meeting_agent: MeetingAgent) -> None:
        core = meeting_agent.core
        agent = meeting_agent.agent

        @agent.events.subscribe
        async def handle_agent_event(event: AgentEvent) -> None:
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
                        meeting_agent.meeting_id
                    )
            elif isinstance(event, CallSessionParticipantLeftEvent):
                participant_id = event.participant.user.id
                if participant_id != "meeting-assistant-bot":
                    logger.info(
                        "Participant %s left meeting %s",
                        event.participant.user.name,
                        meeting_agent.meeting_id
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
                    len(core.transcript)
                )
    
    async def _run_agent(self, meeting_agent: MeetingAgent) -> None:
        try:
            await meeting_agent.agent.create_user()
            call = meeting_agent.agent.edge.client.video.call(
                AgentConstants.STREAM_CALL_TYPE,
                meeting_agent.meeting_id
            )
            
            logger.info("Joining Stream call for meeting %s", meeting_agent.meeting_id)
            
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
                exc_info=exc
            )
        
        finally:
            if meeting_agent.meeting_id in self.agents:
                await self.detach_from_meeting(meeting_agent.meeting_id)
    
    async def listen_to_events(self) -> None:
        if self.redis is None:
            raise RuntimeError("Redis client not initialized")
        
        pubsub = self.redis.pubsub()
        
        await pubsub.subscribe(
            AgentConstants.MEETING_CREATED_CHANNEL,
            AgentConstants.MEETING_ENDED_CHANNEL,
            AgentConstants.MEETING_SNAPSHOT_CHANNEL,
            AgentConstants.MEETING_ASSISTANT_PREFERENCE_CHANNEL,
        )
        
        logger.info("Subscribed to Redis pub/sub channels")
        
        try:
            async for message in pubsub.listen():
                if self._shutdown:
                    break
                
                if message["type"] != "message":
                    continue
                
                await self._handle_pubsub_message(
                    message["channel"],
                    message["data"]
                )
        
        except asyncio.CancelledError:
            logger.info("Event listener cancelled")
            raise
        
        finally:
            await pubsub.unsubscribe()
            await pubsub.close()
    
    async def _handle_pubsub_message(self, channel: str, data: str) -> None:
        try:
            if channel == AgentConstants.MEETING_CREATED_CHANNEL:
                await self._handle_meeting_created(data)
            
            elif channel == AgentConstants.MEETING_ENDED_CHANNEL:
                await self._handle_meeting_ended(data)
            
            elif channel == AgentConstants.MEETING_SNAPSHOT_CHANNEL:
                await self._handle_meeting_snapshot(data)
            
            elif channel == AgentConstants.MEETING_ASSISTANT_PREFERENCE_CHANNEL:
                await self._handle_assistant_preference(data)
        
        except Exception as exc:
            logger.error(
                "Error handling pub/sub message from %s: %s",
                channel,
                exc,
                exc_info=exc
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
            logger.warning("Invalid assistant preference payload: %s (%s)", data, exc)
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


async def main() -> None:
    api_base_url = os.getenv("MEETING_API_URL", "http://127.0.0.1:8001")
    redis_url = os.getenv("REDIS_URL")
    
    if not redis_url:
        raise ValueError("REDIS_URL is required in backend/.env")
    
    manager = AgentManager(api_base_url=api_base_url, redis_url=redis_url)
    
    try:
        await manager.start()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal (KeyboardInterrupt)")
    finally:
        await manager.shutdown()


if __name__ == "__main__":
    _install_agent_log_filters()
    _load_environment()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped by user")
    except Exception as exc:
        logger.critical("Fatal error in main: %s", exc, exc_info=exc)
        sys.exit(1)
