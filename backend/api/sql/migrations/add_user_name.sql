-- Add optional display name to users for meeting UI (run on existing DBs that lack the column).
ALTER TABLE users ADD COLUMN IF NOT EXISTS name VARCHAR(255) NULL;

