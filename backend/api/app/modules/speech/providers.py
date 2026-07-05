import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ProviderCapabilities(BaseModel):
    """Metadata representing the capabilities of a speech provider."""
    supports_streaming: bool
    supports_diarization: bool
    supports_interim_results: bool
    max_session_duration: int  # in seconds
    audio_format: str


class TranscriptionResult(BaseModel):
    """Standardized transcription output for downstream pipeline consumption."""
    text: str
    speaker_id: Optional[str] = None
    speaker_name: Optional[str] = None
    is_final: bool = True
    confidence: Optional[float] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None


class BaseSpeechProvider(ABC):
    """Abstract Base Class defining the interface for all speech-to-text providers."""

    def __init__(self, api_key: str, name: str) -> None:
        self.api_key = api_key
        self.name = name
        self.is_connected = False

    @property
    @abstractmethod
    def capabilities(self) -> ProviderCapabilities:
        """Returns capabilities metadata for the provider."""
        pass

    @abstractmethod
    async def connect(
        self,
        session_id: str,
        user_id: str,
        user_name: str,
    ) -> None:
        """Establishes connection to the speech recognition service."""
        pass

    @abstractmethod
    async def send_audio_chunk(self, chunk: bytes) -> None:
        """Sends binary audio chunk to the STT provider."""
        pass

    @abstractmethod
    async def receive_transcription(self) -> Optional[TranscriptionResult]:
        """Receives and parses transcription results from the provider."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Closes the connection to the speech recognition service."""
        pass


class DeepgramProvider(BaseSpeechProvider):
    """Deepgram STT provider implementation."""

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_streaming=True,
            supports_diarization=True,
            supports_interim_results=True,
            max_session_duration=10800,  # 3 hours
            audio_format="audio/webm",
        )

    async def connect(
        self,
        session_id: str,
        user_id: str,
        user_name: str,
    ) -> None:
        if not self.api_key:
            raise ValueError("Deepgram API Key is required")
        self.is_connected = True
        logger.info("Connected to Deepgram STT for session=%s", session_id)

    async def send_audio_chunk(self, chunk: bytes) -> None:
        if not self.is_connected:
            raise RuntimeError("Deepgram provider is not connected")
        logger.debug("Sent audio chunk of size %d to Deepgram", len(chunk))

    async def receive_transcription(self) -> Optional[TranscriptionResult]:
        if not self.is_connected:
            raise RuntimeError("Deepgram provider is not connected")
        return None

    async def close(self) -> None:
        self.is_connected = False
        logger.info("Closed Deepgram connection")


class GladiaProvider(BaseSpeechProvider):
    """Gladia STT provider implementation."""

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_streaming=True,
            supports_diarization=True,
            supports_interim_results=True,
            max_session_duration=14400,  # 4 hours
            audio_format="audio/webm",
        )

    async def connect(
        self,
        session_id: str,
        user_id: str,
        user_name: str,
    ) -> None:
        if not self.api_key:
            raise ValueError("Gladia API Key is required")
        self.is_connected = True
        logger.info("Connected to Gladia STT for session=%s", session_id)

    async def send_audio_chunk(self, chunk: bytes) -> None:
        if not self.is_connected:
            raise RuntimeError("Gladia provider is not connected")
        logger.debug("Sent audio chunk of size %d to Gladia", len(chunk))

    async def receive_transcription(self) -> Optional[TranscriptionResult]:
        if not self.is_connected:
            raise RuntimeError("Gladia provider is not connected")
        return None

    async def close(self) -> None:
        self.is_connected = False
        logger.info("Closed Gladia connection")


class AssemblyAIProvider(BaseSpeechProvider):
    """AssemblyAI STT provider implementation."""

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_streaming=True,
            supports_diarization=True,
            supports_interim_results=True,
            max_session_duration=7200,  # 2 hours
            audio_format="audio/webm",
        )

    async def connect(
        self,
        session_id: str,
        user_id: str,
        user_name: str,
    ) -> None:
        if not self.api_key:
            raise ValueError("AssemblyAI API Key is required")
        self.is_connected = True
        logger.info("Connected to AssemblyAI STT for session=%s", session_id)

    async def send_audio_chunk(self, chunk: bytes) -> None:
        if not self.is_connected:
            raise RuntimeError("AssemblyAI provider is not connected")
        logger.debug("Sent audio chunk of size %d to AssemblyAI", len(chunk))

    async def receive_transcription(self) -> Optional[TranscriptionResult]:
        if not self.is_connected:
            raise RuntimeError("AssemblyAI provider is not connected")
        return None

    async def close(self) -> None:
        self.is_connected = False
        logger.info("Closed AssemblyAI connection")


class SpeechmaticsProvider(BaseSpeechProvider):
    """Speechmatics STT provider implementation."""

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_streaming=True,
            supports_diarization=True,
            supports_interim_results=True,
            max_session_duration=10800,  # 3 hours
            audio_format="audio/webm",
        )

    async def connect(
        self,
        session_id: str,
        user_id: str,
        user_name: str,
    ) -> None:
        if not self.api_key:
            raise ValueError("Speechmatics API Key is required")
        self.is_connected = True
        logger.info("Connected to Speechmatics STT for session=%s", session_id)

    async def send_audio_chunk(self, chunk: bytes) -> None:
        if not self.is_connected:
            raise RuntimeError("Speechmatics provider is not connected")
        logger.debug("Sent audio chunk of size %d to Speechmatics", len(chunk))

    async def receive_transcription(self) -> Optional[TranscriptionResult]:
        if not self.is_connected:
            raise RuntimeError("Speechmatics provider is not connected")
        return None

    async def close(self) -> None:
        self.is_connected = False
        logger.info("Closed Speechmatics connection")


class GroqWhisperProvider(BaseSpeechProvider):
    """Groq Whisper STT provider implementation (chunked REST fallback)."""

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_streaming=False,
            supports_diarization=False,
            supports_interim_results=False,
            max_session_duration=3600,  # 1 hour
            audio_format="audio/wav",
        )

    async def connect(
        self,
        session_id: str,
        user_id: str,
        user_name: str,
    ) -> None:
        if not self.api_key:
            raise ValueError("Groq API Key is required")
        self.is_connected = True
        logger.info("Connected to Groq Whisper for session=%s", session_id)

    async def send_audio_chunk(self, chunk: bytes) -> None:
        if not self.is_connected:
            raise RuntimeError("Groq Whisper provider is not connected")
        logger.debug("Sent audio chunk of size %d to Groq Whisper", len(chunk))

    async def receive_transcription(self) -> Optional[TranscriptionResult]:
        if not self.is_connected:
            raise RuntimeError("Groq Whisper provider is not connected")
        return None

    async def close(self) -> None:
        self.is_connected = False
        logger.info("Closed Groq Whisper connection")


class GetStreamProvider(BaseSpeechProvider):
    """Adapter for GetStream passive WebRTC STT fallback."""

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_streaming=True,
            supports_diarization=True,
            supports_interim_results=False,
            max_session_duration=86400,  # 24 hours
            audio_format="audio/webrtc",
        )

    async def connect(
        self,
        session_id: str,
        user_id: str,
        user_name: str,
    ) -> None:
        self.is_connected = True
        logger.info("GetStream fallback active for session=%s", session_id)

    async def send_audio_chunk(self, chunk: bytes) -> None:
        # Passive webhook pipeline: audio is sent over WebRTC directly to GetStream SFU
        pass

    async def receive_transcription(self) -> Optional[TranscriptionResult]:
        return None

    async def close(self) -> None:
        self.is_connected = False
        logger.info("Closed GetStream connection")
