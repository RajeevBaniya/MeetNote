from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock
from uuid import UUID

from app.core.dependencies import register_service
from app.core.interfaces import (
    AnalyticsServiceInterface,
    CacheServiceInterface,
    ChatServiceInterface,
    EventServiceInterface,
    MetricsServiceInterface,
    StreamServiceInterface,
    TranscriptServiceInterface,
)


class MockStreamService(StreamServiceInterface):
    """Mock Stream service for testing."""
    
    def __init__(self) -> None:
        self.query_call_members = AsyncMock(return_value=[])  # type: ignore[method-assign]
        self.end_call = AsyncMock()  # type: ignore[method-assign]
    
    async def query_call_members(
        self, 
        call_type: str, 
        call_id: str, 
        acting_user_id: UUID
    ) -> list[dict[str, Any]]:
        return await self.query_call_members(call_type, call_id, acting_user_id)
    
    async def end_call(
        self, 
        call_type: str, 
        call_id: str, 
        acting_user_id: UUID
    ) -> None:
        await self.end_call(call_type, call_id, acting_user_id)


class MockCacheService(CacheServiceInterface):
    """Mock cache service for testing."""
    
    def __init__(self) -> None:
        self.set_with_expiry = AsyncMock(return_value=True)  # type: ignore[method-assign]
        self.delete_keys = AsyncMock()  # type: ignore[method-assign]
        self.ping = AsyncMock()  # type: ignore[method-assign]
    
    async def set_with_expiry(
        self, 
        key: str, 
        value: str, 
        expiry_seconds: int, 
        only_if_not_exists: bool = False
    ) -> bool:
        return bool(await self.set_with_expiry(key, value, expiry_seconds, only_if_not_exists))
    
    async def delete_keys(self, *keys: str) -> None:
        await self.delete_keys(*keys)
    
    async def ping(self) -> None:
        await self.ping()


class MockAnalyticsService(AnalyticsServiceInterface):
    """Mock analytics service for testing."""
    
    def __init__(self) -> None:
        self.initialize_meeting_analytics = AsyncMock()  # type: ignore[method-assign]
        self.finalize_meeting_analytics = AsyncMock()  # type: ignore[method-assign]
        self.record_host_transfer = AsyncMock()  # type: ignore[method-assign]
    
    async def initialize_meeting_analytics(
        self, 
        meeting_id: UUID, 
        started_at: datetime
    ) -> None:
        await self.initialize_meeting_analytics(meeting_id, started_at)
    
    async def finalize_meeting_analytics(
        self, 
        meeting_id: UUID, 
        ended_at: datetime
    ) -> None:
        await self.finalize_meeting_analytics(meeting_id, ended_at)
    
    async def record_host_transfer(
        self, 
        meeting_id: UUID, 
        new_host_id: UUID
    ) -> None:
        await self.record_host_transfer(meeting_id, new_host_id)


def setup_test_services() -> dict[str, Any]:
    """
    Set up mock services for testing and return references to them.
    
    Returns:
        Dictionary containing mock service instances for assertions
        
    Example:
        def test_meeting_creation():
            mocks = setup_test_services()
            
            # Test meeting creation
            meeting = await create_meeting(session, host_id, "Test Meeting")
            
            # Assert analytics was initialized
            mocks["analytics"].initialize_meeting_analytics.assert_called_once_with(
                meeting.id, meeting.created_at
            )
    """
    # Create mock instances
    mock_stream = MockStreamService()
    mock_cache = MockCacheService()
    mock_analytics = MockAnalyticsService()
    mock_event = AsyncMock()
    mock_transcript = AsyncMock()
    mock_chat = AsyncMock()
    mock_metrics = AsyncMock()
    
    # Register mocks in the service container
    register_service(StreamServiceInterface, mock_stream)
    register_service(CacheServiceInterface, mock_cache)
    register_service(AnalyticsServiceInterface, mock_analytics)
    register_service(EventServiceInterface, mock_event)
    register_service(TranscriptServiceInterface, mock_transcript)
    register_service(ChatServiceInterface, mock_chat)
    register_service(MetricsServiceInterface, mock_metrics)
    
    return {
        "stream": mock_stream,
        "cache": mock_cache,
        "analytics": mock_analytics,
        "event": mock_event,
        "transcript": mock_transcript,
        "chat": mock_chat,
        "metrics": mock_metrics,
    }