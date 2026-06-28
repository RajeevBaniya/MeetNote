from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.modules.auth.deps import get_current_user_id
from app.modules.meeting_chat.repository import MeetingChatRepository
from app.modules.meeting_chat.service import MeetingChatService

router = APIRouter(prefix="/meetings", tags=["meeting_chat"])


class ChatStatusOut(BaseModel):
    is_available: bool
    has_transcript: bool
    has_summary: bool
    transcript_ready: bool
    summary_ready: bool
    chat_mode: str


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatHistoryOut(BaseModel):
    history: list[ChatMessage]


class MeetingChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []


class MeetingChatResponse(BaseModel):
    response: str
    response_mode: str
    transcript_chunks_used: int
    summary_chunks_used: int


def get_chat_service(session: AsyncSession = Depends(get_session)) -> MeetingChatService:
    repo = MeetingChatRepository(session)
    return MeetingChatService(repo)


@router.get("/{meeting_id}/chat-status", response_model=ChatStatusOut)
async def get_chat_status(
    meeting_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    service: MeetingChatService = Depends(get_chat_service),
) -> ChatStatusOut:
    status_dict = await service.get_chat_status(meeting_id, user_id)
    return ChatStatusOut(
        is_available=bool(status_dict["is_available"]),
        has_transcript=bool(status_dict["has_transcript"]),
        has_summary=bool(status_dict["has_summary"]),
        transcript_ready=bool(status_dict["transcript_ready"]),
        summary_ready=bool(status_dict["summary_ready"]),
        chat_mode=str(status_dict["chat_mode"]),
    )


@router.get("/{meeting_id}/chat/history", response_model=ChatHistoryOut)
async def get_meeting_chat_history(
    meeting_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    service: MeetingChatService = Depends(get_chat_service),
) -> ChatHistoryOut:
    history_msgs = await service.get_chat_history(meeting_id, user_id)
    chat_messages = [
        ChatMessage(role=msg["role"], content=msg["content"])
        for msg in history_msgs
    ]
    return ChatHistoryOut(history=chat_messages)


@router.post("/{meeting_id}/chat", response_model=MeetingChatResponse)
async def post_meeting_chat(
    meeting_id: UUID,
    body: MeetingChatRequest,
    user_id: UUID = Depends(get_current_user_id),
    service: MeetingChatService = Depends(get_chat_service),
) -> MeetingChatResponse:
    history_dicts = [
        {"role": msg.role, "content": msg.content}
        for msg in body.history
    ]
    result = await service.get_chat_response(
        meeting_id=meeting_id,
        user_id=user_id,
        message=body.message,
        history=history_dicts,
    )
    return MeetingChatResponse(
        response=result.response,
        response_mode=result.response_mode,
        transcript_chunks_used=result.transcript_chunks_used,
        summary_chunks_used=result.summary_chunks_used,
    )
