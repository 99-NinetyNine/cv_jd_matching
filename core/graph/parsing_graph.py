from typing import TypedDict, Dict, Any, Annotated
from langgraph.graph import StateGraph, END
from core.parsing.extractors.naive.pdf_parser import PDFParser
import operator

class ParsingState(TypedDict):
    file_path: str
    text_content: str
    structured_data: Dict[str, Any]
    status: str
    error: str

def extract_text_node(state: ParsingState):
    """Node to extract text from PDF."""
    # In a real graph, we might separate text extraction from parsing
    # For now, we'll just update status
    return {"status": "Extracting text from PDF..."}

def parse_cv_node(state: ParsingState):
    """Node to parse CV using LLM."""
    file_path = state["file_path"]
    parser = PDFParser() # Uses default model
    
    try:
        # PDFParser currently does both extraction and parsing
        # We could refactor PDFParser to separate them, but for now let's just call parse
        data = parser.parse(file_path)
        return {
            "parsed_data": data, # Changed structured_data to parsed_data for consistency with new node
            "status": "CV parsed successfully."
        }
    except Exception as e:
        return {
            "error": str(e),
            "status": "Error parsing CV."
        }

def fetch_external_data_node(state: ParsingState):
    """Node to fetch external data from links."""
    parsed_data = state.get("parsed_data", {})
    if not parsed_data:
        return {}
        
    profiles = parsed_data.get("basics", {}).get("profiles", [])
    if not profiles:
        return {}
        
    # We need a session here. In a real app, we'd inject it or use a context manager.
    # For this demo, we'll create a new session.
    from sqlmodel import Session, create_engine
    from core.parsing.external import ProfileFetcher
    import os
    
    # Use env var or default
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/cv_matching")
    engine = create_engine(db_url)
    
    augmented_data = parsed_data.copy()
    
    with Session(engine) as session:
        fetcher = ProfileFetcher(session)
        for profile in profiles:
            url = profile.get("url")
            if url:
                try:
                    ext_data = fetcher.fetch(url)
                    # Merge logic: Append skills, projects, etc.
                    if "skills" in ext_data:
                        existing_skills = [s.get("name") for s in augmented_data.get("skills", [])]
                        for skill in ext_data["skills"]:
                            if skill not in existing_skills:
                                augmented_data.setdefault("skills", []).append({"name": skill})
                                
                    if "projects" in ext_data:
                        # specific logic for projects
                        augmented_data.setdefault("projects", []).extend(ext_data["projects"])
                        
                except Exception as e:
                    logger.error(f"Failed to fetch {url}: {e}")
                    
    return {"parsed_data": augmented_data, "status": "External data fetched."}

def create_parsing_graph():
    workflow = StateGraph(ParsingState)
    
    workflow.add_node("extract_text", extract_text_node)
    workflow.add_node("parse_cv", parse_cv_node)
    workflow.add_node("fetch_external", fetch_external_data_node)
    
    workflow.set_entry_point("extract_text")
    workflow.add_edge("extract_text", "parse_cv")
    workflow.add_edge("parse_cv", "fetch_external")
    workflow.add_edge("fetch_external", END)
    
    return workflow.compile()

