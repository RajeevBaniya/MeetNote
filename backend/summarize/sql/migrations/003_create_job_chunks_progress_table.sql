CREATE TABLE IF NOT EXISTS job_chunks_progress (
    id UUID PRIMARY KEY,
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    chunk_index INT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    summary TEXT NULL,
    action_items JSONB NULL DEFAULT '[]'::jsonb,
    decisions JSONB NULL DEFAULT '[]'::jsonb,
    deadlines JSONB NULL DEFAULT '[]'::jsonb,
    participants JSONB NULL DEFAULT '[]'::jsonb,
    retry_count INT NOT NULL DEFAULT 0,
    error TEXT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_job_chunks_progress_job_id ON job_chunks_progress (job_id);
CREATE INDEX IF NOT EXISTS idx_job_chunks_progress_chunk_index ON job_chunks_progress (chunk_index);
