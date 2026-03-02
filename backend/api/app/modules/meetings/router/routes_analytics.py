import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import rate_limit_general
from app.db.session import get_session
from app.modules.auth.deps import get_current_user_id
from app.modules.analytics.service import get_analytics_for_meeting
from app.modules.meetings.schemas import (
    MeetingAnalyticsMeetingOut,
    MeetingAnalyticsOut,
    MeetingParticipantStatsOut,
)
from app.modules.meetings.service import get_meeting_by_id


logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{meeting_id}/analytics", response_model=MeetingAnalyticsOut)
async def get_meeting_analytics(
    meeting_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(rate_limit_general),
) -> MeetingAnalyticsOut:
    meeting = await get_meeting_by_id(session, meeting_id)
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found",
        )
    is_host = (
        meeting.current_host_id == user_id or meeting.original_host_id == user_id
    )
    if not is_host:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the host can view analytics for this meeting",
        )
    if meeting.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Analytics are available only after the meeting has ended",
        )
    if not meeting.ended_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Analytics are not available for this meeting yet",
        )
    analytics, participants = await get_analytics_for_meeting(session, meeting_id)
    if not analytics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analytics not found for this meeting",
        )
    meeting_out = MeetingAnalyticsMeetingOut(
        meeting_id=analytics.meeting_id,
        started_at=analytics.started_at,
        ended_at=analytics.ended_at,
        duration_seconds=analytics.duration_seconds,
        total_participants=analytics.total_participants,
        host_transfers=analytics.host_transfers,
        transcript_segments=analytics.transcript_segments,
    )
    participants_out = [
        MeetingParticipantStatsOut(
            user_id=p.user_id,
            joined_at=p.joined_at,
            left_at=p.left_at,
            total_time_seconds=p.total_time_seconds,
            speaking_time_seconds=p.speaking_time_seconds,
        )
        for p in participants
    ]
    return MeetingAnalyticsOut(meeting=meeting_out, participants=participants_out)
