from typing import Dict, Any, List
from sklearn.metrics.pairwise import cosine_similarity
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder
import numpy as np
from core.matching.base import BaseMatcher
from core.llm.factory import get_llm, get_embeddings
from langchain_core.prompts import PromptTemplate
import logging

logger = logging.getLogger(__name__)

from core.cache.simple_cache import embedding_cache, get_cache_key

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
        key = get_cache_key(text)
        cached = embedding_cache.get(key)
        if cached:
            return cached
        
        embedding = self.embeddings.embed_query(text)
        embedding_cache.set(key, embedding)
        return embedding
            
    def _get_text_representation(self, data: Dict[str, Any]) -> str:
        """Convert structured data to a text representation."""
        # Enhanced text representation
        text = ""
        if "basics" in data:
            text += f"Name: {data['basics'].get('name', '')}\n"
            text += f"Summary: {data['basics'].get('summary', '')}\n"
        
        if "skills" in data:
            skills = [s.get("name", "") for s in data["skills"]]
            text += f"Skills: {', '.join(skills)}\n"
            
        if "work" in data:
            for work in data["work"]:
                text += f"Role: {work.get('position', '')} at {work.get('company', '')}. {work.get('summary', '')}\n"
                
        if "title" in data: # For jobs
            text += f"Title: {data.get('title', '')}\n"
        if "description" in data: # For jobs
            text += f"Description: {data.get('description', '')}\n"
            
        return text

    def _explain_match(self, cv_text: str, job_text: str, score: float) -> str:
        """Generate an explanation for the match using LLM."""
        prompt = PromptTemplate(
            template="""You are an expert HR assistant. Explain why this candidate is a good match for the job.
            
            Candidate Profile:
            {cv_text}
            
            Job Description:
            {job_text}
            
            Match Score: {score}
            
            Provide a concise explanation (max 3 sentences) highlighting key matching skills and experience.
            """,
            input_variables=["cv_text", "job_text", "score"]
        )
        
        chain = prompt | self.llm
        try:
            return chain.invoke({"cv_text": cv_text[:1000], "job_text": job_text[:1000], "score": f"{score:.2f}"}).content
        except Exception as e:
            logger.error(f"Explanation failed: {e}")
            return "Could not generate explanation."

    def match(self, cv_data: Dict[str, Any], job_descriptions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not job_descriptions:
            return []
            
        cv_text = self._get_text_representation(cv_data)
        job_texts = [self._get_text_representation(job) for job in job_descriptions]
        
        # 1. Vector Search (Semantic)
        cv_embedding = self._get_embedding(cv_text)
        # For jobs, we assume they might be cached individually, but embed_documents is batch.
        # For simplicity in this demo, we'll just use embed_documents for now, 
        # but in production we'd cache job embeddings in DB.
        job_embeddings = self.embeddings.embed_documents(job_texts)
        semantic_scores = cosine_similarity([cv_embedding], job_embeddings)[0]
        
        # 2. Keyword Search (BM25)
        tokenized_jobs = [doc.split() for doc in job_texts]
        bm25 = BM25Okapi(tokenized_jobs)
        tokenized_cv = cv_text.split()
        keyword_scores = bm25.get_scores(tokenized_cv)
        
        # Normalize BM25 scores
        if len(keyword_scores) > 0 and max(keyword_scores) > 0:
            keyword_scores = keyword_scores / max(keyword_scores)
            
        # 3. Hybrid Score (Weighted Sum)
        # 0.7 Semantic + 0.3 Keyword
        hybrid_scores = 0.7 * semantic_scores + 0.3 * keyword_scores
        
        # Create initial results
        results = []
        for i, job in enumerate(job_descriptions):
            results.append({
                "job_id": job.get("job_id", f"job_{i}"),
                "initial_score": float(hybrid_scores[i]),
                "job_title": job.get("title", "Unknown"),
                "company": job.get("company", "Unknown"),
                "job_text": job_texts[i],
                "raw_job": job
            })
            
        # Sort by hybrid score
        results.sort(key=lambda x: x["initial_score"], reverse=True)
        
        # 4. Reranking (Top 10)
        top_k = results[:10]
        if self.reranker:
            pairs = [[cv_text, res["job_text"]] for res in top_k]
            rerank_scores = self.reranker.predict(pairs)
            
            for i, res in enumerate(top_k):
                # Sigmoid to normalize cross-encoder output if needed, but raw is often fine for ranking
                # Let's just use it as the final match score
                res["match_score"] = float(rerank_scores[i])
        else:
            for res in top_k:
                res["match_score"] = res["initial_score"]
                
        # Re-sort after reranking
        top_k.sort(key=lambda x: x["match_score"], reverse=True)
        
        # 5. Add Explanations (Top 3)
        for res in top_k[:3]:
            res["explanation"] = self._explain_match(cv_text, res["job_text"], res["match_score"])
            
        # Cold Start / Fallback
        # If no good matches found (score < threshold), recommend popular/random jobs
        if not top_k or top_k[0]["match_score"] < 0.2:
            logger.info("Low match scores, adding cold start recommendations.")
            # In a real app, fetch "popular" jobs from DB. Here we just take random ones.
            # We'll mark them as "Trending" or "Suggested"
            import random
            remaining = [j for j in job_descriptions if j["job_id"] not in [r["job_id"] for r in top_k]]
            if remaining:
                cold_start = random.sample(remaining, min(3, len(remaining)))
                for job in cold_start:
                    top_k.append({
                        "job_id": job["job_id"],
                        "job_title": job["title"],
                        "company": job["company"],
                        "match_score": 0.1, # Low score to indicate it's a suggestion
                        "explanation": "Suggested based on current job trends."
                    })
            
        # Cleanup internal fields
        final_results = []
        for res in top_k:
            final_results.append({
                "job_id": res["job_id"],
                "job_title": res["job_title"],
                "company": res["company"],
                "match_score": res["match_score"],
                "explanation": res.get("explanation", "Good match based on skills and experience.")
            })
            
        return final_results
