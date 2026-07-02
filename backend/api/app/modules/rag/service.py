import hashlib
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import MeetingSummaryChunk, MeetingTranscriptChunk, MeetingTranscript, RagFailedJob, Meeting
from app.core.config import TRANSCRIPT_CHUNK_OVERLAP

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
    sequence: Optional[int] = None,
) -> uuid.UUID:
    """Saves an active transcript chunk with its vector embedding."""
    chunk = MeetingTranscriptChunk(
        id=uuid.uuid4(),
        meeting_id=meeting_id,
        sequence=sequence,
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


async def process_rag_ingestion_job(
    session: AsyncSession,
    client: Any,
    meeting_id: uuid.UUID,
    chunk_type: str,
    text_content: str,
    speaker_name: Optional[str] = None,
    sequence: Optional[int] = None,
) -> bool:
    """Processes a single RAG ingestion job: handles exists check, overlap generation, embedding, and save."""
    # 1. Verify meeting still exists before doing any database operations
    meeting_exists = await session.scalar(
        select(1).select_from(Meeting).where(Meeting.id == meeting_id).limit(1)
    )
    if not meeting_exists:
        logger.info("Meeting %s does not exist. Skipping RAG ingestion.", meeting_id)
        return True

    text_hash = generate_chunk_hash(meeting_id, text_content)

    if chunk_type == "transcript":
        exists = await check_transcript_chunk_exists(session, meeting_id, text_hash)
    elif chunk_type == "summary":
        exists = await check_summary_chunk_exists(session, meeting_id, text_hash)
    else:
        logger.warning("Unknown chunk type: %s", chunk_type)
        return True

    if exists:
        logger.info("Duplicate RAG chunk detected (meeting_id=%s, text_hash=%s, type=%s), skipping insert.", meeting_id, text_hash, chunk_type)
        return True

    # Build overlapping text for transcript chunks
    embedding_text = text_content
    if chunk_type == "transcript" and sequence is not None and TRANSCRIPT_CHUNK_OVERLAP > 0:
        prev_seqs = list(range(max(1, sequence - TRANSCRIPT_CHUNK_OVERLAP), sequence))
        if prev_seqs:
            stmt = (
                select(MeetingTranscript)
                .where(
                    MeetingTranscript.meeting_id == meeting_id,
                    MeetingTranscript.sequence.in_(prev_seqs)
                )
                .order_by(MeetingTranscript.sequence.asc())
            )
            res = await session.execute(stmt)
            prev_segs = res.scalars().all()
            
            lines = [f"[{s.speaker_name or 'Unknown Speaker'}]: {s.text_content.strip()}" for s in prev_segs]
            current_line = f"[{speaker_name or 'Unknown Speaker'}]: {text_content.strip()}"
            embedding_text = "\n".join(lines + [current_line])
        else:
            embedding_text = f"[{speaker_name or 'Unknown Speaker'}]: {text_content.strip()}"

    embedding = await client.embed_content(embedding_text)

    try:
        if chunk_type == "transcript":
            await save_transcript_chunk(
                session=session,
                meeting_id=meeting_id,
                speaker_name=speaker_name,
                text_content=text_content,
                text_hash=text_hash,
                embedding=embedding,
                sequence=sequence,
            )
        elif chunk_type == "summary":
            await save_summary_chunk(
                session=session,
                meeting_id=meeting_id,
                text_content=text_content,
                text_hash=text_hash,
                embedding=embedding,
            )
    except Exception as exc:
        from sqlalchemy.exc import IntegrityError
        if isinstance(exc, IntegrityError):
            logger.info("Duplicate RAG chunk insert prevented by database uniqueness constraint (meeting_id=%s, text_hash=%s, type=%s).", meeting_id, text_hash, chunk_type)
            return True
        raise exc

    return True
