import logging
import random
import secrets
import string
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Meeting
from app.db.session import async_session_factory
from app.modules.stream_tokens.service import query_stream_call_members

logger = logging.getLogger(__name__)

STREAM_CALL_TYPE = "default"


JOIN_CODE_LENGTH = 12
PASSCODE_LENGTH = 6
MAX_JOIN_CODE_RETRIES = 10


def generate_join_code() -> str:
    return "".join(random.choices(string.digits, k=JOIN_CODE_LENGTH))


def generate_secure_passcode() -> str:
    return "".join(random.choices(string.ascii_lowercase, k=PASSCODE_LENGTH))


async def create_meeting(
    session: AsyncSession,
    host_id: UUID,
    title: str | None = None,
    scheduled_start_at: datetime | None = None,
    scheduled_end_at: datetime | None = None,
) -> Meeting:
    for attempt in range(MAX_JOIN_CODE_RETRIES):
        join_code = generate_join_code()
        passcode = generate_secure_passcode()
        existing = await session.execute(
            select(Meeting).where(Meeting.join_code == join_code)
        )
        if existing.scalar_one_or_none() is None:
            break
        if attempt == MAX_JOIN_CODE_RETRIES - 1:
            logger.error("Failed to generate unique join_code after %d attempts", MAX_JOIN_CODE_RETRIES)
            raise RuntimeError("Failed to generate unique join code")
    meeting = Meeting(
        host_id=host_id,
        original_host_id=host_id,
        current_host_id=host_id,
        title=title or "",
        join_code=join_code,
        passcode=passcode,
        is_active=True,
        scheduled_start_at=scheduled_start_at,
        scheduled_end_at=scheduled_end_at,
    )
    session.add(meeting)
    await session.commit()
    await session.refresh(meeting)
    return meeting


async def get_meeting_by_id(
    session: AsyncSession,
    meeting_id: UUID,
) -> Meeting | None:
    result = await session.execute(select(Meeting).where(Meeting.id == meeting_id))
    return result.scalar_one_or_none()


async def get_meeting_by_join_code(
    session: AsyncSession,
    join_code: str,
) -> Meeting | None:
    cleaned = join_code.strip().replace(" ", "").replace("-", "")
    if not cleaned.isdigit() or len(cleaned) != JOIN_CODE_LENGTH:
        return None
    result = await session.execute(select(Meeting).where(Meeting.join_code == cleaned))
    return result.scalar_one_or_none()


async def end_meeting(
    session: AsyncSession,
    meeting_id: UUID,
    requester_id: UUID,
) -> Meeting:
    meeting = await get_meeting_by_id(session, meeting_id)
    if not meeting:
        raise ValueError("Meeting not found")
    if meeting.current_host_id != requester_id:
        raise ValueError("Only the host can end the meeting")
    if not meeting.is_active:
        raise ValueError("Meeting is already ended")

    now = datetime.now(timezone.utc)
    await session.execute(
        update(Meeting)
        .where(Meeting.id == meeting_id)
        .values(is_active=False, ended_at=now)
    )
    await session.commit()
    await session.refresh(meeting)
    return meeting


async def select_next_host_candidate(
    meeting_id: UUID,
    original_host_id: UUID,
    exclude_user_id: UUID,
) -> UUID | None:
    members = await query_stream_call_members(
        call_type=STREAM_CALL_TYPE,
        call_id=str(meeting_id),
        acting_user_id=original_host_id,
    )
    for member in members:
        uid = member.get("user_id")
        if not uid or not isinstance(uid, str):
            continue
        try:
            user_uuid = UUID(uid)
        except Exception:
            continue
        if user_uuid == exclude_user_id:
            continue
        return user_uuid
    return None


async def transfer_host_if_current_disconnected(
    meeting_id: UUID,
    disconnected_user_id: UUID | None,
) -> UUID | None:
    async with async_session_factory() as session:
        async with session.begin():
            result = await session.execute(
                select(Meeting).where(Meeting.id == meeting_id).with_for_update()
            )
            meeting = result.scalar_one_or_none()
            if not meeting or not meeting.is_active:
                return None
            target_id = disconnected_user_id or meeting.current_host_id
            if meeting.current_host_id != target_id:
                return None
            members = await query_stream_call_members(
                call_type=STREAM_CALL_TYPE,
                call_id=str(meeting_id),
                acting_user_id=meeting.original_host_id,
            )
            connected_ids: set[UUID] = set()
            for member in members:
                uid = member.get("user_id")
                if not uid or not isinstance(uid, str):
                    continue
                try:
                    connected_ids.add(UUID(uid))
                except Exception:
                    continue
            if target_id in connected_ids:
                return None
            candidate = await select_next_host_candidate(
                meeting_id=meeting_id,
                original_host_id=meeting.original_host_id,
                exclude_user_id=target_id,
            )
            if candidate is None:
                return None
            await session.execute(
                update(Meeting)
                .where(Meeting.id == meeting_id)
                .values(current_host_id=candidate)
            )
        return candidate


async def restore_original_host_if_rejoined(
    meeting_id: UUID,
    user_id: UUID,
) -> UUID | None:
    async with async_session_factory() as session:
        async with session.begin():
            result = await session.execute(
                select(Meeting).where(Meeting.id == meeting_id).with_for_update()
            )
            meeting = result.scalar_one_or_none()
            if not meeting or not meeting.is_active:
                return None
            if meeting.original_host_id != user_id:
                return None
            if meeting.current_host_id == meeting.original_host_id:
                return None
            members = await query_stream_call_members(
                call_type=STREAM_CALL_TYPE,
                call_id=str(meeting_id),
                acting_user_id=user_id,
            )
            user_ids: set[str] = set()
            for member in members:
                uid = member.get("user_id")
                if isinstance(uid, str) and uid.strip():
                    user_ids.add(uid.strip())
            if str(user_id) not in user_ids:
                return None
            await session.execute(
                update(Meeting)
                .where(Meeting.id == meeting_id)
                .values(current_host_id=meeting.original_host_id)
            )
        return meeting.original_host_id


async def ensure_host_consistency(meeting_id: UUID) -> UUID | None:
    return await transfer_host_if_current_disconnected(meeting_id, None)


async def get_meetings_for_host(
    session: AsyncSession,
    host_id: UUID,
    ended_limit: int,
) -> tuple[list[Meeting], list[Meeting]]:
    active_result = await session.execute(
        select(Meeting)
        .where(Meeting.host_id == host_id, Meeting.is_active.is_(True))
        .order_by(desc(Meeting.created_at))
    )
    active_meetings = list(active_result.scalars().all())

    ended_result = await session.execute(
        select(Meeting)
        .where(Meeting.host_id == host_id, Meeting.is_active.is_(False))
        .order_by(desc(Meeting.created_at))
        .limit(ended_limit)
    )
    ended_meetings = list(ended_result.scalars().all())

    return active_meetings, ended_meetings
