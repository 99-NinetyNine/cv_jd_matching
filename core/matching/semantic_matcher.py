from typing import Dict, Any, List, Optional, TypedDict
from langgraph.graph import StateGraph, END
from sentence_transformers import CrossEncoder
import numpy as np
import logging
import psycopg2
import os
from core.matching.embeddings import EmbeddingFactory
from core.services.job_service import get_job_text_representation
from core.llm.factory import get_llm
from langchain_core.prompts import PromptTemplate

logger = logging.getLogger(__name__)

# Define State
class MatcherState(TypedDict):
    cv_text: str
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
        
        # Add Edges
        workflow.set_entry_point("embed")
        workflow.add_edge("embed", "retrieve")
        workflow.add_edge("retrieve", "rerank")
        workflow.add_edge("rerank", END)
        
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
            # Optimized vector search
            cur.execute("""
                SELECT id, data, 1 - (embedding <=> %s::vector) as similarity
                FROM jobs
                WHERE embedding_status = 'completed'
                ORDER BY embedding <=> %s::vector
                LIMIT 20;
            """, (embedding, embedding))
            
            results = []
            for row in cur.fetchall():
                results.append({
                    "job_id": row[0],
                    "data": row[1],
                    "similarity": float(row[2]),
                    "job_text": get_job_text_representation(row[1])
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
            return {"final_results": []}
            
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
        top_k = matches[:10]
        
        # Format for output
        final_results = []
        for m in top_k:
            final_results.append({
                "job_id": m["job_id"],
                "job_title": m["data"].get("title", "Unknown"),
                "company": m["data"].get("company", "Unknown"),
                "match_score": m["match_score"],
                "explanation": None, # Pending batch processing
                "location": m["data"].get("location"),
                "salary_range": m["data"].get("salary_range")
            })
            
        return {"final_results": final_results}

    def match(self, cv_data: Dict[str, Any], cv_id: str = None) -> List[Dict[str, Any]]:
        """
        Execute the matching workflow.
        """
        # Prepare input text
        cv_text = str(cv_data.get("basics", {})) + " " + str(cv_data.get("skills", []))
        
        # Run Graph
        inputs = {"cv_text": cv_text, "cv_embedding": [], "matches": [], "final_results": []}
        result = self.app.invoke(inputs)
        
        return result["final_results"]

# For backward compatibility if needed, though we should update callers
HybridMatcher = GraphMatcher
