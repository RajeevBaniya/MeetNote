"""Analytics service facade. Re-exports all public functions for backward compatibility."""

from app.modules.analytics.analytics_finalize import (
    finalize_analytics,
    increment_host_transfer,
    increment_host_transfer_in_session,
    init_analytics,
)
from app.modules.analytics.analytics_queries import get_analytics_for_meeting
from app.modules.analytics.analytics_tracking import (
    add_speaking_time,
    record_participant_join,
    record_participant_leave,
)

__all__ = [
    "add_speaking_time",
    "finalize_analytics",
    "get_analytics_for_meeting",
    "increment_host_transfer",
    "increment_host_transfer_in_session",
    "init_analytics",
    "record_participant_join",
    "record_participant_leave",
]
