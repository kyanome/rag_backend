-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create indexes for better performance (will be added after data insertion)
-- Example: CREATE INDEX ON document_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Grant necessary permissions
GRANT ALL PRIVILEGES ON DATABASE ragdb TO raguser;

-- Set default search path
ALTER DATABASE ragdb SET search_path TO public;