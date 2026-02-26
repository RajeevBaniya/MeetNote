from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


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


class ParticipantActionIn(BaseModel):
    user_id: UUID


class CheckRemovedOut(BaseModel):
    removed: bool


class RecordingActionOut(BaseModel):
    status: str


class RecordingItemOut(BaseModel):
    url: str
    filename: str
    start_time: str
    end_time: str
    session_id: str


class RecordingsListOut(BaseModel):
    recordings: list[RecordingItemOut]


class TranscriptSegmentOut(BaseModel):
    type: str
    start_time: str
    stop_time: str
    speaker_id: str | None = None
    text: str


class TranscriptOut(BaseModel):
    segments: list[TranscriptSegmentOut]


class MeetingListItemOut(BaseModel):
    id: UUID
    title: str
    is_active: bool
    created_at: datetime
    scheduled_start_at: datetime | None = None


class MyMeetingsOut(BaseModel):
    upcoming: list[MeetingListItemOut]
    active: list[MeetingListItemOut]
    ended: list[MeetingListItemOut]


class MeetingAnalyticsOut(BaseModel):
    meeting_id: UUID
    duration_seconds: int | None
    participants_count: int
    chat_message_count: int
    recording_count: int


class AssistantPreferenceIn(BaseModel):
    enabled: bool


class AssistantPreferenceOut(BaseModel):
    enabled: bool
