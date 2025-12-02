"""
Shared service for CV processing operations.
Handles parsing, embedding computation, and caching.
"""
from typing import Dict, Any, Optional
from pathlib import Path
from sqlmodel import Session, select
import logging

from core.db.models import CV, ParsingCorrection
from core.parsing.main import RESUME_PARSER
from core.matching.embeddings import Embedder

logger = logging.getLogger(__name__)


def get_cv_text_representation(data: Dict[str, Any]) -> str:
    """
    Convert structured CV data (based on JSON Resume schema) to a text representation for embedding.
    This is the canonical implementation used across the codebase.
    
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


def get_or_parse_cv(cv_id: str, file_path: Optional[Path], session: Session) -> Dict[str, Any]:
    """
    Get CV data from database if already parsed, otherwise parse and save.
    
    Args:
        cv_id: Unique CV identifier
        file_path: Path to CV file (required if not in DB)
        session: Database session
    
    Returns:
        Parsed CV data as dictionary
    """
    # Check if CV exists in database
    cv = session.exec(select(CV).where(CV.filename == f"{cv_id}.pdf")).first()
    
    if cv and cv.content:
        logger.info(f"CV {cv_id} already parsed, retrieving from database")
        return cv.content
    
    # Parse CV
    if not file_path or not file_path.exists():
        raise FileNotFoundError(f"CV file not found for {cv_id}")
    
    logger.info(f"Parsing CV {cv_id}")
    parser = RESUME_PARSER
    data = parser.parse(file_path)
    
    # Save to database
    if cv:
        cv.content = data
    else:
        cv = CV(filename=f"{cv_id}.pdf", content=data, parsing_status="completed")
        session.add(cv)
    
    session.commit()
    session.refresh(cv)
    
    return data


def compute_cv_embedding(cv_id: str, cv_data: Dict[str, Any], embedder: Embedder) -> list:
    """
    Compute CV embedding with ID-based caching.
    
    Args:
        cv_id: Unique CV identifier
        cv_data: Parsed CV data
        embedder: Embedder instance (must support embed_with_id)
    
    Returns:
        Embedding vector
    """
    text_rep = get_cv_text_representation(cv_data)
    
    # Use ID-based caching if available
    if hasattr(embedder, 'embed_with_id'):
        return embedder.embed_with_id(text_rep, cv_id, 'cv')
    else:
        # Fallback to regular embedding
        logger.warning(f"Embedder does not support embed_with_id, using embed_query")
        return embedder.embed_query(text_rep)


def update_cv_with_corrections(
    cv_id: str, 
    original_data: Dict[str, Any],
    corrected_data: Dict[str, Any], 
    session: Session,
) -> Dict[str, Any]:
    """
    Update CV with user corrections and optionally recompute embedding.
    
    Args:
        cv_id: Unique CV identifier
        original_data: Original parsed data
        corrected_data: User-corrected data
        session: Database session
        embedder: Optional embedder to recompute embedding
    
    Returns:
        Updated CV data
    """
    # Save correction for training
    if corrected_data != original_data:
        logger.info(f"Saving corrections for CV {cv_id}")
        correction = ParsingCorrection(
            cv_id=cv_id,
            original_data=original_data,
            corrected_data=corrected_data
        )
        session.add(correction)
    else:
        logger.info(f"No corrections received for CV {cv_id}")

    # Update CV record
    cv = session.exec(select(CV).where(CV.filename == f"{cv_id}.pdf")).first()
    if cv:
        cv.content = corrected_data
        
        session.add(cv)
        session.commit()
        session.refresh(cv)
    
    return corrected_data
