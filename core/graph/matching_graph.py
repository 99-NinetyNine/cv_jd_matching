from typing import TypedDict, Dict, Any, List
from langgraph.graph import StateGraph, END


class MatchingState(TypedDict):
    cv_data: Dict[str, Any]
    job_descriptions: List[Dict[str, Any]]
    matches: List[Dict[str, Any]]
    status: str
    error: str

def embed_cv_node(state: MatchingState):
    return {"status": "Embedding CV data..."}

def match_jobs_node(state: MatchingState):
    cv_data = state["cv_data"]
    jobs = state["job_descriptions"]
    
    # Use HybridMatcher instead of SemanticMatcher
    from core.matching.semantic_matcher import HybridMatcher
    matcher = HybridMatcher()
    try:
        matches = matcher.match(cv_data, jobs)
        return {
            "matches": matches,
            "status": "Matching completed."
        }
    except Exception as e:
        return {
            "error": str(e),
            "status": "Error during matching."
        }

def create_matching_graph():
    workflow = StateGraph(MatchingState)
    
    workflow.add_node("embed_cv", embed_cv_node)
    workflow.add_node("match_jobs", match_jobs_node)
    
    workflow.set_entry_point("embed_cv")
    workflow.add_edge("embed_cv", "match_jobs")
    workflow.add_edge("match_jobs", END)
    
    return workflow.compile()
