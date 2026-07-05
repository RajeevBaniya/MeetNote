import os
from typing import Dict, List, Type, Optional
from pydantic import BaseModel

from app.core import config
from app.modules.speech.providers import (
    BaseSpeechProvider,
    DeepgramProvider,
    GladiaProvider,
    AssemblyAIProvider,
    SpeechmaticsProvider,
    GroqWhisperProvider,
    GetStreamProvider,
    ProviderCapabilities,
)

# Registry of class mappings to allow dynamic registration of future providers
# satisfying the Open/Closed Principle.
_PROVIDER_CLASSES: Dict[str, Type[BaseSpeechProvider]] = {
    "DeepgramProvider": DeepgramProvider,
    "GladiaProvider": GladiaProvider,
    "AssemblyAIProvider": AssemblyAIProvider,
    "SpeechmaticsProvider": SpeechmaticsProvider,
    "GroqWhisperProvider": GroqWhisperProvider,
    "GetStreamProvider": GetStreamProvider,
}


def register_provider_class(name: str, cls: Type[BaseSpeechProvider]) -> None:
    """Register a new provider class to support future extension without modifying core logic."""
    _PROVIDER_CLASSES[name] = cls


class ProviderRegistryEntry(BaseModel):
    """Configuration structure representing a configured provider instance in the registry."""
    name: str
    priority: int
    enabled: bool
    api_key: str
    cooldown_seconds: int
    timeout_seconds: int
    provider_class_name: str

    model_config = {
        "arbitrary_types_allowed": True
    }


class ProviderRegistry:
    """Registry maintaining configured speech providers and their instantiation factories."""

    def __init__(self) -> None:
        self._entries: List[ProviderRegistryEntry] = []
        self._initialize_registry()

    def _initialize_registry(self) -> None:
        # Load the configuration list dynamically according to defined priority order
        raw_configs = [
            ("Deepgram1", 1, config.DEEPGRAM_API_KEY_1, config.DEEPGRAM_COOLDOWN_SECONDS, "DeepgramProvider"),
            ("Deepgram2", 2, config.DEEPGRAM_API_KEY_2, config.DEEPGRAM_COOLDOWN_SECONDS, "DeepgramProvider"),
            ("Deepgram3", 3, config.DEEPGRAM_API_KEY_3, config.DEEPGRAM_COOLDOWN_SECONDS, "DeepgramProvider"),
            ("Gladia", 4, config.GLADIA_API_KEY, config.GLADIA_COOLDOWN_SECONDS, "GladiaProvider"),
            ("AssemblyAI", 5, config.ASSEMBLYAI_API_KEY, config.ASSEMBLYAI_COOLDOWN_SECONDS, "AssemblyAIProvider"),
            ("Speechmatics", 6, config.SPEECHMATICS_API_KEY, config.SPEECHMATICS_COOLDOWN_SECONDS, "SpeechmaticsProvider"),
            ("GroqWhisper", 7, config.GROQ_API_KEY, config.GROQ_COOLDOWN_SECONDS, "GroqWhisperProvider"),
            ("GetStream", 8, "fallback_dummy_key", 0, "GetStreamProvider"),
        ]

        for name, priority, key, cooldown, class_name in raw_configs:
            enabled = bool(key and key.strip())
            entry = ProviderRegistryEntry(
                name=name,
                priority=priority,
                enabled=enabled,
                api_key=key,
                cooldown_seconds=cooldown,
                timeout_seconds=30,  # Standard timeout
                provider_class_name=class_name,
            )
            self._entries.append(entry)

    def get_entries(self) -> List[ProviderRegistryEntry]:
        """Returns all registered provider entries ordered by priority."""
        return sorted(self._entries, key=lambda e: e.priority)

    def get_entry(self, name: str) -> Optional[ProviderRegistryEntry]:
        """Retrieves a specific registry entry by its unique name."""
        for entry in self._entries:
            if entry.name == name:
                return entry
        return None

    def create_provider_instance(self, name: str) -> Optional[BaseSpeechProvider]:
        """Instantiates a fresh provider subclass instance using the registry mapping."""
        entry = self.get_entry(name)
        if not entry or not entry.enabled:
            return None

        cls = _PROVIDER_CLASSES.get(entry.provider_class_name)
        if not cls:
            raise ValueError(f"Unknown provider class mapping: {entry.provider_class_name}")

        return cls(api_key=entry.api_key, name=entry.name)
