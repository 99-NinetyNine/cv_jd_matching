from typing import Dict, Any, List, Optional
from sentence_transformers import CrossEncoder
import numpy as np
from core.matching.base import BaseMatcher
from core.llm.factory import get_llm
from langchain_core.prompts import PromptTemplate
import logging
from core.matching.embeddings import EmbeddingFactory
from core.matching.strategies import NaiveMatcherStrategy, PgvectorMatcherStrategy

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
            
    def _get_embedding(self, text: str) -> List[float]:
        return self.embedder.embed_query(text)

    def _get_text_representation(self, data: Dict[str, Any]) -> str:
        """
        Convert structured CV data (based on JSON Resume schema) to a text representation for embedding.
        
        Args:
            data: Dictionary containing CV data matching the core.parsing.schema.Resume structure.
            
        Returns:
            A single string concatenating key information for semantic search.
        """
        text = ""
        
        # Basics
        if "basics" in data:
            basics = data["basics"]
            text += f"Name: {basics.get('name', '')}\n"
            text += f"Label: {basics.get('label', '')}\n"
            text += f"Summary: {basics.get('summary', '')}\n"
            if "location" in basics and isinstance(basics["location"], dict):
                loc = basics["location"]
                text += f"Location: {loc.get('city', '')}, {loc.get('countryCode', '')}\n"
        
        # Skills
        if "skills" in data:
            skills_list = []
            for s in data["skills"]:
                if isinstance(s, dict):
                    name = s.get("name", "")
                    keywords = ", ".join(s.get("keywords", []))
                    skills_list.append(f"{name} ({keywords})" if keywords else name)
                else:
                    skills_list.append(str(s))
            text += f"Skills: {', '.join(skills_list)}\n"
            
        # Work Experience
        if "work" in data:
            text += "Work Experience:\n"
            for work in data["work"]:
                text += f"- {work.get('position', '')} at {work.get('name', '')}\n"
                if work.get('summary'):
                    text += f"  Summary: {work['summary']}\n"
                if work.get('highlights'):
                    text += f"  Highlights: {', '.join(work['highlights'])}\n"
        
        # Education
        if "education" in data:
            text += "Education:\n"
            for edu in data["education"]:
                text += f"- {edu.get('studyType', '')} in {edu.get('area', '')} at {edu.get('institution', '')}\n"
        
        # Projects
        if "projects" in data:
            text += "Projects:\n"
            for proj in data["projects"]:
                text += f"- {proj.get('name', '')}: {proj.get('description', '')}\n"
                if proj.get('highlights'):
                    text += f"  Highlights: {', '.join(proj['highlights'])}\n"

        # Certificates
        if "certificates" in data:
            certs = [f"{c.get('name', '')} from {c.get('issuer', '')}" for c in data["certificates"]]
            text += f"Certificates: {', '.join(certs)}\n"

        # Job specific fields (if data is a job description)
        if "title" in data: 
            text += f"Job Title: {data.get('title', '')}\n"
        if "description" in data: 
            text += f"Job Description: {data.get('description', '')}\n"
        if "company" in data:
            text += f"Company: {data.get('company', '')}\n"
            
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
        """Save job embedding using strategy."""
        job_text = self._get_text_representation(job_data)
        embedding = self._get_embedding(job_text)
        self.strategy.save_job(job_id, job_data, embedding)

    def match(self, cv_data: Dict[str, Any], job_candidates: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Match CV against jobs using the configured strategy.
        """
        cv_text = self._get_text_representation(cv_data)
        
        # 1. Get CV Embedding
        if "embedding" in cv_data and cv_data["embedding"]:
            cv_embedding = cv_data["embedding"]
        else:
            cv_embedding = self._get_embedding(cv_text)
            
        # 2. If job_candidates provided, save them (mostly for naive strategy or demo)
        if job_candidates:
            for job in job_candidates:
                job_id = job.get("job_id", str(hash(job.get("title", "") + job.get("company", ""))))
                self.save_job_embedding(job_id, job)
        
        # 3. Vector Search
        semantic_results = self.strategy.search(cv_embedding, limit=20)
        
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
