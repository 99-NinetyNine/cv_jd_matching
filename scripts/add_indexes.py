import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import logging

# Add project root to path
sys.path.append(os.getcwd())

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/cv_matching")

def add_indexes():
    try:
        conn = psycopg2.connect(DB_URL)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        
        logger.info("Adding HNSW index to 'jobs' table...")
        # HNSW index for cosine distance
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_jobs_embedding 
            ON jobs USING hnsw (embedding vector_cosine_ops);
        """)
        logger.info("Successfully added index to 'jobs'.")
        
        logger.info("Adding HNSW index to 'cv' table...")
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_cv_embedding 
            ON cv USING hnsw (embedding vector_cosine_ops);
        """)
        logger.info("Successfully added index to 'cv'.")
        
        cur.close()
        conn.close()
        logger.info("Index creation complete.")
        
    except Exception as e:
        logger.error(f"Failed to add indexes: {e}")
        sys.exit(1)

if __name__ == "__main__":
    add_indexes()
