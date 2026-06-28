import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from app.core.config import ENABLE_RAG

logger = logging.getLogger(__name__)


async def ensure_database_schema(engine: AsyncEngine) -> None:
    """
    Ensures all required database schema changes are applied.
    This handles incremental migrations for the MeetNote application.
    """
    try:
        async with engine.begin() as conn:
            await _add_user_columns(conn)
            await _add_meeting_columns(conn)
            await _create_analytics_tables(conn)
            await _create_analytics_indexes(conn)
            await _create_recordings_table(conn)
            await _create_recordings_indexes(conn)
            await _ensure_lifecycle_constraints(conn)
            await _create_outbox_table(conn)
            await _create_meeting_transcripts_table(conn)
            await _create_meeting_chat_messages_table(conn)
            if ENABLE_RAG:
                await _create_rag_tables(conn)
    except Exception as exc:
        logger.exception("database_schema_setup_failed")
        raise RuntimeError("Database schema setup failed") from exc


async def _create_outbox_table(conn: AsyncConnection) -> None:
    """Create meeting_outbox table and index if they don't exist."""
    await conn.execute(
        text(
            "CREATE TABLE IF NOT EXISTS meeting_outbox ("
            "id UUID PRIMARY KEY,"
            "event_type VARCHAR(50) NOT NULL,"
            "payload JSONB NOT NULL,"
            "status VARCHAR(20) NOT NULL DEFAULT 'pending',"
            "attempts INT NOT NULL DEFAULT 0,"
            "max_attempts INT NOT NULL DEFAULT 5,"
            "last_attempt_at TIMESTAMPTZ NULL,"
            "processing_started_at TIMESTAMPTZ NULL,"
            "created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),"
            "error_message TEXT NULL"
            ")"
        )
    )
    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS idx_meeting_outbox_status_attempts "
            "ON meeting_outbox(status, attempts)"
        )
    )


async def _add_user_columns(conn: AsyncConnection) -> None:
    """Add missing columns to users table."""
    await conn.execute(
        text("ALTER TABLE users ADD COLUMN IF NOT EXISTS name VARCHAR(255) NULL")
    )


async def _add_meeting_columns(conn: AsyncConnection) -> None:
    """Add missing columns to meetings table."""
    await conn.execute(
        text(
            "ALTER TABLE meetings "
            "ADD COLUMN IF NOT EXISTS ended_at TIMESTAMPTZ NULL"
        )
    )
    await conn.execute(
        text(
            "ALTER TABLE meetings "
            "ADD COLUMN IF NOT EXISTS host_joined BOOLEAN NOT NULL DEFAULT FALSE"
        )
    )
    await conn.execute(
        text(
            "ALTER TABLE meetings "
            "ADD COLUMN IF NOT EXISTS original_host_id UUID NULL"
        )
    )
    await conn.execute(
        text(
            "ALTER TABLE meetings "
            "ADD COLUMN IF NOT EXISTS current_host_id UUID NULL"
        )
    )
    
    # Populate host ID columns with existing host_id values
    await conn.execute(
        text(
            "UPDATE meetings "
            "SET original_host_id = host_id "
            "WHERE original_host_id IS NULL"
        )
    )
    await conn.execute(
        text(
            "UPDATE meetings "
            "SET current_host_id = host_id "
            "WHERE current_host_id IS NULL"
        )
    )
    
    # Make host ID columns required after population
    await conn.execute(
        text(
            "ALTER TABLE meetings "
            "ALTER COLUMN original_host_id SET NOT NULL"
        )
    )
    await conn.execute(
        text(
            "ALTER TABLE meetings "
            "ALTER COLUMN current_host_id SET NOT NULL"
        )
    )


async def _create_analytics_tables(conn: AsyncConnection) -> None:
    """Create analytics tables if they don't exist."""
    await conn.execute(
        text(
            "CREATE TABLE IF NOT EXISTS meeting_analytics ("
            "meeting_id UUID PRIMARY KEY REFERENCES meetings(id) ON DELETE CASCADE,"
            "started_at TIMESTAMPTZ NOT NULL,"
            "ended_at TIMESTAMPTZ NULL,"
            "duration_seconds INT NOT NULL DEFAULT 0,"
            "total_participants INT NOT NULL DEFAULT 0,"
            "host_transfers INT NOT NULL DEFAULT 0,"
            "transcript_segments INT NOT NULL DEFAULT 0,"
            "created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),"
            "updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"
            ")"
        )
    )
    await conn.execute(
        text(
            "CREATE TABLE IF NOT EXISTS meeting_participant_stats ("
            "meeting_id UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,"
            "user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,"
            "joined_at TIMESTAMPTZ NOT NULL,"
            "left_at TIMESTAMPTZ NULL,"
            "total_time_seconds INT NOT NULL DEFAULT 0,"
            "speaking_time_seconds INT NOT NULL DEFAULT 0,"
            "PRIMARY KEY (meeting_id, user_id)"
            ")"
        )
    )


async def _create_analytics_indexes(conn: AsyncConnection) -> None:
    """Create indexes for analytics tables."""
    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS idx_meeting_participant_stats_meeting "
            "ON meeting_participant_stats(meeting_id)"
        )
    )
    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS idx_meeting_participant_stats_user "
            "ON meeting_participant_stats(user_id)"
        )
    )
    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS idx_meeting_analytics_meeting "
            "ON meeting_analytics(meeting_id)"
        )
    )


async def _create_recordings_table(conn: AsyncConnection) -> None:
    """Create recordings table if it doesn't exist (metadata only)."""
    await conn.execute(
        text(
            "CREATE TABLE IF NOT EXISTS recordings ("
            "id UUID PRIMARY KEY,"
            "meeting_id UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,"
            "file_name VARCHAR(255) NULL,"
            "duration_seconds INT NOT NULL DEFAULT 0,"
            "started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),"
            "ended_at TIMESTAMPTZ NULL,"
            "created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"
            ")"
        )
    )


async def _create_recordings_indexes(conn: AsyncConnection) -> None:
    """Create indexes for recordings table."""
    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS idx_recordings_meeting_started "
            "ON recordings(meeting_id, started_at DESC)"
        )
    )


async def _ensure_lifecycle_constraints(conn: AsyncConnection) -> None:
    """Ensure meeting lifecycle constraints are properly set up."""
    # Check if is_active column exists
    check_result = await conn.execute(
        text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema = current_schema() AND table_name = 'meetings' AND column_name = 'is_active'"
        )
    )
    has_is_active = check_result.scalar() is not None
    
    if not has_is_active:
        return
    
    # Drop existing constraint and recreate
    await conn.execute(
        text(
            "ALTER TABLE meetings "
            "DROP CONSTRAINT IF EXISTS chk_meeting_lifecycle_consistency"
        )
    )
    await conn.execute(
        text(
            "ALTER TABLE meetings "
            "ADD CONSTRAINT chk_meeting_lifecycle_consistency "
            "CHECK ((is_active = true AND ended_at IS NULL) OR (is_active = false AND ended_at IS NOT NULL))"
        )
    )
    
    # Fix any inconsistent data
    result = await conn.execute(
        text(
            "SELECT COUNT(*) FROM meetings "
            "WHERE NOT ((is_active = true AND ended_at IS NULL) OR (is_active = false AND ended_at IS NOT NULL))"
        )
    )
    invalid_count = result.scalar() or 0
    
    if invalid_count > 0:
        logger.warning(
            "lifecycle_constraint_validation_failed",
            extra={"invalid_meetings_count": invalid_count},
        )
        await conn.execute(
            text(
                "UPDATE meetings "
                "SET ended_at = NOW() "
                "WHERE is_active = false AND ended_at IS NULL"
            )
        )
        await conn.execute(
            text(
                "UPDATE meetings "
                "SET is_active = false, ended_at = NOW() "
                "WHERE is_active = true AND ended_at IS NOT NULL"
            )
        )
        logger.info("lifecycle_constraint_data_fixed")


async def _create_rag_tables(conn: AsyncConnection) -> None:
    """Create RAG tables and vector indexes if RAG is enabled."""
    res = await conn.execute(
        text("SELECT 1 FROM pg_available_extensions WHERE name = 'vector'")
    )
    if not res.scalar():
        logger.warning("pgvector extension is not available on this server; skipping RAG tables creation")
        return

    await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

    await conn.execute(
        text(
            "CREATE TABLE IF NOT EXISTS rag_failed_jobs ("
            "id UUID PRIMARY KEY,"
            "meeting_id UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,"
            "chunk_type VARCHAR(32) NOT NULL,"
            "payload JSONB NOT NULL,"
            "status VARCHAR(20) NOT NULL DEFAULT 'failed',"
            "attempts INT NOT NULL DEFAULT 0,"
            "max_attempts INT NOT NULL DEFAULT 5,"
            "last_attempt_at TIMESTAMPTZ NULL,"
            "error_message TEXT NULL,"
            "created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),"
            "updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"
            ")"
        )
    )

    await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_rag_failed_jobs_status ON rag_failed_jobs(status)"))
    await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_rag_failed_jobs_attempts ON rag_failed_jobs(attempts)"))
    await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_rag_failed_jobs_last_attempt ON rag_failed_jobs(last_attempt_at)"))

    await conn.execute(
        text(
            "CREATE TABLE IF NOT EXISTS meeting_transcript_chunks ("
            "id UUID PRIMARY KEY,"
            "meeting_id UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,"
            "sequence INT NULL,"
            "speaker_name TEXT NULL,"
            "text_content TEXT NOT NULL,"
            "text_hash VARCHAR(64) NOT NULL,"
            "is_active BOOLEAN NOT NULL DEFAULT TRUE,"
            "embedding vector(768) NOT NULL,"
            "created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),"
            "CONSTRAINT uq_meeting_transcript_chunk_hash UNIQUE(meeting_id, text_hash)"
            ")"
        )
    )
    await conn.execute(
        text("ALTER TABLE meeting_transcript_chunks ADD COLUMN IF NOT EXISTS sequence INT NULL")
    )

    await conn.execute(
        text(
            "CREATE TABLE IF NOT EXISTS meeting_summary_chunks ("
            "id UUID PRIMARY KEY,"
            "meeting_id UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,"
            "text_content TEXT NOT NULL,"
            "text_hash VARCHAR(64) NOT NULL,"
            "embedding vector(768) NOT NULL,"
            "created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),"
            "CONSTRAINT uq_meeting_summary_chunk_hash UNIQUE(meeting_id, text_hash)"
            ")"
        )
    )

    await conn.execute(
        text(
            "CREATE TABLE IF NOT EXISTS meeting_documents ("
            "id UUID PRIMARY KEY,"
            "meeting_id UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,"
            "filename VARCHAR(255) NOT NULL,"
            "storage_url TEXT NOT NULL,"
            "file_hash VARCHAR(64) NOT NULL,"
            "created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),"
            "CONSTRAINT uq_meeting_documents_hash UNIQUE(meeting_id, file_hash)"
            ")"
        )
    )

    await conn.execute(
        text(
            "CREATE TABLE IF NOT EXISTS meeting_document_chunks ("
            "id UUID PRIMARY KEY,"
            "document_id UUID NOT NULL REFERENCES meeting_documents(id) ON DELETE CASCADE,"
            "meeting_id UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,"
            "text_content TEXT NOT NULL,"
            "text_hash VARCHAR(64) NOT NULL,"
            "embedding vector(768) NOT NULL,"
            "created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),"
            "CONSTRAINT uq_meeting_document_chunks_hash UNIQUE(document_id, text_hash)"
            ")"
        )
    )

    await conn.execute(
        text("CREATE INDEX IF NOT EXISTS idx_transcript_chunks_meeting_active ON meeting_transcript_chunks(meeting_id, is_active)")
    )
    await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_summary_chunks_meeting ON meeting_summary_chunks(meeting_id)"))
    await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_documents_meeting ON meeting_documents(meeting_id)"))
    await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_document_chunks_meeting ON meeting_document_chunks(meeting_id)"))
    await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_document_chunks_document ON meeting_document_chunks(document_id)"))

    await conn.execute(
        text("CREATE INDEX IF NOT EXISTS idx_transcript_chunks_embedding_hnsw ON meeting_transcript_chunks USING hnsw (embedding vector_cosine_ops)")
    )
    await conn.execute(
        text("CREATE INDEX IF NOT EXISTS idx_summary_chunks_embedding_hnsw ON meeting_summary_chunks USING hnsw (embedding vector_cosine_ops)")
    )
    await conn.execute(
        text("CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding_hnsw ON meeting_document_chunks USING hnsw (embedding vector_cosine_ops)")
    )


async def _create_meeting_transcripts_table(conn: AsyncConnection) -> None:
    """Create meeting_transcripts table if it doesn't exist."""
    await conn.execute(
        text(
            "CREATE TABLE IF NOT EXISTS meeting_transcripts ("
            "id UUID PRIMARY KEY,"
            "meeting_id UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,"
            "sequence INT NOT NULL,"
            "speaker_id VARCHAR(255) NULL,"
            "speaker_name VARCHAR(255) NULL,"
            "text_content TEXT NOT NULL,"
            "timestamp TIMESTAMPTZ NOT NULL,"
            "created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),"
            "CONSTRAINT uq_meeting_transcripts_seq UNIQUE (meeting_id, sequence)"
            ")"
        )
    )
    await conn.execute(
        text(
            "ALTER TABLE meeting_transcripts "
            "DROP CONSTRAINT IF EXISTS uq_meeting_transcripts_seq"
        )
    )
    await conn.execute(
        text(
            "ALTER TABLE meeting_transcripts "
            "ADD CONSTRAINT uq_meeting_transcripts_seq UNIQUE (meeting_id, sequence)"
        )
    )
    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS idx_meeting_transcripts_meeting_seq "
            "ON meeting_transcripts(meeting_id, sequence ASC)"
        )
    )
    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS idx_meeting_transcripts_created_at "
            "ON meeting_transcripts(created_at)"
        )
    )


async def _create_meeting_chat_messages_table(conn: AsyncConnection) -> None:
    """Create meeting_chat_messages table if it doesn't exist."""
    await conn.execute(
        text(
            "CREATE TABLE IF NOT EXISTS meeting_chat_messages ("
            "id UUID PRIMARY KEY,"
            "meeting_id UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,"
            "user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,"
            "role VARCHAR(20) NOT NULL,"
            "content TEXT NOT NULL,"
            "created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"
            ")"
        )
    )
    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS idx_meeting_chat_messages_meeting_user "
            "ON meeting_chat_messages(meeting_id, user_id, created_at ASC)"
        )
    )
