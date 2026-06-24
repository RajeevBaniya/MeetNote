from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import CursorResult, text
from sqlalchemy.ext.asyncio import AsyncSession


async def create_recording_start(
    session: AsyncSession,
    meeting_id: UUID,
) -> tuple[UUID, datetime]:
    recording_id = uuid4()
    started_at = datetime.now(timezone.utc)
    await session.execute(
        text(
            "INSERT INTO recordings (id, meeting_id, started_at) "
            "VALUES (:id, :meeting_id, :started_at)"
        ),
        {"id": recording_id, "meeting_id": meeting_id, "started_at": started_at},
    )
    await session.commit()
    return recording_id, started_at


async def finalize_recording(
    session: AsyncSession,
    meeting_id: UUID,
    recording_id: UUID,
    file_name: str | None,
    duration_seconds: int | None,
    started_at: datetime | None,
    ended_at: datetime | None,
) -> bool:
    updates: dict[str, object] = {
        "id": recording_id,
        "meeting_id": meeting_id,
    }
    set_parts: list[str] = []

    if file_name is not None:
        set_parts.append("file_name = :file_name")
        updates["file_name"] = file_name
    if duration_seconds is not None:
        set_parts.append("duration_seconds = :duration_seconds")
        updates["duration_seconds"] = int(duration_seconds)
    if started_at is not None:
        set_parts.append("started_at = :started_at")
        updates["started_at"] = started_at
    if ended_at is not None:
        set_parts.append("ended_at = :ended_at")
        updates["ended_at"] = ended_at

    if not set_parts:
        return False

    q = (
        "UPDATE recordings SET "
        + ", ".join(set_parts)
        + " WHERE id = :id AND meeting_id = :meeting_id"
    )
    result = await session.execute(text(q), updates)
    await session.commit()
    if isinstance(result, CursorResult):
        return (result.rowcount or 0) > 0
    return False


async def list_recordings_for_meeting(
    session: AsyncSession,
    meeting_id: UUID,
) -> list[dict[str, Any]]:
    result = await session.execute(
        text(
            "SELECT id, meeting_id, file_name, duration_seconds, started_at, ended_at "
            "FROM recordings "
            "WHERE meeting_id = :meeting_id "
            "ORDER BY started_at DESC"
        ),
        {"meeting_id": meeting_id},
    )
    return [dict(row._mapping) for row in result.fetchall()]

