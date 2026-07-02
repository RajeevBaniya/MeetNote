from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CreateMeetingIn(BaseModel):
    title: str | None = None
    scheduled_start_at: datetime | None = None


class MeetingOut(BaseModel):
    id: UUID
    host_id: UUID
    original_host_id: UUID
    current_host_id: UUID
    title: str
    join_code: str
    passcode: str
    is_active: bool
    scheduled_start_at: datetime | None = None
    scheduled_end_at: datetime | None = None
    created_at: datetime
    ended_at: datetime | None = None

    class Config:
        from_attributes = True


class EndMeetingOut(BaseModel):
    status: str = "ended"
    meeting_id: UUID | None = None
    ended_at: datetime | None = None
    ended_by: UUID | None = None


class MeetingStatusOut(BaseModel):
    is_active: bool
    host_joined: bool


class ParticipantActionIn(BaseModel):
    user_id: UUID


class CheckRemovedOut(BaseModel):
    removed: bool


class TranscriptSegmentOut(BaseModel):
    type: str
    start_time: str
    stop_time: str
    speaker_id: str | None = None
    text: str


class TranscriptOut(BaseModel):
    segments: list[TranscriptSegmentOut]
    chunk_summaries: list[str] = Field(default_factory=list)


class MeetingListItemOut(BaseModel):
    id: UUID
    title: str
    is_active: bool
    created_at: datetime
    scheduled_start_at: datetime | None = None
    can_delete: bool = False


class MyMeetingsOut(BaseModel):
    upcoming: list[MeetingListItemOut]
    active: list[MeetingListItemOut]
    ended: list[MeetingListItemOut]


class MeetingMyItemOut(BaseModel):
    """Extended list row: host or participant; has_summary is always false from API."""

    id: UUID
    title: str
    created_at: datetime
    ended_at: datetime | None
    is_active: bool
    participant_count: int
    has_summary: bool = False
    scheduled_start_at: datetime | None = None
    can_delete: bool = False


class MeetingAnalyticsMeetingOut(BaseModel):
    meeting_id: UUID
    started_at: datetime
    ended_at: datetime | None
    duration_seconds: int
    total_participants: int
    host_transfers: int
    transcript_segments: int


class MeetingParticipantStatsOut(BaseModel):
    user_id: UUID
    joined_at: datetime
    left_at: datetime | None
    total_time_seconds: int
    speaking_time_seconds: int


class MeetingAnalyticsOut(BaseModel):
    meeting: MeetingAnalyticsMeetingOut
    participants: list[MeetingParticipantStatsOut]


class AssistantPreferenceIn(BaseModel):
    enabled: bool


class AssistantPreferenceOut(BaseModel):
    enabled: bool


class MeetingParticipantOut(BaseModel):
    user_id: UUID
    name: str
    joined_at: str
    is_current_host: bool


class MeetingParticipantsOut(BaseModel):
    participants: list[MeetingParticipantOut]
