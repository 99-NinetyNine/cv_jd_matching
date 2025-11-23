from typing import Dict, Any, List, Optional
from sklearn.metrics.pairwise import cosine_similarity
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder
import numpy as np
from core.matching.base import BaseMatcher
from core.llm.factory import get_llm, get_embeddings
from langchain_core.prompts import PromptTemplate
import logging
from core.cache.redis_cache import redis_client
import json

logger = logging.getLogger(__name__)

class HybridMatcher(BaseMatcher):
    def __init__(self, reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.embeddings = get_embeddings()
        self.llm = get_llm()
        # Initialize reranker (lazy load might be better for startup time, but eager is fine for now)
        try:
            self.reranker = CrossEncoder(reranker_model)
        except Exception as e:
            logger.warning(f"Failed to load reranker: {e}. Reranking will be disabled.")
            self.reranker = None
            
    def _get_embedding(self, text: str) -> List[float]:
        """Get embedding with caching."""
        # Check Redis first
        import hashlib
        key = f"cv_embedding:{hashlib.md5(text.encode()).hexdigest()}"
        cached = redis_client.get(key)
        if cached:
            return np.frombuffer(cached, dtype=np.float64).tolist() # Assuming stored as bytes
        
        embedding = self.embeddings.embed_query(text)
        # Cache it
        redis_client.set(key, np.array(embedding).tobytes(), ttl=86400)
        return embedding
            
    def _get_text_representation(self, data: Dict[str, Any]) -> str:
        """Convert structured data to a text representation."""
        # Enhanced text representation
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
        # In a real system, parse years of experience from CV and compare with job reqs
        # Here we just check if there is any work experience
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

    def match(self, cv_data: Dict[str, Any], job_candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Match CV against a list of job candidates.
        job_candidates should ideally contain pre-computed embeddings.
        """
        if not job_candidates:
            return []
            
        cv_text = self._get_text_representation(cv_data)
        
        # 1. Get CV Embedding
        if "embedding" in cv_data and cv_data["embedding"]:
            cv_embedding = cv_data["embedding"]
        else:
            cv_embedding = self._get_embedding(cv_text)
            
        # 2. Prepare Job Embeddings
        job_embeddings = []
        valid_jobs = []
        
        for job in job_candidates:
            if "embedding" in job and job["embedding"]:
                job_embeddings.append(job["embedding"])
                valid_jobs.append(job)
            else:
                # Fallback: compute embedding (slow)
                job_text = self._get_text_representation(job)
                emb = self._get_embedding(job_text)
                job_embeddings.append(emb)
                valid_jobs.append(job)
        
        if not job_embeddings:
            return []

        # 3. Vector Search (Semantic)
        semantic_scores = cosine_similarity([cv_embedding], job_embeddings)[0]
        
        # 4. Feature Matching
        cv_skills = [s.get("name", "") if isinstance(s, dict) else str(s) for s in cv_data.get("skills", [])]
        
        results = []
        for i, job in enumerate(valid_jobs):
            # Extract job skills (mocking extraction if not present)
            # In real system, job should have structured skills
            job_text = self._get_text_representation(job)
            job_skills = [] # TODO: Extract skills from job description or use structured data
            
            # Skills Score
            skills_score = 0.5 # Default if no structured skills
            if "skills" in job:
                 job_skills = job["skills"]
                 skills_score = self._calculate_skills_score(cv_skills, job_skills)
            
            # Experience Score
            experience_score = self._calculate_experience_score(cv_data.get("work", []), job)
            
            # Semantic Score
            semantic_score = float(semantic_scores[i])
            
            # Weighted Sum
            # Weights: Semantic (50%), Skills (30%), Experience (20%)
            final_score = (semantic_score * 0.5) + (skills_score * 0.3) + (experience_score * 0.2)
            
            results.append({
                "job_id": job.get("job_id", f"job_{i}"),
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
                    # Reranker score is usually logits, need sigmoid or just use as is for ranking
                    # We blend it with the initial score
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
