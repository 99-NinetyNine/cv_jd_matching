from typing import Dict, Any, List, Optional, TypedDict
from langgraph.graph import StateGraph, END
from sentence_transformers import CrossEncoder
import numpy as np
import logging
import psycopg2
import os
from core.matching.embeddings import EmbeddingFactory
from core.services.cv_service import get_cv_text_representation
from core.services.job_service import get_job_text_representation
from core.llm.factory import get_llm
from langchain_core.prompts import PromptTemplate
from core.matching.skills_analyzer import SkillsAnalyzer
from core.matching.matching_factors import MatchingFactorsCalculator

logger = logging.getLogger(__name__)

# Define State
class MatcherState(TypedDict):
    cv_text: str
    cv_data: Dict[str, Any]  # Full CV data for detailed analysis
    cv_embedding: List[float]
    matches: List[Dict[str, Any]]
    final_results: List[Dict[str, Any]]

class GraphMatcher:
    """
    LangGraph-based matcher that treats CV matching as a RAG workflow.
    """
    def __init__(self, 
                 reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
                 embedding_provider: str = "ollama",
                 db_url: str = None,
                 **kwargs):
        
        self.db_url = db_url or os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/cv_matching")
        self.embedder = EmbeddingFactory.get_embedder(provider=embedding_provider, **kwargs)
        self.llm = get_llm()
        self.skills_analyzer = SkillsAnalyzer()
        self.factors_calculator = MatchingFactorsCalculator()
        
        try:
            self.reranker = CrossEncoder(reranker_model)
        except Exception as e:
            logger.warning(f"Failed to load reranker: {e}. Reranking will be disabled.")
            self.reranker = None
            
        # Build Graph
        self.app = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(MatcherState)
        
        # Add Nodes
        workflow.add_node("embed", self.embed_cv)
        workflow.add_node("retrieve", self.retrieve_jobs)
        workflow.add_node("rerank", self.rerank_jobs)
        workflow.add_node("analyze_factors", self.analyze_factors)
        workflow.add_node("explain", self.explain_matches)
        
        # Add Edges
        workflow.set_entry_point("embed")
        workflow.add_edge("embed", "retrieve")
        workflow.add_edge("retrieve", "rerank")
        workflow.add_edge("rerank", "analyze_factors")
        workflow.add_edge("analyze_factors", "explain")
        workflow.add_edge("explain", END)
        
        return workflow.compile()

    def embed_cv(self, state: MatcherState):
        """Generate embedding for the CV."""
        print("[GRAPH] Node: embed_cv")
        text = state["cv_text"]
        embedding = self.embedder.embed_query(text)
        return {"cv_embedding": embedding}

    def retrieve_jobs(self, state: MatcherState):
        """Retrieve top candidates using pgvector."""
        print("[GRAPH] Node: retrieve_jobs")
        embedding = state["cv_embedding"]

        conn = psycopg2.connect(self.db_url)
        cur = conn.cursor()
        try:
            # Optimized vector search - use data JSON column and canonical_text
            cur.execute("""
                SELECT id, data, canonical_text, 1 - (embedding <=> %s::vector) as similarity
                FROM job
                WHERE embedding_status = 'completed'
                ORDER BY embedding <=> %s::vector
                LIMIT 20;
            """, (embedding, embedding))

            results = []
            for row in cur.fetchall():
                results.append({
                    "job_id": row[0],
                    "data": row[1],  # Complete job data as JSON
                    "similarity": float(row[3]),
                    "job_text": row[2]  # Pre-computed canonical_text
                })
            
            print(f"[GRAPH] Retrieved {len(results)} candidates")
            return {"matches": results}
        except Exception as e:
            logger.error(f"Retrieval failed: {e}")
            return {"matches": []}
        finally:
            cur.close()
            conn.close()

    def rerank_jobs(self, state: MatcherState):
        """Rerank candidates using CrossEncoder."""
        print("[GRAPH] Node: rerank_jobs")
        matches = state["matches"]
        cv_text = state["cv_text"]
        
        if not matches:
            return {"matches": []}
            
        if self.reranker:
            pairs = [[cv_text, m["job_text"]] for m in matches]
            try:
                scores = self.reranker.predict(pairs)
                for i, m in enumerate(matches):
                    # Combine scores (50% semantic, 50% reranker)
                    m["match_score"] = (m["similarity"] + float(scores[i])) / 2
            except Exception as e:
                logger.warning(f"Reranking failed: {e}")
                for m in matches:
                    m["match_score"] = m["similarity"]
        else:
             for m in matches:
                m["match_score"] = m["similarity"]
                
        # Sort
        matches.sort(key=lambda x: x["match_score"], reverse=True)
        # Keep top 10 for detailed analysis
        return {"matches": matches[:10]}
    
    def analyze_factors(self, state: MatcherState):
        """Analyze detailed matching factors for each match."""
        print("[GRAPH] Node: analyze_factors")
        matches = state["matches"]
        cv_data = state["cv_data"]
        
        if not matches:
            return {"matches": []}
        
        enhanced_matches = []
        
        for match in matches:
            job_data = match["data"]
            semantic_similarity = match["match_score"]
            
            # Analyze skills
            skills_analysis = self.skills_analyzer.analyze(cv_data, job_data)
            
            # Calculate all matching factors
            matching_factors = self.factors_calculator.calculate_all_factors(
                cv_data=cv_data,
                job_data=job_data,
                semantic_similarity=semantic_similarity,
                skills_match=skills_analysis["skills_match"]
            )
            
            # Calculate overall match score (weighted average)
            overall_score = (
                matching_factors["skills_match"] * 0.35 +
                matching_factors["experience_match"] * 0.25 +
                matching_factors["education_match"] * 0.15 +
                matching_factors["semantic_similarity"] * 0.25
            )
            
            # Enhance match with detailed factors
            match["matching_factors"] = matching_factors
            match["matched_skills"] = skills_analysis["matched_skills"]
            match["missing_skills"] = skills_analysis["missing_skills"]
            match["match_score"] = overall_score  # Update with weighted score
            
            enhanced_matches.append(match)
        
        # Re-sort by new overall score
        enhanced_matches.sort(key=lambda x: x["match_score"], reverse=True)
        
        return {"matches": enhanced_matches}

    def explain_matches(self, state: MatcherState):
        """Generate explanations for top matches using LLM in parallel."""
        print("[GRAPH] Node: explain_matches")
        matches = state["matches"]
        cv_text = state["cv_text"]
        
        # Only explain top 3 to save latency/tokens, or all if requested
        top_matches = matches[:3]
        
        final_results = []
        
        # Helper function for parallel execution
        def generate_explanation(match_item):
            try:
                # Enhanced prompt
                prompt = f"""
                Analyze the fit between the candidate and the job.
                
                CANDIDATE PROFILE:
                {cv_text[:900]}
                
                JOB DESCRIPTION:
                {match_item['job_text'][:900]}
                
                TASK:
                Provide a concise 3-sentence explanation of why this candidate is a good match for this job.
                Focus on matching skills, relevant experience, and specific requirements.
                Do not mention the match score.
                
                EXPLANATION:
                """
                ####
                # TODO: remove
                return match_item["job_id"], "very nice"  # Placeholder to avoid LLM calls during testing

                response = self.llm.invoke(prompt)
                return match_item["job_id"], response.content
            except Exception as e:
                logger.error(f"Explanation failed for job {match_item['job_id']}: {e}")
                return match_item["job_id"], None

        # Run LLM calls in parallel
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        explanations = {}
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_to_job = {executor.submit(generate_explanation, m): m for m in top_matches}
            for future in as_completed(future_to_job):
                job_id, explanation = future.result()
                if explanation:
                    explanations[job_id] = explanation

        for m in matches:
            result = {
                "job_id": m["job_id"],
                "job_title": m["data"].get("title", "Unknown"),
                "company": m["data"].get("company", "Unknown"),
                "match_score": round(m["match_score"], 3),
                "matching_factors": {
                    k: round(v, 3) for k, v in m.get("matching_factors", {}).items()
                },
                "matched_skills": m.get("matched_skills", []),
                "missing_skills": m.get("missing_skills", []),
                "explanation": explanations.get(m["job_id"]),
                "location": m["data"].get("location"),
                "salary_range": m["data"].get("salary_range")
            }
            final_results.append(result)
            
        return {"final_results": final_results}

    def match(self, cv_data: Dict[str, Any],) -> List[Dict[str, Any]]:
        """
        Execute the matching workflow.
        
        Args:
            cv_data: Parsed CV data dictionary
            cv_id: Optional CV identifier
            
        Returns:
            List of job matches with detailed factors and skills analysis
        """
        # Prepare input text for embedding
        cv_text = get_cv_text_representation(cv_data)
        
        # Run Graph with full CV data
        inputs = {
            "cv_text": cv_text,
            "cv_data": cv_data,  # Pass full data for detailed analysis
            "cv_embedding": [],
            "matches": [],
            "final_results": []
        }
        result = self.app.invoke(inputs)
        
        return result["final_results"]

