from abc import ABC, abstractmethod
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import TRANSCRIPT_SIMILARITY_THRESHOLD, SUMMARY_SIMILARITY_THRESHOLD
from app.db.models import Meeting, MeetingParticipantStats, MeetingTranscriptChunk, MeetingSummaryChunk, MeetingTranscript, MeetingChatMessage


class MeetingChatRepositoryInterface(ABC):
    @abstractmethod
    async def check_user_membership(self, meeting_id: UUID, user_id: UUID) -> bool:
        """Verify user belongs to the meeting."""
        pass

    @abstractmethod
    async def get_meeting(self, meeting_id: UUID) -> Meeting | None:
        """Fetch meeting by ID."""
        pass

    @abstractmethod
    async def has_transcript_chunks(self, meeting_id: UUID) -> bool:
        """Check if any active transcript chunks exist."""
        pass

    @abstractmethod
    async def has_summary_chunks(self, meeting_id: UUID) -> bool:
        """Check if any summary chunks exist."""
        pass

    @abstractmethod
    async def has_transcript_records(self, meeting_id: UUID) -> bool:
        """Check if any transcript records exist in meeting_transcripts."""
        pass

    @abstractmethod
    async def search_transcript_chunks(
        self,
        meeting_id: UUID,
        query_emb: list[float],
        limit: int
    ) -> list[MeetingTranscriptChunk]:
        """Perform similarity search on transcript chunks."""
        pass

    @abstractmethod
    async def search_summary_chunks(
        self,
        meeting_id: UUID,
        query_emb: list[float],
        limit: int
    ) -> list[MeetingSummaryChunk]:
        """Perform similarity search on summary chunks."""
        pass

    @abstractmethod
    async def save_chat_message(
        self,
        meeting_id: UUID,
        user_id: UUID,
        role: str,
        content: str
    ) -> MeetingChatMessage:
        """Persist a chat message to database."""
        pass

    @abstractmethod
    async def get_chat_history(
        self,
        meeting_id: UUID,
        user_id: UUID
    ) -> list[MeetingChatMessage]:
        """Fetch chat history for the user and meeting, ordered by creation time."""
        pass

    @abstractmethod
    async def find_transcript_sequences_by_texts(
        self,
        meeting_id: UUID,
        texts: list[str]
    ) -> list[dict[str, object]]:
        """Fetch sequences and text content matching raw texts for legacy chunks."""
        pass

    @abstractmethod
    async def update_chunk_sequence(
        self,
        meeting_id: UUID,
        text_content: str,
        sequence: int
    ) -> None:
        """Lazily self-heal a legacy chunk sequence back to database."""
        pass

    @abstractmethod
    async def get_transcript_segments_by_sequences(
        self,
        meeting_id: UUID,
        sequences: list[int]
    ) -> list[MeetingTranscript]:
        """Retrieve transcript segments by sequence numbers, ordered chronologically."""
        pass


class MeetingChatRepository(MeetingChatRepositoryInterface):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def check_user_membership(self, meeting_id: UUID, user_id: UUID) -> bool:
        result = await self.session.execute(select(Meeting).where(Meeting.id == meeting_id))
        meeting = result.scalar_one_or_none()
        if not meeting:
            return False
        if user_id in (meeting.host_id, meeting.original_host_id, meeting.current_host_id):
            return True
        row = await self.session.execute(
            select(MeetingParticipantStats.user_id).where(
                MeetingParticipantStats.meeting_id == meeting_id,
                MeetingParticipantStats.user_id == user_id,
            ).limit(1)
        )
        return row.scalar_one_or_none() is not None

    async def get_meeting(self, meeting_id: UUID) -> Meeting | None:
        result = await self.session.execute(select(Meeting).where(Meeting.id == meeting_id))
        return result.scalar_one_or_none()

    async def has_transcript_chunks(self, meeting_id: UUID) -> bool:
        stmt = select(MeetingTranscriptChunk.id).where(
            MeetingTranscriptChunk.meeting_id == meeting_id,
            MeetingTranscriptChunk.is_active.is_(True)
        ).limit(1)
        res = await self.session.execute(stmt)
        return res.scalar() is not None

    async def has_summary_chunks(self, meeting_id: UUID) -> bool:
        stmt = select(MeetingSummaryChunk.id).where(
            MeetingSummaryChunk.meeting_id == meeting_id
        ).limit(1)
        res = await self.session.execute(stmt)
        return res.scalar() is not None

    async def has_transcript_records(self, meeting_id: UUID) -> bool:
        stmt = select(MeetingTranscript.id).where(
            MeetingTranscript.meeting_id == meeting_id
        ).limit(1)
        res = await self.session.execute(stmt)
        return res.scalar() is not None


    async def search_transcript_chunks(
        self,
        meeting_id: UUID,
        query_emb: list[float],
        limit: int
    ) -> list[MeetingTranscriptChunk]:
        dist = MeetingTranscriptChunk.embedding.cosine_distance(query_emb)
        stmt = (
            select(MeetingTranscriptChunk)
            .where(
                MeetingTranscriptChunk.meeting_id == meeting_id,
                MeetingTranscriptChunk.is_active.is_(True),
                dist <= (1.0 - TRANSCRIPT_SIMILARITY_THRESHOLD)
            )
            .order_by(dist.asc())
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def search_summary_chunks(
        self,
        meeting_id: UUID,
        query_emb: list[float],
        limit: int
    ) -> list[MeetingSummaryChunk]:
        dist = MeetingSummaryChunk.embedding.cosine_distance(query_emb)
        stmt = (
            select(MeetingSummaryChunk)
            .where(
                MeetingSummaryChunk.meeting_id == meeting_id,
                dist <= (1.0 - SUMMARY_SIMILARITY_THRESHOLD)
            )
            .order_by(dist.asc())
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def save_chat_message(
        self,
        meeting_id: UUID,
        user_id: UUID,
        role: str,
        content: str
    ) -> MeetingChatMessage:
        msg = MeetingChatMessage(
            meeting_id=meeting_id,
            user_id=user_id,
            role=role,
            content=content,
        )
        self.session.add(msg)
        await self.session.flush()
        return msg

    async def get_chat_history(
        self,
        meeting_id: UUID,
        user_id: UUID
    ) -> list[MeetingChatMessage]:
        stmt = (
            select(MeetingChatMessage)
            .where(
                MeetingChatMessage.meeting_id == meeting_id,
                MeetingChatMessage.user_id == user_id,
            )
            .order_by(MeetingChatMessage.created_at.asc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def find_transcript_sequences_by_texts(
        self,
        meeting_id: UUID,
        texts: list[str]
    ) -> list[dict[str, object]]:
        if not texts:
            return []
        stmt = (
            select(MeetingTranscript.sequence, MeetingTranscript.text_content)
            .where(
                MeetingTranscript.meeting_id == meeting_id,
                MeetingTranscript.text_content.in_(texts)
            )
        )
        res = await self.session.execute(stmt)
        return [{"sequence": row[0], "text_content": row[1]} for row in res.all()]

    async def update_chunk_sequence(
        self,
        meeting_id: UUID,
        text_content: str,
        sequence: int
    ) -> None:
        from sqlalchemy import update
        stmt = (
            update(MeetingTranscriptChunk)
            .where(
                MeetingTranscriptChunk.meeting_id == meeting_id,
                MeetingTranscriptChunk.text_content == text_content,
                MeetingTranscriptChunk.sequence.is_(None)
            )
            .values(sequence=sequence)
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def get_transcript_segments_by_sequences(
        self,
        meeting_id: UUID,
        sequences: list[int]
    ) -> list[MeetingTranscript]:
        if not sequences:
            return []
        stmt = (
            select(MeetingTranscript)
            .where(
                MeetingTranscript.meeting_id == meeting_id,
                MeetingTranscript.sequence.in_(sequences)
            )
            .order_by(MeetingTranscript.sequence.asc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())
