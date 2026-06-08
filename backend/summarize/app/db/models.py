import uuid
from datetime import datetime, date, timezone
from typing import Any

from sqlalchemy import Boolean, DateTime, Date, Text, Index, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

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
