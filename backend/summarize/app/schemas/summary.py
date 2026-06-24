import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class StructuredData(BaseModel):
    actionItems: list[dict[str, Any]] = Field(default_factory=list)
    decisions: list[dict[str, Any]] = Field(default_factory=list)
    deadlines: list[dict[str, Any]] = Field(default_factory=list)
    participants: list[str] = Field(default_factory=list)


class SummaryGenerateRequest(BaseModel):
    transcript: str
    instruction: str
    title: str | None = None
    meetingTitle: str | None = None
    meetingDate: str | None = None
    meetingType: str | None = None
    participants: list[str] | None = None
    location: str | None = None
    tags: list[str] | None = None
    extractStructured: bool = True
    meetingId: uuid.UUID | None = None
    persist: bool = True


class SummaryUpdateRequest(BaseModel):
    title: str | None = None
    summary: str | None = None
    instruction: str | None = None
    isShared: bool | None = None
    emailRecipients: list[str] | None = None
    meetingTitle: str | None = None
    meetingDate: str | date | None = None
    meetingType: str | None = None
    participants: list[str] | None = None
    location: str | None = None
    tags: list[str] | None = None
    actionItems: list[dict[str, Any]] | None = None
    decisions: list[dict[str, Any]] | None = None
    deadlines: list[dict[str, Any]] | None = None
    extractedParticipants: list[str] | None = None


class SummaryResponse(BaseModel):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    title: str | None
    transcript: str | None
    summary: str
    instruction: str | None
    meeting_title: str | None
    meeting_date: date | None
    meeting_type: str | None
    participants: list[str]
    location: str | None
    tags: list[str]
    action_items: list[dict[str, Any]]
    decisions: list[dict[str, Any]]
    deadlines: list[dict[str, Any]]
    extracted_participants: list[str]
    is_shared: bool
    email_recipients: list[str]
    meeting_id: uuid.UUID | None

    @field_validator(
        "participants",
        "tags",
        "action_items",
        "decisions",
        "deadlines",
        "extracted_participants",
        "email_recipients",
        mode="before",
    )
    @classmethod
    def default_empty_list(cls, v: Any) -> list:
        if v is None:
            return []
        return v

    @field_validator("is_shared", mode="before")
    @classmethod
    def default_false(cls, v: Any) -> bool:
        if v is None:
            return False
        return v

    class Config:
        from_attributes = True


class SummaryListResponse(BaseModel):
    success: bool
    items: list[SummaryResponse]


class SummaryGenerateResponse(BaseModel):
    success: bool
    summary: str
    structured: StructuredData
    savedId: uuid.UUID | None


class SummaryDetailResponse(BaseModel):
    success: bool
    item: SummaryResponse


class DeleteResponse(BaseModel):
    success: bool

