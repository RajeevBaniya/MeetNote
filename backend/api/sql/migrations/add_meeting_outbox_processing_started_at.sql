-- Migration: Add processing_started_at to meeting_outbox table
ALTER TABLE meeting_outbox ADD COLUMN IF NOT EXISTS processing_started_at TIMESTAMPTZ NULL;
