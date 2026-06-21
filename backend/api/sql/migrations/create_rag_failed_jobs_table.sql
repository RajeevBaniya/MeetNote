-- Create RAG failed ingestion jobs table for retries
CREATE TABLE IF NOT EXISTS rag_failed_jobs (
    id UUID PRIMARY KEY,
    meeting_id UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    chunk_type VARCHAR(32) NOT NULL,
    payload JSONB NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'failed',
    attempts INT NOT NULL DEFAULT 0,
    max_attempts INT NOT NULL DEFAULT 5,
    last_attempt_at TIMESTAMPTZ NULL,
    error_message TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes to prevent retry scan degradation
CREATE INDEX IF NOT EXISTS idx_rag_failed_jobs_status
ON rag_failed_jobs(status);

CREATE INDEX IF NOT EXISTS idx_rag_failed_jobs_attempts
ON rag_failed_jobs(attempts);

CREATE INDEX IF NOT EXISTS idx_rag_failed_jobs_last_attempt
ON rag_failed_jobs(last_attempt_at);
