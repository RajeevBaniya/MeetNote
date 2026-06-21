-- Safely initialize vector extension if available
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_available_extensions WHERE name = 'vector') THEN
        CREATE EXTENSION IF NOT EXISTS vector;
    ELSE
        RAISE WARNING 'pgvector extension package (vector) is not physically installed on the database server.';
    END IF;
END $$;

-- Check if vector extension was successfully enabled before creating RAG tables
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN
        -- Create meeting_transcript_chunks table
        CREATE TABLE IF NOT EXISTS meeting_transcript_chunks (
            id UUID PRIMARY KEY,
            meeting_id UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
            speaker_name TEXT NULL,
            text_content TEXT NOT NULL,
            text_hash VARCHAR(64) NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            embedding vector(768) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_meeting_transcript_chunk_hash UNIQUE(meeting_id, text_hash)
        );

        -- Create meeting_summary_chunks table
        CREATE TABLE IF NOT EXISTS meeting_summary_chunks (
            id UUID PRIMARY KEY,
            meeting_id UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
            text_content TEXT NOT NULL,
            text_hash VARCHAR(64) NOT NULL,
            embedding vector(768) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_meeting_summary_chunk_hash UNIQUE(meeting_id, text_hash)
        );

        -- Create meeting_documents table
        CREATE TABLE IF NOT EXISTS meeting_documents (
            id UUID PRIMARY KEY,
            meeting_id UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
            filename VARCHAR(255) NOT NULL,
            storage_url TEXT NOT NULL,
            file_hash VARCHAR(64) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_meeting_documents_hash UNIQUE(meeting_id, file_hash)
        );

        -- Create meeting_document_chunks table
        CREATE TABLE IF NOT EXISTS meeting_document_chunks (
            id UUID PRIMARY KEY,
            document_id UUID NOT NULL REFERENCES meeting_documents(id) ON DELETE CASCADE,
            meeting_id UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
            text_content TEXT NOT NULL,
            text_hash VARCHAR(64) NOT NULL,
            embedding vector(768) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_meeting_document_chunks_hash UNIQUE(document_id, text_hash)
        );

        -- Create standard B-tree indexes for fast queries
        CREATE INDEX IF NOT EXISTS idx_transcript_chunks_meeting_active ON meeting_transcript_chunks(meeting_id, is_active);
        CREATE INDEX IF NOT EXISTS idx_summary_chunks_meeting ON meeting_summary_chunks(meeting_id);
        CREATE INDEX IF NOT EXISTS idx_documents_meeting ON meeting_documents(meeting_id);
        CREATE INDEX IF NOT EXISTS idx_document_chunks_meeting ON meeting_document_chunks(meeting_id);
        CREATE INDEX IF NOT EXISTS idx_document_chunks_document ON meeting_document_chunks(document_id);

        -- Create HNSW vector similarity indexes
        CREATE INDEX IF NOT EXISTS idx_transcript_chunks_embedding_hnsw
        ON meeting_transcript_chunks USING hnsw (embedding vector_cosine_ops);

        CREATE INDEX IF NOT EXISTS idx_summary_chunks_embedding_hnsw
        ON meeting_summary_chunks USING hnsw (embedding vector_cosine_ops);

        CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding_hnsw
        ON meeting_document_chunks USING hnsw (embedding vector_cosine_ops);
    ELSE
        RAISE WARNING 'Skipping RAG tables creation because vector extension is not enabled.';
    END IF;
END $$;
