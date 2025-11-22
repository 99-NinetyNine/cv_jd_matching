-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create HNSW index for CV embeddings
CREATE INDEX ON cv USING hnsw (embedding vector_cosine_ops);

-- Create HNSW index for Job embeddings
CREATE INDEX ON job USING hnsw (embedding vector_cosine_ops);

-- Create index for Job ID
CREATE INDEX ON job (job_id);
