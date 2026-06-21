CREATE TABLE IF NOT EXISTS jobs (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    progress_percentage INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ NULL,
    failure_reason TEXT NULL,
    result_summary_id UUID NULL REFERENCES summaries(id) ON DELETE SET NULL,
    file_name TEXT NULL,
    file_size INT NULL,
    file_path TEXT NULL,
    upload_path TEXT NULL,
    file_deleted_at TIMESTAMPTZ NULL,
    instruction TEXT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_jobs_user_id_created_at ON jobs (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs (status);
