from uuid import UUID

from pydantic import BaseModel


class JoinMeetingIn(BaseModel):
    join_code: str
    passcode: str | None = None


class JoinMeetingOut(BaseModel):
    status: str
    meeting_id: UUID
    user_id: UUID
