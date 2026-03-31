from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class RecordingStartOut(BaseModel):
    recording_id: str
    started_at: datetime


class RecordingStopIn(BaseModel):
    recording_id: UUID
    file_name: str | None = Field(default=None, max_length=255)
    duration_seconds: int | None = Field(default=None, ge=0)
    started_at: datetime | None = None
    ended_at: datetime | None = None


class RecordingItemOut(BaseModel):
    id: UUID
    meeting_id: UUID
    file_name: str | None
    duration_seconds: int
    started_at: datetime
    ended_at: datetime | None


class RecordingsListOut(BaseModel):
    recordings: list[RecordingItemOut]

