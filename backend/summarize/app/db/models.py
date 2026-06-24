import uuid
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SummaryModel(Base):
    __tablename__ = "summaries"
    __table_args__ = (
        Index("ix_summaries_user_id_created_at", "user_id", text("created_at DESC")),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    instruction: Mapped[str | None] = mapped_column(Text, nullable=True)
    meeting_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    meeting_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    meeting_type: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    location: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_shared: Mapped[bool | None] = mapped_column(Boolean, default=False, nullable=True)

    # JSONB columns for arrays and structured data
    participants: Mapped[list[str] | None] = mapped_column(JSONB, default=list, nullable=True)
    tags: Mapped[list[str] | None] = mapped_column(JSONB, default=list, nullable=True)
    action_items: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, default=list, nullable=True)
    decisions: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, default=list, nullable=True)
    deadlines: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, default=list, nullable=True)
    extracted_participants: Mapped[list[str] | None] = mapped_column(JSONB, default=list, nullable=True)
    email_recipients: Mapped[list[str] | None] = mapped_column(JSONB, default=list, nullable=True)

    # Foreign meeting link
    meeting_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )


class JobModel(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        Index("ix_jobs_user_id_created_at", "user_id", text("created_at DESC")),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        Text,
        default="PENDING",
        nullable=False,
        index=True,
    )
    progress_percentage: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_summary_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("summaries.id", ondelete="SET NULL"),
        nullable=True,
    )
    file_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    upload_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    instruction: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    chunks = relationship(
        "JobChunkProgressModel",
        back_populates="job",
        cascade="all, delete-orphan",
    )


class JobChunkProgressModel(Base):
    __tablename__ = "job_chunks_progress"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        Text,
        default="PENDING",
        nullable=False,
    )
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    action_items: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB,
        default=list,
        nullable=True,
    )
    decisions: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB,
        default=list,
        nullable=True,
    )
    deadlines: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB,
        default=list,
        nullable=True,
    )
    participants: Mapped[list[str] | None] = mapped_column(
        JSONB,
        default=list,
        nullable=True,
    )
    retry_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    job = relationship("JobModel", back_populates="chunks")

