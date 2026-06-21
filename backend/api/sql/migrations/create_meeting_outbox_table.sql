-- Create meeting_outbox table for transactional outbox pattern
CREATE TABLE IF NOT EXISTS meeting_outbox (
    id UUID PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,
    payload JSONB NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    attempts INT NOT NULL DEFAULT 0,
    max_attempts INT NOT NULL DEFAULT 5,
    last_attempt_at TIMESTAMPTZ NULL,
    processing_started_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    error_message TEXT NULL
);

-- Create index for polling optimization
CREATE INDEX IF NOT EXISTS idx_meeting_outbox_status_attempts ON meeting_outbox(status, attempts);
