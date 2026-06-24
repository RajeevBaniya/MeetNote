# Re-export all functions from focused modules for backward compatibility
from app.modules.meetings.meeting_creation import create_meeting
from app.modules.meetings.meeting_queries import (
    ensure_host_started,
    get_meeting_by_id,
    get_meeting_by_join_code,
    get_meetings_for_host,
    get_my_meetings_dashboard_data,
    list_meetings_for_user_host_or_participant,
)
from app.modules.meetings.meeting_lifecycle import end_meeting
from app.modules.meetings.host_management import (
    ensure_host_consistency,
    restore_original_host_if_rejoined,
    select_next_host_candidate,
    transfer_host_if_current_disconnected,
)

# Export all functions for external use
__all__ = [
    "create_meeting",
    "ensure_host_started",
    "get_meeting_by_id",
    "get_meeting_by_join_code",
    "get_meetings_for_host",
    "get_my_meetings_dashboard_data",
    "list_meetings_for_user_host_or_participant",
    "end_meeting",
    "ensure_host_consistency",
    "restore_original_host_if_rejoined",
    "select_next_host_candidate",
    "transfer_host_if_current_disconnected",
]
