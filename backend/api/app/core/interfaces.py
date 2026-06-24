from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any
from uuid import UUID


class StreamServiceInterface(ABC):
    """Interface for Stream video service operations."""
    
    @abstractmethod
    async def query_call_members(
        self,
        call_type: str,
        call_id: str,
        acting_user_id: UUID
    ) -> list[dict[str, Any]]:
        """Query members currently in a Stream call."""
        pass
    
    @abstractmethod
    async def end_call(
        self,
        call_type: str,
        call_id: str,
        acting_user_id: UUID
    ) -> None:
        """End a Stream video call."""
        pass


class CacheServiceInterface(ABC):
    """Interface for caching operations (Redis)."""
    
    @abstractmethod
    async def set_with_expiry(
        self,
        key: str,
        value: str,
        expiry_seconds: int,
        only_if_not_exists: bool = False
    ) -> bool:
        """Set a cache value with expiration."""
        pass
    
    @abstractmethod
    async def delete_keys(self, *keys: str) -> None:
        """Delete multiple cache keys."""
        pass
    
    @abstractmethod
    async def ping(self) -> None:
        """Test cache connectivity."""
        pass


class AnalyticsServiceInterface(ABC):
    """Interface for analytics operations."""
    
    @abstractmethod
    async def initialize_meeting_analytics(
        self,
        meeting_id: UUID,
        started_at: datetime
    ) -> None:
        """Initialize analytics tracking for a new meeting."""
        pass
    
    @abstractmethod
    async def finalize_meeting_analytics(
        self,
        meeting_id: UUID,
        ended_at: datetime
    ) -> None:
        """Finalize analytics when meeting ends."""
        pass
    
    @abstractmethod
    async def record_host_transfer(
        self,
        meeting_id: UUID,
        new_host_id: UUID
    ) -> None:
        """Record a host transfer event."""
        pass


class EventServiceInterface(ABC):
    """Interface for event publishing operations."""
    
    @abstractmethod
    async def publish_meeting_ended(self, meeting_id: UUID) -> None:
        """Publish meeting ended event."""
        pass


class TranscriptServiceInterface(ABC):
    """Interface for transcript operations."""
    
    @abstractmethod
    async def expire_meeting_keys(
        self,
        cache: CacheServiceInterface,
        meeting_id: UUID
    ) -> None:
        """Expire transcript-related cache keys for a meeting."""
        pass


class ChatServiceInterface(ABC):
    """Interface for chat operations."""
    
    @abstractmethod
    async def close_meeting_connections(self, meeting_id: UUID) -> None:
        """Close all chat WebSocket connections for a meeting."""
        pass

    @abstractmethod
    def register_close_handler(self, handler: Any) -> None:
        """Register a handler callback to close chat connections."""
        pass


class MetricsServiceInterface(ABC):
    """Interface for metrics operations."""
    
    @abstractmethod
    def increment_counter(self, metric_name: str) -> None:
        """Increment a metrics counter."""
        pass
