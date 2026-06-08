import re
import logging
from typing import Any

logger = logging.getLogger(__name__)

EMAIL_REGEX = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


async def send_summary_email(
    recipients: list[str],
    summary_text: str,
    subject: str = "Meeting Summary",
    reply_to_email: str | None = None,
) -> list[dict[str, Any]]:
    """
    Validate parameters and log email dispatch request.
    Raises NotImplementedError since Gmail integration is deferred.
    """
    # 1. Input Validation
    if not recipients or len(recipients) == 0:
        raise ValueError("Recipients list cannot be empty")
        
    if not summary_text or not summary_text.strip():
        raise ValueError("Summary text cannot be empty")
        
    invalid = [r for r in recipients if not EMAIL_REGEX.match(r)]
    if invalid:
        raise ValueError(f"Invalid email addresses: {', '.join(invalid)}")
        
    # 2. Logging
    logger.info(
        "Email dispatch requested: recipients=%s, subject=%s, reply_to=%s",
        recipients,
        subject,
        reply_to_email,
        extra={
            "recipients_count": len(recipients),
            "subject": subject,
        }
    )
    
    # 3. Raise 501 parity exception
    raise NotImplementedError("email service not configured")
