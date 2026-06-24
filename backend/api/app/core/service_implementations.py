import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from app.core.interfaces import (
    AnalyticsServiceInterface,
    CacheServiceInterface,
    ChatServiceInterface,
    EventServiceInterface,
    MetricsServiceInterface,
    StreamServiceInterface,
    TranscriptServiceInterface,
)
from app.core.metrics import incr
from app.modules.analytics.service import (
    finalize_analytics,
    increment_host_transfer,
    init_analytics,
)
from app.modules.meetings.events import publish_meeting_ended
from app.modules.stream_tokens.service import (
    end_stream_call,
    query_stream_call_members,
)
from app.modules.transcripts.service import expire_transcript_keys
from app.modules.transcripts.summarization import ensure_summary_chunks_for_meeting_end
from app.state.client import get_redis

logger = logging.getLogger(__name__)


class StreamService(StreamServiceInterface):
    """Concrete implementation of Stream video service."""
    
    async def query_call_members(
        self,
        call_type: str,
        call_id: str,
        acting_user_id: UUID
    ) -> list[dict[str, Any]]:
        return await query_stream_call_members(call_type, call_id, acting_user_id)
    
    async def end_call(
        self,
        call_type: str,
        call_id: str,
        acting_user_id: UUID
    ) -> None:
        await end_stream_call(call_type, call_id, acting_user_id)


class CacheService(CacheServiceInterface):
    """Concrete implementation of cache service using Redis."""
    
    async def set_with_expiry(
        self,
        key: str,
        value: str,
        expiry_seconds: int,
        only_if_not_exists: bool = False
    ) -> bool:
        redis = await get_redis()
        result = await redis.set(key, value, ex=expiry_seconds, nx=only_if_not_exists)
        return bool(result)
    
    async def delete_keys(self, *keys: str) -> None:
        if not keys:
            return
        redis = await get_redis()
        await redis.delete(*keys)
    
    async def ping(self) -> None:
        redis = await get_redis()
        await redis.ping()


class AnalyticsService(AnalyticsServiceInterface):
    """Concrete implementation of analytics service."""
    
    async def initialize_meeting_analytics(
        self,
        meeting_id: UUID,
        started_at: datetime
    ) -> None:
        await init_analytics(meeting_id, started_at)
    
    async def finalize_meeting_analytics(
        self,
        meeting_id: UUID,
        ended_at: datetime
    ) -> None:
        await finalize_analytics(meeting_id, ended_at)
    
    async def record_host_transfer(
        self,
        meeting_id: UUID,
        new_host_id: UUID
    ) -> None:
        await increment_host_transfer(meeting_id, new_host_id)


class EventService(EventServiceInterface):
    """Concrete implementation of event service."""
    
    async def publish_meeting_ended(self, meeting_id: UUID) -> None:
        await publish_meeting_ended(meeting_id)


class TranscriptService(TranscriptServiceInterface):
    """Concrete implementation of transcript service."""
    
    async def expire_meeting_keys(
        self,
        cache: CacheServiceInterface,
        meeting_id: UUID
    ) -> None:
        redis = await get_redis()
        try:
            await ensure_summary_chunks_for_meeting_end(redis, meeting_id)
        except Exception:
            logger.exception(
                "ensure_summary_chunks_for_meeting_end_failed meeting_id=%s",
                meeting_id,
            )
        await expire_transcript_keys(redis, meeting_id)


class ChatService(ChatServiceInterface):
    """Concrete implementation of chat service."""
    
    def __init__(self) -> None:
        self._close_handler = None

    def register_close_handler(self, handler: Any) -> None:
        self._close_handler = handler
    
    async def close_meeting_connections(self, meeting_id: UUID) -> None:
        if self._close_handler:
            await self._close_handler(meeting_id)


class MetricsService(MetricsServiceInterface):
    """Concrete implementation of metrics service."""
    
    def increment_counter(self, metric_name: str) -> None:
        incr(metric_name)
