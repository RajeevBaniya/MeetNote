import uuid
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import String, and_, cast, select
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import SummaryModel


def parse_meeting_date(meeting_date: Any) -> date | None:
    if not meeting_date:
        return None
    if isinstance(meeting_date, date):
        return meeting_date
    if isinstance(meeting_date, str):
        val_str = meeting_date.strip()
        if not val_str:
            return None
        # Extract the date part only (e.g., from "2026-06-08T16:36" or "2026-06-08 16:36" or "2026-06-08")
        date_part = val_str.replace(" ", "T").split("T")[0]
        try:
            return date.fromisoformat(date_part)
        except ValueError:
            raise ValueError(f"Invalid date format: {meeting_date}")
    raise ValueError(f"Invalid date type: {type(meeting_date)}")


async def save_summary(
    session: AsyncSession,
    user_id: uuid.UUID,
    transcript: str | None,
    summary: str,
    instruction: str | None,
    title: str | None = None,
    meeting_title: str | None = None,
    meeting_date: str | date | None = None,
    meeting_type: str | None = None,
    participants: list[str] | None = None,
    location: str | None = None,
    tags: list[str] | None = None,
    action_items: list[dict[str, Any]] | None = None,
    decisions: list[dict[str, Any]] | None = None,
    deadlines: list[dict[str, Any]] | None = None,
    extracted_participants: list[str] | None = None,
    meeting_id: uuid.UUID | None = None,
) -> SummaryModel:
    """Save generated summary details to Postgres database."""
    normalized_date = parse_meeting_date(meeting_date)
    new_summary = SummaryModel(
        user_id=user_id,
        transcript=transcript,
        summary=summary,
        instruction=instruction,
        title=title,
        meeting_title=meeting_title,
        meeting_date=normalized_date,
        meeting_type=meeting_type,
        participants=participants or [],
        location=location,
        tags=tags or [],
        action_items=action_items or [],
        decisions=decisions or [],
        deadlines=deadlines or [],
        extracted_participants=extracted_participants or [],
        meeting_id=meeting_id,
    )
    session.add(new_summary)
    await session.commit()
    await session.refresh(new_summary)
    return new_summary


async def list_summaries(
    session: AsyncSession,
    user_id: uuid.UUID,
    skip: int = 0,
    take: int = 20,
    search: str = "",
    date_from: date | None = None,
    date_to: date | None = None,
    meeting_type: str | None = None,
    meeting_id: uuid.UUID | None = None,
    upload_only: bool = False,
    tags: list[str] | None = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> list[SummaryModel]:
    """Query, filter, and page stored summaries for a given user."""
    stmt = select(SummaryModel)

    # Filter constraints
    conditions = [SummaryModel.user_id == user_id]

    if meeting_id:
        conditions.append(SummaryModel.meeting_id == meeting_id)
    if upload_only:
        conditions.append(SummaryModel.meeting_id.is_(None))
    if search and search.strip():
        search_term = f"%{search.strip()}%"
        conditions.append(
            (SummaryModel.summary.ilike(search_term)) |
            (SummaryModel.meeting_title.ilike(search_term)) |
            (SummaryModel.title.ilike(search_term))
        )
    if date_from:
        conditions.append(SummaryModel.meeting_date >= date_from)
    if date_to:
        conditions.append(SummaryModel.meeting_date <= date_to)
    if meeting_type:
        conditions.append(SummaryModel.meeting_type == meeting_type)
    if tags and len(tags) > 0:
        conditions.append(SummaryModel.tags.op("?|")(cast(tags, ARRAY(String))))

    stmt = stmt.where(and_(*conditions))

    # Column Sorting validation
    valid_sorts = {"created_at", "updated_at", "meeting_date", "meeting_title"}
    actual_sort = sort_by if sort_by in valid_sorts else "created_at"
    sort_column = getattr(SummaryModel, actual_sort)

    if sort_order.lower() == "asc":
        stmt = stmt.order_by(sort_column.asc())
    else:
        stmt = stmt.order_by(sort_column.desc())

    stmt = stmt.offset(skip).limit(take)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_summary_by_id(
    session: AsyncSession,
    summary_id: uuid.UUID,
    user_id: uuid.UUID,
) -> SummaryModel | None:
    """Retrieve details of a saved summary after validating ownership."""
    stmt = select(SummaryModel).where(
        SummaryModel.id == summary_id,
        SummaryModel.user_id == user_id,
    )
    result = await session.execute(stmt)
    return result.scalars().first()


async def get_summary_for_export(
    session: AsyncSession,
    summary_id: uuid.UUID,
) -> SummaryModel | None:
    """Retrieve details of a saved summary for pdf/word exporter without user check."""
    stmt = select(SummaryModel).where(SummaryModel.id == summary_id)
    result = await session.execute(stmt)
    return result.scalars().first()


async def update_summary(
    session: AsyncSession,
    summary_id: uuid.UUID,
    user_id: uuid.UUID,
    update_data: dict[str, Any],
) -> SummaryModel | None:
    """Update fields of a saved summary after validating ownership."""
    summary = await get_summary_by_id(session, summary_id, user_id)
    if not summary:
        return None

    # Map incoming camelCase keys to target snake_case model attributes
    CAMEL_TO_SNAKE = {
        "title": "title",
        "summary": "summary",
        "instruction": "instruction",
        "isShared": "is_shared",
        "emailRecipients": "email_recipients",
        "meetingTitle": "meeting_title",
        "meetingDate": "meeting_date",
        "meetingType": "meeting_type",
        "participants": "participants",
        "location": "location",
        "tags": "tags",
        "actionItems": "action_items",
        "decisions": "decisions",
        "deadlines": "deadlines",
        "extractedParticipants": "extracted_participants",
    }

    for key, value in update_data.items():
        db_key = CAMEL_TO_SNAKE.get(key)
        if db_key and hasattr(summary, db_key):
            if db_key == "meeting_date":
                value = parse_meeting_date(value)
            setattr(summary, db_key, value)

    summary.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(summary)
    return summary


async def delete_summary(
    session: AsyncSession,
    summary_id: uuid.UUID,
    user_id: uuid.UUID,
) -> bool:
    """Delete a saved summary if owned by the user."""
    summary = await get_summary_by_id(session, summary_id, user_id)
    if not summary:
        return False
    await session.delete(summary)
    await session.commit()
    return True
