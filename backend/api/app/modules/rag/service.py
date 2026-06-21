import hashlib
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import MeetingTranscriptChunk, MeetingSummaryChunk, RagFailedJob

logger = logging.getLogger(__name__)


def generate_chunk_hash(meeting_id: uuid.UUID, text_content: str) -> str:
    """Generates a stable normalized hash for deduplication within a meeting."""
    normalized = " ".join(text_content.strip().lower().split())
    hasher = hashlib.sha256()
    hasher.update(str(meeting_id).encode("utf-8"))
    hasher.update(b"|")
    hasher.update(normalized.encode("utf-8"))
    return hasher.hexdigest()


async def check_transcript_chunk_exists(
    session: AsyncSession,
    meeting_id: uuid.UUID,
    text_hash: str,
) -> bool:
    """Checks if a transcript chunk already exists in the database."""
    stmt = select(MeetingTranscriptChunk.id).where(
        MeetingTranscriptChunk.meeting_id == meeting_id,
        MeetingTranscriptChunk.text_hash == text_hash,
        MeetingTranscriptChunk.is_active.is_(True)
    ).limit(1)
    res = await session.execute(stmt)
    return res.scalar() is not None


async def check_summary_chunk_exists(
    session: AsyncSession,
    meeting_id: uuid.UUID,
    text_hash: str,
) -> bool:
    """Checks if a summary chunk already exists in the database."""
    stmt = select(MeetingSummaryChunk.id).where(
        MeetingSummaryChunk.meeting_id == meeting_id,
        MeetingSummaryChunk.text_hash == text_hash
    ).limit(1)
    res = await session.execute(stmt)
    return res.scalar() is not None


async def save_transcript_chunk(
    session: AsyncSession,
    meeting_id: uuid.UUID,
    speaker_name: Optional[str],
    text_content: str,
    text_hash: str,
    embedding: List[float],
) -> uuid.UUID:
    """Saves an active transcript chunk with its vector embedding."""
    chunk = MeetingTranscriptChunk(
        id=uuid.uuid4(),
        meeting_id=meeting_id,
        speaker_name=speaker_name,
        text_content=text_content,
        text_hash=text_hash,
        is_active=True,
        embedding=embedding,
    )
    session.add(chunk)
    await session.flush()
    return chunk.id


async def save_summary_chunk(
    session: AsyncSession,
    meeting_id: uuid.UUID,
    text_content: str,
    text_hash: str,
    embedding: List[float],
) -> uuid.UUID:
    """Saves a summary chunk with its vector embedding."""
    chunk = MeetingSummaryChunk(
        id=uuid.uuid4(),
        meeting_id=meeting_id,
        text_content=text_content,
        text_hash=text_hash,
        embedding=embedding,
    )
    session.add(chunk)
    await session.flush()
    return chunk.id


async def soft_delete_transcript_chunks(
    session: AsyncSession,
    meeting_id: uuid.UUID,
    text_hashes: List[str],
) -> None:
    """Soft-deletes transcript chunks by marking them inactive."""
    if not text_hashes:
        return
    stmt = select(MeetingTranscriptChunk).where(
        MeetingTranscriptChunk.meeting_id == meeting_id,
        MeetingTranscriptChunk.text_hash.in_(text_hashes),
        MeetingTranscriptChunk.is_active.is_(True)
    )
    res = await session.execute(stmt)
    for chunk in res.scalars().all():
        chunk.is_active = False
    await session.flush()


async def record_failed_job(
    session: AsyncSession,
    job_id: uuid.UUID,
    meeting_id: uuid.UUID,
    chunk_type: str,
    payload: Dict[str, Any],
    error_message: str,
) -> None:
    """Records a failed ingestion job or increments attempts on an existing failure record."""
    stmt = select(RagFailedJob).where(RagFailedJob.id == job_id)
    res = await session.execute(stmt)
    job = res.scalar_one_or_none()

    now = datetime.now(timezone.utc)
    if job:
        job.attempts += 1
        job.last_attempt_at = now
        job.error_message = error_message
        job.updated_at = now
        if job.attempts >= job.max_attempts:
            job.status = "dead_letter"
        else:
            job.status = "failed"
    else:
        job = RagFailedJob(
            id=job_id,
            meeting_id=meeting_id,
            chunk_type=chunk_type,
            payload=payload,
            status="failed",
            attempts=1,
            max_attempts=5,
            last_attempt_at=now,
            error_message=error_message,
        )
        session.add(job)
    await session.flush()


async def mark_failed_job_completed(
    session: AsyncSession,
    job_id: uuid.UUID,
) -> None:
    """Deletes or marks a failed job record as completed."""
    stmt = select(RagFailedJob).where(RagFailedJob.id == job_id)
    res = await session.execute(stmt)
    job = res.scalar_one_or_none()
    if job:
        await session.delete(job)
        await session.flush()
