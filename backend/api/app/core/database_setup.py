import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

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
    except Exception as exc:
        logger.exception("database_schema_setup_failed")
        raise RuntimeError("Database schema setup failed") from exc


async def _add_user_columns(conn):
    """Add missing columns to users table."""
    await conn.execute(
        text("ALTER TABLE users ADD COLUMN IF NOT EXISTS name VARCHAR(255) NULL")
    )


async def _add_meeting_columns(conn):
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


async def _create_analytics_tables(conn):
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


async def _create_analytics_indexes(conn):
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


async def _create_recordings_table(conn):
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


async def _create_recordings_indexes(conn):
    """Create indexes for recordings table."""
    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS idx_recordings_meeting_started "
            "ON recordings(meeting_id, started_at DESC)"
        )
    )


async def _ensure_lifecycle_constraints(conn):
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
    invalid_count = result.scalar()
    
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