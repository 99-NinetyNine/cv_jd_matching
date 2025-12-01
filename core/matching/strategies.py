from typing import List, Dict, Any, Protocol
from sklearn.metrics.pairwise import cosine_similarity
import psycopg2
from psycopg2.extras import Json
import os
import logging
from core.matching.embeddings import Embedder

logger = logging.getLogger(__name__)

class MatcherStrategy(Protocol):
    def search(self, cv_embedding: List[float], limit: int = 50) -> List[Dict[str, Any]]:
        ...
    def save_job(self, job_id: str, job_data: Dict[str, Any], embedding: List[float]):
        ...

class NaiveMatcherStrategy:
    """In-memory cosine similarity search."""
    def __init__(self):
        self.jobs = [] # List of {id, data, embedding}

    def save_job(self, job_id: str, job_data: Dict[str, Any], embedding: List[float]):
        # Check if exists
        for j in self.jobs:
            if j["id"] == job_id:
                j["data"] = job_data
                j["embedding"] = embedding
                return
        self.jobs.append({"id": job_id, "data": job_data, "embedding": embedding})

    def search(self, cv_embedding: List[float], limit: int = 50) -> List[Dict[str, Any]]:
        if not self.jobs:
            return []
        
        job_embeddings = [j["embedding"] for j in self.jobs]
        scores = cosine_similarity([cv_embedding], job_embeddings)[0]
        
        results = []
        for i, score in enumerate(scores):
            results.append({
                "job_id": self.jobs[i]["id"],
                "data": self.jobs[i]["data"],
                "similarity": float(score)
            })
        
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:limit]

class PgvectorMatcherStrategy:
    """
    Strategy for searching jobs using PostgreSQL's pgvector extension.
    Efficient for large datasets using HNSW indexing.
    """
    def __init__(self, db_url: str = None):
        """
        Args:
            db_url: Database connection string. Defaults to env var DATABASE_URL.
        """
        self.db_url = db_url or os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/cv_matching")

    def save_job(self, job_id: str, job_data: Dict[str, Any], embedding: List[float]):
        """Save job and its embedding to the database."""
        # DEPRECATED
        conn = psycopg2.connect(self.db_url)
        cur = conn.cursor()
        try:
            # Ensure table exists (should be in migration)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    data JSONB,
                    embedding vector(768)
                );
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS jobs_embedding_idx ON jobs USING hnsw (embedding vector_cosine_ops);
            """)
            
            cur.execute("""
                INSERT INTO jobs (id, data, embedding)
                VALUES (%s, %s, %s)
                ON CONFLICT (id) DO UPDATE 
                SET data = EXCLUDED.data, embedding = EXCLUDED.embedding;
            """, (job_id, Json(job_data), embedding))
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to save job to pgvector: {e}")
            raise e
        finally:
            cur.close()
            conn.close()

    def search(self, cv_embedding: List[float], limit: int = 50) -> List[Dict[str, Any]]:
        conn = psycopg2.connect(self.db_url)
        cur = conn.cursor()
        try:
            # TODO those jobs whose embedding status is not pending or others
            cur.execute("""
                SELECT id, data, 1 - (embedding <=> %s::vector) as similarity
                FROM jobs
                ORDER BY embedding <=> %s::vector
                LIMIT %s;
            """, (cv_embedding, cv_embedding, limit))
            
            results = []
            for row in cur.fetchall():
                results.append({
                    "job_id": row[0],
                    "data": row[1],
                    "similarity": row[2]
                })
            return results
        except Exception as e:
            logger.error(f"Pgvector search failed: {e}")
            return []
        finally:
            cur.close()
            conn.close()
