import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_app_base_url
from app.core.rate_limit import rate_limit_general
from app.db.session import get_session
from app.modules.auth.deps import get_current_user_id
from app.modules.meetings.service import get_meeting_by_id


logger = logging.getLogger(__name__)

router = APIRouter()


def _format_ics_datetime(value: datetime) -> str:
  return value.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


@router.get("/{meeting_id}/ics")
async def get_meeting_ics(
    meeting_id: UUID,
    _user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(rate_limit_general),
):
    meeting = await get_meeting_by_id(session, meeting_id)
    if not meeting:
        raise HTTPException(
            status_code=404,
            detail="Meeting not found",
        )
    base_url = get_app_base_url()
    parsed = urlparse(base_url)
    domain = parsed.hostname or parsed.netloc or "localhost"
    join_link = f"{base_url}/meeting/join?code={meeting.join_code}"
    start = meeting.scheduled_start_at or meeting.created_at
    if start is None:
        start = datetime.now(timezone.utc)
    start_utc = start.astimezone(timezone.utc)
    if meeting.scheduled_end_at:
        end_utc = meeting.scheduled_end_at.astimezone(timezone.utc)
    else:
        end_utc = start_utc + timedelta(hours=1)
    dtstamp = datetime.now(timezone.utc)
    uid = f"{meeting.id}@{domain}"
    title = meeting.title or "Meeting"
    scheduled_label = start_utc.strftime("%Y-%m-%d %H:%M:%S UTC")
    description_lines = [
        f"Scheduled time: {scheduled_label}",
        f"Join link: {join_link}",
        f"Passcode: {meeting.passcode}",
    ]
    raw_description = "\n".join(description_lines)
    description = (
        raw_description.replace("\\", "\\\\")
        .replace("\n", "\\n")
        .replace(",", r"\,")
        .replace(";", r"\;")
    )
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:-//{domain}//Meeting//EN",
        "CALSCALE=GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{_format_ics_datetime(dtstamp)}",
        f"DTSTART:{_format_ics_datetime(start_utc)}",
        f"DTEND:{_format_ics_datetime(end_utc)}",
        f"SUMMARY:{title}",
        f"DESCRIPTION:{description}",
        f"URL:{join_link}",
        f"LOCATION:{join_link}",
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    body = "\r\n".join(lines) + "\r\n"
    return Response(
        content=body,
        media_type="text/calendar",
        headers={
            "Content-Disposition": 'attachment; filename=\"meeting.ics\"',
        },
    )

