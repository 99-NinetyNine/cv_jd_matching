-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- ========================================
-- VECTOR INDICES (for similarity search)
-- ========================================

-- Create HNSW index for CV embeddings (optimized for cosine similarity)
CREATE INDEX IF NOT EXISTS idx_cv_embedding_hnsw ON cv USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

-- Create HNSW index for Job embeddings (optimized for cosine similarity)
CREATE INDEX IF NOT EXISTS idx_job_embedding_hnsw ON job USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

-- Alternative: IVFFlat index (faster build, less accurate)
-- CREATE INDEX IF NOT EXISTS idx_cv_embedding_ivfflat ON cv USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
-- CREATE INDEX IF NOT EXISTS idx_job_embedding_ivfflat ON job USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ========================================
-- STATUS INDICES (for filtering)
-- ========================================

-- CV status indices
CREATE INDEX IF NOT EXISTS idx_cv_parsing_status ON cv (parsing_status);
CREATE INDEX IF NOT EXISTS idx_cv_embedding_status ON cv (embedding_status);
CREATE INDEX IF NOT EXISTS idx_cv_is_latest ON cv (is_latest);
CREATE INDEX IF NOT EXISTS idx_cv_batch_id ON cv (batch_id) WHERE batch_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_cv_owner_id ON cv (owner_id) WHERE owner_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_cv_last_analyzed ON cv (last_analyzed) WHERE last_analyzed IS NOT NULL;

-- Job status indices
CREATE INDEX IF NOT EXISTS idx_job_embedding_status ON job (embedding_status);
CREATE INDEX IF NOT EXISTS idx_job_owner_id ON job (owner_id) WHERE owner_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_job_created_at ON job (created_at DESC);

-- ========================================
-- PRIMARY KEY INDICES
-- ========================================

-- Job ID (for lookups)
CREATE INDEX IF NOT EXISTS idx_job_job_id ON job (job_id);

-- ========================================
-- INTERACTION & ANALYTICS INDICES
-- ========================================

-- User interactions
CREATE INDEX IF NOT EXISTS idx_interaction_user_id ON userinteraction (user_id);
CREATE INDEX IF NOT EXISTS idx_interaction_job_id ON userinteraction (job_id);
CREATE INDEX IF NOT EXISTS idx_interaction_action ON userinteraction (action);
CREATE INDEX IF NOT EXISTS idx_interaction_timestamp ON userinteraction (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_interaction_metadata ON userinteraction USING gin (interaction_metadata jsonb_path_ops);

-- Predictions
CREATE INDEX IF NOT EXISTS idx_prediction_cv_id ON prediction (cv_id);
CREATE INDEX IF NOT EXISTS idx_prediction_prediction_id ON prediction (prediction_id);
CREATE INDEX IF NOT EXISTS idx_prediction_created_at ON prediction (created_at DESC);

-- Applications
CREATE INDEX IF NOT EXISTS idx_application_cv_id ON application (cv_id);
CREATE INDEX IF NOT EXISTS idx_application_job_id ON application (job_id);
CREATE INDEX IF NOT EXISTS idx_application_prediction_id ON application (prediction_id);
CREATE INDEX IF NOT EXISTS idx_application_status ON application (status);
CREATE INDEX IF NOT EXISTS idx_application_applied_at ON application (applied_at DESC);

-- ========================================
-- BATCH PROCESSING INDICES
-- ========================================

-- Batch jobs
CREATE INDEX IF NOT EXISTS idx_batchjob_batch_id ON batchjob (batch_id);
CREATE INDEX IF NOT EXISTS idx_batchjob_status ON batchjob (status);
CREATE INDEX IF NOT EXISTS idx_batchjob_type ON batchjob (type);
CREATE INDEX IF NOT EXISTS idx_batchjob_created_at ON batchjob (created_at DESC);

-- Batch requests (OpenAI)
CREATE INDEX IF NOT EXISTS idx_batchrequest_batch_api_id ON batchrequest (batch_api_id);
CREATE INDEX IF NOT EXISTS idx_batchrequest_status ON batchrequest (status);
CREATE INDEX IF NOT EXISTS idx_batchrequest_batch_type ON batchrequest (batch_type);

-- ========================================
-- SYSTEM METRICS INDICES
-- ========================================

-- System metrics
CREATE INDEX IF NOT EXISTS idx_systemmetric_name ON systemmetric (name);
CREATE INDEX IF NOT EXISTS idx_systemmetric_timestamp ON systemmetric (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_systemmetric_name_timestamp ON systemmetric (name, timestamp DESC);

-- ========================================
-- COMPOSITE INDICES (for common queries)
-- ========================================

-- Find completed CVs for matching
CREATE INDEX IF NOT EXISTS idx_cv_completed_latest ON cv (embedding_status, is_latest, last_analyzed)
WHERE embedding_status = 'completed' AND is_latest = true;

-- Find pending batch CVs
CREATE INDEX IF NOT EXISTS idx_cv_pending_batch ON cv (parsing_status, embedding_status, created_at)
WHERE parsing_status = 'pending_batch' OR embedding_status = 'pending_batch';

-- Find completed jobs for matching
CREATE INDEX IF NOT EXISTS idx_job_completed ON job (embedding_status, created_at)
WHERE embedding_status = 'completed';

-- ========================================
-- ANALYZE TABLES (update statistics)
-- ========================================

ANALYZE cv;
ANALYZE job;
ANALYZE userinteraction;
ANALYZE prediction;
ANALYZE application;
ANALYZE systemmetric;
