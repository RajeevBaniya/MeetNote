CREATE TABLE IF NOT EXISTS schema_migrations (
    migration_filename VARCHAR(255) PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
