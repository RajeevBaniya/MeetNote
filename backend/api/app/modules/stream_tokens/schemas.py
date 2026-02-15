from pydantic import BaseModel


class StreamTokenIn(BaseModel):
    display_name: str | None = None
    passcode: str | None = None


class StreamTokenOut(BaseModel):
    token: str
    user_id: str
    expires_in_seconds: int
