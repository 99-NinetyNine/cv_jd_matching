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


def _get_text_representation(cv_data: Dict[str, Any]) -> str:
    """Convert CV data to text representation for embedding."""
    text = ""
    
    if "basics" in cv_data:
        basics = cv_data["basics"]
        text += f"{basics.get('name', '')} {basics.get('label', '')} {basics.get('summary', '')} "
        if "location" in basics and isinstance(basics["location"], dict):
            loc = basics["location"]
            text += f"{loc.get('city', '')}, {loc.get('countryCode', '')} "
    
    if "skills" in cv_data:
        skills_list = []
        for s in cv_data["skills"]:
            if isinstance(s, dict):
                name = s.get("name", "")
                keywords = ", ".join(s.get("keywords", []))
                skills_list.append(f"{name} ({keywords})" if keywords else name)
            else:
                skills_list.append(str(s))
        text += " ".join(skills_list) + " "
    
    if "work" in cv_data:
        for work in cv_data["work"]:
            text += f"{work.get('position', '')} {work.get('name', '')} {work.get('summary', '')} "
    
    if "education" in cv_data:
        for edu in cv_data["education"]:
            text += f"{edu.get('studyType', '')} {edu.get('area', '')} {edu.get('institution', '')} "
    
    return text.strip()


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
        cv = CV(filename=f"{cv_id}.pdf", content=data)
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
    text_rep = _get_text_representation(cv_data)
    
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
    embedder: Optional[Embedder] = None
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
    
    # Update CV record
    cv = session.exec(select(CV).where(CV.filename == f"{cv_id}.pdf")).first()
    if cv:
        cv.content = corrected_data
        
        # Recompute embedding if embedder provided
        if embedder:
            logger.info(f"Recomputing embedding for corrected CV {cv_id}")
            cv.embedding = compute_cv_embedding(cv_id, corrected_data, embedder)
        
        session.add(cv)
        session.commit()
        session.refresh(cv)
    
    return corrected_data
