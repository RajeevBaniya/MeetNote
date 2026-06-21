import os
import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)


async def ensure_database_schema(engine: AsyncEngine) -> None:
    # 1. Bootstrap schema_migrations table
    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                migration_filename VARCHAR(255) PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
        """))

    # 2. Identify migration scripts
    migrations_dir = os.path.abspath(
        os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "sql",
            "migrations",
        )
    )
    if not os.path.exists(migrations_dir):
        logger.warning("migrations_directory_not_found path=%s", migrations_dir)
        return

    migration_files = sorted(
        [f for f in os.listdir(migrations_dir) if f.endswith(".sql")]
    )

    # 3. Retrieve already applied migrations
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT migration_filename FROM schema_migrations"))
        applied_migrations = {row[0] for row in result.all()}

    # 4. Apply unapplied migrations sequentially
    for filename in migration_files:
        if filename in applied_migrations:
            continue

        filepath = os.path.join(migrations_dir, filename)
        logger.info("applying_db_migration file=%s", filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                sql_content = f.read().strip()

            if not sql_content:
                continue

            statements = [s.strip() for s in sql_content.split(";") if s.strip()]

            async with engine.begin() as conn:
                # Execute each statement in migration sequentially
                for statement in statements:
                    await conn.execute(text(statement))
                # Log application inside schema_migrations table
                await conn.execute(
                    text(
                        "INSERT INTO schema_migrations (migration_filename) "
                        "VALUES (:filename)"
                    ),
                    {"filename": filename},
                )
            logger.info("migration_applied_successfully file=%s", filename)
        except Exception as exc:
            logger.exception("migration_failed file=%s", filename)
            raise RuntimeError(f"Database migration failed on {filename}") from exc
