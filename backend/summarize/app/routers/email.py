import re
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.middleware.auth import get_current_user_id
from app.services.email import send_summary_email

router = APIRouter(prefix="/api/email", tags=["email"])

# Email verification regex matching JS regex: /^[^\s@]+@[^\s@]+\.[^\s@]+$/
EMAIL_REGEX = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class EmailSendRequest(BaseModel):
    recipients: list[str]
    summary: str
    subject: str = "Meeting Summary"
    replyToEmail: str | None = None


class EmailSendSuccessResponse(BaseModel):
    success: bool
    message: str
    sentTo: list[str]


@router.post("/send", responses={
    200: {"model": EmailSendSuccessResponse},
    400: {"description": "Validation Error"},
    500: {"description": "Mail Delivery Error"},
})
async def send_email(
    request: EmailSendRequest,
    current_user_id: UUID = Depends(get_current_user_id),
) -> Any:
    """Send meeting summary details via email to the listed recipients."""
    if not request.recipients or len(request.recipients) == 0:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "Recipients array is required"},
        )

    if not request.summary.strip():
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "Summary is required"},
        )

    invalid_emails = [
        email for email in request.recipients if not EMAIL_REGEX.match(email)
    ]
    if invalid_emails:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "Invalid email addresses",
                "invalid": invalid_emails,
            },
        )

    try:
        reply_to = request.replyToEmail or None
        # TODO: Implement google-api-python-client Gmail delivery within services.
        # This calls the Gmail service boundary.
        await send_summary_email(
            recipients=request.recipients,
            summary_text=request.summary,
            subject=request.subject,
            reply_to_email=reply_to,
        )

        return EmailSendSuccessResponse(
            success=True,
            message="Summary sent successfully",
            sentTo=request.recipients,
        )
    except NotImplementedError as nie:
        return JSONResponse(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            content={
                "error": str(nie),
            },
        )
    except Exception as exc:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Failed to send email",
                "details": str(exc),
            },
        )
