from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_frontend_base_url_required
from app.modules.meetings.meeting_queries import get_meeting_by_id


def _is_meeting_creator(meeting, user_id: UUID) -> bool:
    return meeting.host_id == user_id


async def get_share_info(
    session: AsyncSession,
    meeting_id: UUID,
    user_id: UUID,
) -> dict | None:
    meeting = await get_meeting_by_id(session, meeting_id)
    if not meeting:
        return None
    if not _is_meeting_creator(meeting, user_id):
        return None
    if not meeting.is_active and meeting.ended_at is not None:
        raise HTTPException(
            status_code=400,
            detail="Meeting has already ended",
        )
    base = get_frontend_base_url_required()
    join_url = f"{base}/meeting/join"
    return {
        "meeting_id": str(meeting.id),
        "join_code": meeting.join_code,
        "passcode": meeting.passcode,
        "title": meeting.title or "",
        "scheduled_start_at": (
            meeting.scheduled_start_at.isoformat() if meeting.scheduled_start_at else None
        ),
        "join_url": join_url,
    }
