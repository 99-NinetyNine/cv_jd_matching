from typing import Dict, Any, List, Optional
from sentence_transformers import CrossEncoder
import numpy as np
from core.matching.base import BaseMatcher
from core.llm.factory import get_llm
from langchain_core.prompts import PromptTemplate
import logging
from core.matching.embeddings import EmbeddingFactory
from core.matching.strategies import NaiveMatcherStrategy, PgvectorMatcherStrategy
from core.services.cv_service import get_text_representation

logger = logging.getLogger(__name__)

class HybridMatcher(BaseMatcher):
    """
    A matcher that combines semantic search (vector similarity) with feature-based scoring (skills, experience).
    Supports multiple embedding providers (Ollama, Google) and search strategies (Pgvector, Naive).
    """
    def __init__(self, 
                 reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
                 embedding_provider: str = "ollama",
                 strategy: str = "pgvector",
                 **kwargs):
        """
        Initialize the HybridMatcher.

        Args:
            reranker_model: Name of the cross-encoder model for reranking.
            embedding_provider: 'ollama' or 'google'.
            strategy: 'pgvector' (database) or 'naive' (in-memory).
            **kwargs: Additional arguments passed to the embedder.
        """
        self.llm = get_llm()
        
        # Initialize Embedder
        self.embedder = EmbeddingFactory.get_embedder(provider=embedding_provider, **kwargs)
        
        # Initialize Strategy
        if strategy == "naive":
            self.strategy = NaiveMatcherStrategy()
        elif strategy == "pgvector":
            self.strategy = PgvectorMatcherStrategy()
        else:
            raise ValueError(f"Unknown strategy: {strategy}")
            
        # Initialize reranker
        try:
            self.reranker = CrossEncoder(reranker_model)
        except Exception as e:
            logger.warning(f"Failed to load reranker: {e}. Reranking will be disabled.")
            self.reranker = None
            
    def _get_embedding(self, text: str, entity_id: Optional[str] = None, entity_type: Optional[str] = None) -> List[float]:
        """Get embedding with optional ID-based caching."""
        if entity_id and entity_type and hasattr(self.embedder, 'embed_with_id'):
            return self.embedder.embed_with_id(text, entity_id, entity_type)
        return self.embedder.embed_query(text)

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
        """
        Generate an explanation for the match using LLM.
        For real-time requests, this calls LLM immediately.
        For batch processing, this might be skipped or handled differently.
        """
        # If we want to batch explanations, we shouldn't call this here for real-time requests
        # unless we are okay with waiting.
        # The user request implies batching "explain match" too.
        # This method is currently called by match() which is real-time.
        # To support batching, we'd need a separate flow where we save the match details 
        # and process them later.
        
        # For now, we'll keep the immediate implementation but return a placeholder if LLM fails
        # or if we decide to defer it.
        
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
        
        # return "very good!" # Placeholder
        
        try:
            chain = prompt | self.llm
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
        """Save job embedding using strategy with ID-based caching."""
        job_text = get_text_representation(job_data)
        embedding = self._get_embedding(job_text, entity_id=job_id, entity_type='job')
        self.strategy.save_job(job_id, job_data, embedding)

    def match(self, cv_id: str, job_candidates: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Match CV against jobs using the configured strategy.
        
        Args:
            cv_data: CV data dictionary
            job_candidates: Optional list of job candidates (for naive strategy)
            cv_id: Optional CV ID for ID-based embedding caching
        """
        print(f"[MATCH] Starting match process for CV ID: {cv_id}")
        print(f"[MATCH] Job candidates provided: {len(job_candidates) if job_candidates else 0}")
        
        # 1. Get CV Embedding (use ID-based caching if cv_id provided)
        print(f"[MATCH] Generating embedding with ID-based caching for CV: {cv_id}")
        cv_embedding = self._get_embedding(cv_text, entity_id=cv_id, entity_type='cv')
        
        # 2. If job_candidates provided, save them (mostly for naive strategy or demo)
        # not used in real case, just for studyinf purpose
        if job_candidates:
            print(f"[MATCH] Saving {len(job_candidates)} job candidates to strategy")
            for idx, job in enumerate(job_candidates):
                job_id = job.get("job_id", str(hash(job.get("title", "") + job.get("company", ""))))
                print(f"[MATCH] Saving job {idx+1}/{len(job_candidates)}: {job_id} - {job.get('title', 'Unknown')}")
                self.save_job_embedding(job_id, job)
        
        
        # 3. Vector Search - Convert NumPy array to list for pgvector compatibility
        import numpy as np
        embedding_for_search = cv_embedding.tolist() if isinstance(cv_embedding, np.ndarray) else cv_embedding
        print(f"[MATCH] Embedding type for search: {type(embedding_for_search)}, is numpy: {isinstance(cv_embedding, np.ndarray)}")
        print(f"[MATCH] Starting vector search with limit=20 using strategy: {type(self.strategy).__name__}")
        
        semantic_results = self.strategy.search(embedding_for_search, limit=20)
        print(f"[MATCH] Vector search returned {len(semantic_results)} results")
        
        if not semantic_results:
            logger.warning("[MATCH] No semantic results found, returning empty list")
            return []

        # 4. Feature Matching & Reranking
        cv_skills = [s.get("name", "") if isinstance(s, dict) else str(s) for s in cv_data.get("skills", [])]
        print(f"[MATCH] Extracted {len(cv_skills)} skills from CV: {cv_skills}")
        
        results = []
        for idx, res in enumerate(semantic_results):
            job = res["data"]
            job_id = res["job_id"]
            job_title = job.get("title", "Unknown")
            print(f"[MATCH] Processing result {idx+1}/{len(semantic_results)}: Job {job_id} - {job_title}")
            
            # TODO: Job test is different
            job_text = get_text_representation(job)
            print(f"[MATCH]   Job text length: {len(job_text)} chars")
            
            # Skills Score
            skills_score = 0.5
            if "skills" in job:
                 job_skills = job["skills"]
                 skills_score = self._calculate_skills_score(cv_skills, job_skills)
                 print(f"[MATCH]   Skills match: {skills_score:.3f} (CV: {len(cv_skills)}, Job: {len(job_skills)})")
            else:
                print(f"[MATCH]   No skills in job, using default score: {skills_score}")
            
            # Experience Score
            experience_score = self._calculate_experience_score(cv_data.get("work", []), job)
            print(f"[MATCH]   Experience score: {experience_score:.3f}")
            
            # Semantic Score
            semantic_score = float(res["similarity"])
            print(f"[MATCH]   Semantic similarity: {semantic_score:.3f}")
            
            # Weighted Sum
            final_score = (semantic_score * 0.5) + (skills_score * 0.3) + (experience_score * 0.2)
            print(f"[MATCH]   Final score: {final_score:.3f} (sem: {semantic_score*0.5:.3f}, skills: {skills_score*0.3:.3f}, exp: {experience_score*0.2:.3f})")
            
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
        print(f"[MATCH] Sorting {len(results)} results by match score")
        results.sort(key=lambda x: x["match_score"], reverse=True)
        print(f"[MATCH] Top 3 scores after sorting: {[r['match_score'] for r in results[:3]]}")
        
        # 5. Reranking (Top 10)
        top_k = results[:10]
        print(f"[MATCH] Reranking top {len(top_k)} results")
        if self.reranker:
            pairs = [[cv_text, res["job_text"]] for res in top_k]
            print(f"[MATCH] Created {len(pairs)} pairs for reranking")
            try:
                rerank_scores = self.reranker.predict(pairs)
                print(f"[MATCH] Reranker scores: {[float(s) for s in rerank_scores]}")
                for i, res in enumerate(top_k):
                    old_score = res["match_score"]
                    res["match_score"] = (res["match_score"] + float(rerank_scores[i])) / 2
                    print(f"[MATCH]   Job {i+1} score updated: {old_score:.3f} -> {res['match_score']:.3f}")
            except Exception as e:
                logger.warning(f"[MATCH] Reranking failed: {e}")
        else:
            print("[MATCH] No reranker available, skipping reranking")
                
        # Re-sort
        print("[MATCH] Re-sorting after reranking")
        top_k.sort(key=lambda x: x["match_score"], reverse=True)
        print(f"[MATCH] Top 3 scores after reranking: {[r['match_score'] for r in top_k[:3]]}")
        
        # 6. Explanations (Top 3)
        print(f"[MATCH] Generating explanations for top {min(3, len(top_k))} results")
        
        # Filter out low scores (e.g. < 0)
        final_results = []
        for idx, res in enumerate(top_k):
            if res["match_score"] < 0:
                print(f"[MATCH] Skipping result {idx+1} due to low score: {res['match_score']}")
                continue
            # To save test tokens
            if len(final_results) < 3:
                print(f"[MATCH] Generating explanation for result {idx+1}: {res['job_title']}")
                res["explanation"] = self._explain_match(
                    cv_text, 
                    res["job_text"], 
                    res["match_score"], 
                    res["matching_factors"]
                )
                print(f"[MATCH]   Explanation generated: {res['explanation'][:100]}...")
            
            final_results.append(res)
        
        print(f"[MATCH] Match process complete, returning {len(final_results)} results")
        return final_results
