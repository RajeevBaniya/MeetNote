from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.modules.auth.deps import get_current_user_id
from app.modules.meetings.share_service import get_share_info

router = APIRouter()


@router.get("/{meeting_id}/share")
async def get_meeting_share(
    meeting_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    info = await get_share_info(session, meeting_id, user_id)
    if not info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found or you are not the host",
        )
    return info
