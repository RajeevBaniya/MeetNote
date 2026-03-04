import logging
import random
import string
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_service
from app.core.interfaces import AnalyticsServiceInterface
from app.db.models import Meeting

logger = logging.getLogger(__name__)

JOIN_CODE_LENGTH = 12
PASSCODE_LENGTH = 6
MAX_JOIN_CODE_RETRIES = 10


def generate_join_code() -> str:
    """Generate a random numeric join code for meeting access."""
    return "".join(random.choices(string.digits, k=JOIN_CODE_LENGTH))


def generate_secure_passcode() -> str:
    """Generate a random alphabetic passcode for meeting security."""
    return "".join(random.choices(string.ascii_lowercase, k=PASSCODE_LENGTH))


async def create_meeting(
    session: AsyncSession,
    host_id: UUID,
    title: str | None = None,
    scheduled_start_at: datetime | None = None,
    scheduled_end_at: datetime | None = None,
) -> Meeting:
    """
    Create a new meeting with unique join code and initialize analytics.
    
    Args:
        session: Database session
        host_id: UUID of the meeting host
        title: Optional meeting title
        scheduled_start_at: Optional scheduled start time
        scheduled_end_at: Optional scheduled end time
        
    Returns:
        Created meeting instance
        
    Raises:
        RuntimeError: If unable to generate unique join code after retries
    """
    # Generate unique join code with retries
    for attempt in range(MAX_JOIN_CODE_RETRIES):
        join_code = generate_join_code()
        passcode = generate_secure_passcode()
        
        existing = await session.execute(
            select(Meeting).where(Meeting.join_code == join_code)
        )
        if existing.scalar_one_or_none() is None:
            break
            
        if attempt == MAX_JOIN_CODE_RETRIES - 1:
            logger.error(
                "Failed to generate unique join_code after %d attempts", 
                MAX_JOIN_CODE_RETRIES
            )
            raise RuntimeError("Failed to generate unique join code")
    
    # Create meeting instance
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
    
    # Initialize analytics tracking
    analytics_service = get_service(AnalyticsServiceInterface)
    await analytics_service.initialize_meeting_analytics(meeting.id, meeting.created_at)
    
    return meeting