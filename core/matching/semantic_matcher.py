from typing import Dict, Any, List, Optional
from sklearn.metrics.pairwise import cosine_similarity
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder
import numpy as np
from core.matching.base import BaseMatcher
from core.llm.factory import get_llm
from langchain_core.prompts import PromptTemplate
import logging
from core.cache.redis_cache import redis_client
import json
import requests
import os
import psycopg2
from psycopg2.extras import Json

logger = logging.getLogger(__name__)

class HybridMatcher(BaseMatcher):
    def __init__(self, reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.llm = get_llm()
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.embedding_model = "nomic-embed-text" # Or any other model pulled in Ollama
        
        # Database connection for pgvector
        self.db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/cv_matching")
        
        # Initialize reranker
        try:
            self.reranker = CrossEncoder(reranker_model)
        except Exception as e:
            logger.warning(f"Failed to load reranker: {e}. Reranking will be disabled.")
            self.reranker = None
            
    def _get_embedding(self, text: str) -> List[float]:
        """Get embedding from Ollama with caching."""
        # Check Redis first
        import hashlib
        key = f"cv_embedding_ollama:{hashlib.md5(text.encode()).hexdigest()}"
        cached = redis_client.get(key)
        if cached:
            return np.frombuffer(cached, dtype=np.float64).tolist()
        
        try:
            response = requests.post(
                f"{self.ollama_base_url}/api/embeddings",
                json={
                    "model": self.embedding_model,
                    "prompt": text
                }
            )
            response.raise_for_status()
            embedding = response.json()["embedding"]
            
            # Cache it
            redis_client.set(key, np.array(embedding).tobytes(), ttl=86400)
            return embedding
        except Exception as e:
            logger.error(f"Failed to get embedding from Ollama: {e}")
            # Fallback or re-raise? For now, return empty list or raise
            raise e

    def _get_text_representation(self, data: Dict[str, Any]) -> str:
        """Convert structured data to a text representation."""
        text = ""
        if "basics" in data:
            text += f"Name: {data['basics'].get('name', '')}\n"
            text += f"Summary: {data['basics'].get('summary', '')}\n"
        
        if "skills" in data:
            skills = [s.get("name", "") if isinstance(s, dict) else str(s) for s in data.get("skills", [])]
            text += f"Skills: {', '.join(skills)}\n"
            
        if "work" in data:
            for work in data["work"]:
                text += f"Role: {work.get('position', '')} at {work.get('company', '')}. {work.get('summary', '')}\n"
                
        if "title" in data: # For jobs
            text += f"Title: {data.get('title', '')}\n"
        if "description" in data: # For jobs
            text += f"Description: {data.get('description', '')}\n"
            
        return text

    def _calculate_skills_score(self, cv_skills: List[str], job_skills: List[str]) -> float:
        if not cv_skills or not job_skills:
            return 0.0
        
        cv_set = set(s.lower() for s in cv_skills)
        job_set = set(s.lower() for s in job_skills)
        
        intersection = cv_set.intersection(job_set)
        if not job_set:
            return 0.0
        
        return len(intersection) / len(job_set)

    def _calculate_experience_score(self, cv_work: List[Dict], job_requirements: Dict) -> float:
        # Simplified experience scoring
        if cv_work:
            return 1.0
        return 0.0

    def _explain_match(self, cv_text: str, job_text: str, score: float, factors: Dict[str, float]) -> str:
        """Generate an explanation for the match using LLM."""
        prompt = PromptTemplate(
            template="""You are an expert HR assistant. Explain why this candidate is a good match for the job.
            
            Candidate Profile:
            {cv_text}
            
            Job Description:
            {job_text}
            
            Match Score: {score}
            Factors: {factors}
            
            Provide a concise explanation (max 3 sentences) highlighting key matching skills and experience.
            """,
            input_variables=["cv_text", "job_text", "score", "factors"]
        )
        
        chain = prompt | self.llm
        try:
            return chain.invoke({
                "cv_text": cv_text[:1000], 
                "job_text": job_text[:1000], 
                "score": f"{score:.2f}",
                "factors": str(factors)
            }).content
        except Exception as e:
            logger.error(f"Explanation failed: {e}")
            return "Could not generate explanation."

    def save_job_embedding(self, job_id: str, job_data: Dict[str, Any]):
        """Save job embedding to pgvector."""
        job_text = self._get_text_representation(job_data)
        embedding = self._get_embedding(job_text)
        
        conn = psycopg2.connect(self.db_url)
        cur = conn.cursor()
        try:
            # Ensure table exists (this should ideally be in a migration)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    data JSONB,
                    embedding vector(768)
                );
            """)
            # Create HNSW index if not exists
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
            logger.error(f"Failed to save job embedding: {e}")
            raise e
        finally:
            cur.close()
            conn.close()

    def search_jobs(self, cv_embedding: List[float], limit: int = 10) -> List[Dict[str, Any]]:
        """Search jobs using pgvector."""
        conn = psycopg2.connect(self.db_url)
        cur = conn.cursor()
        try:
            # HNSW search
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
            logger.error(f"Job search failed: {e}")
            return []
        finally:
            cur.close()
            conn.close()

    def match(self, cv_data: Dict[str, Any], job_candidates: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Match CV against jobs. 
        If job_candidates is provided, we might index them on the fly or just use them (but we prefer pgvector now).
        For this implementation, we assume jobs are already in DB or we insert them first if provided.
        """
        cv_text = self._get_text_representation(cv_data)
        
        # 1. Get CV Embedding
        if "embedding" in cv_data and cv_data["embedding"]:
            cv_embedding = cv_data["embedding"]
        else:
            cv_embedding = self._get_embedding(cv_text)
            
        # 2. If job_candidates provided, save them to DB first (for demo purposes)
        if job_candidates:
            for job in job_candidates:
                job_id = job.get("job_id", str(hash(job.get("title", "") + job.get("company", ""))))
                self.save_job_embedding(job_id, job)
        
        # 3. Vector Search (Semantic)
        # We search against ALL jobs in DB. In a real scenario, we might want to filter by job_candidates IDs if provided.
        # But here we assume we want to find best matches from the DB.
        semantic_results = self.search_jobs(cv_embedding, limit=20)
        
        if not semantic_results:
            return []

        # 4. Feature Matching & Reranking
        cv_skills = [s.get("name", "") if isinstance(s, dict) else str(s) for s in cv_data.get("skills", [])]
        
        results = []
        for res in semantic_results:
            job = res["data"]
            job_text = self._get_text_representation(job)
            
            # Skills Score
            skills_score = 0.5
            if "skills" in job:
                 job_skills = job["skills"]
                 skills_score = self._calculate_skills_score(cv_skills, job_skills)
            
            # Experience Score
            experience_score = self._calculate_experience_score(cv_data.get("work", []), job)
            
            # Semantic Score
            semantic_score = float(res["similarity"])
            
            # Weighted Sum
            final_score = (semantic_score * 0.5) + (skills_score * 0.3) + (experience_score * 0.2)
            
            results.append({
                "job_id": res["job_id"],
                "job_title": job.get("title", "Unknown"),
                "company": job.get("company", "Unknown"),
                "match_score": final_score,
                "matching_factors": {
                    "semantic_similarity": semantic_score,
                    "skills_match": skills_score,
                    "experience_match": experience_score
                },
                "job_text": job_text,
                "raw_job": job
            })
            
        # Sort by score
        results.sort(key=lambda x: x["match_score"], reverse=True)
        
        # 5. Reranking (Top 10)
        top_k = results[:10]
        if self.reranker:
            pairs = [[cv_text, res["job_text"]] for res in top_k]
            try:
                rerank_scores = self.reranker.predict(pairs)
                for i, res in enumerate(top_k):
                    res["match_score"] = (res["match_score"] + float(rerank_scores[i])) / 2
            except Exception as e:
                logger.warning(f"Reranking failed: {e}")
                
        # Re-sort
        top_k.sort(key=lambda x: x["match_score"], reverse=True)
        
        # 6. Explanations (Top 3)
        for res in top_k[:3]:
            res["explanation"] = self._explain_match(
                cv_text, 
                res["job_text"], 
                res["match_score"], 
                res["matching_factors"]
            )
            
        return top_k
