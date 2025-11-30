"""
Shared service for job processing operations.
Handles embedding computation and caching for job postings.
"""
from typing import Dict, Any, Optional
from sqlmodel import Session
import logging
import uuid

from core.db.models import Job
from core.matching.embeddings import Embedder

logger = logging.getLogger(__name__)


def _get_job_text_representation(job_data: Dict[str, Any]) -> str:
    """Convert job data to text representation for embedding."""
    text = ""
    
    # Core fields
    text += f"Title: {job_data.get('title', '')} "
    text += f"Role: {job_data.get('role', '')} " if job_data.get('role') else ""
    text += f"Company: {job_data.get('company', '')} "
    text += f"Description: {job_data.get('description', '')} "
    
    # Requirements
    if job_data.get('experience'):
        text += f"Experience: {job_data['experience']} "
    if job_data.get('qualifications'):
        text += f"Qualifications: {job_data['qualifications']} "
    if job_data.get('skills'):
        text += f"Skills: {', '.join(job_data['skills'])} "
    
    # Location
    if job_data.get('location'):
        text += f"Location: {job_data['location']}"
        if job_data.get('country'):
            text += f", {job_data['country']} "
    
    # Additional details
    if job_data.get('work_type'):
        text += f"Work Type: {job_data['work_type']} "
    if job_data.get('salary_range'):
        text += f"Salary: {job_data['salary_range']} "
    if job_data.get('responsibilities'):
        text += f"Responsibilities: {', '.join(job_data['responsibilities'])} "
    if job_data.get('benefits'):
        text += f"Benefits: {', '.join(job_data['benefits'])} "
    
    return text.strip()


def compute_job_embedding(job_id: str, job_data: Dict[str, Any], embedder: Embedder) -> list:
    """
    Compute job embedding with ID-based caching.
    
    Args:
        job_id: Unique job identifier
        job_data: Job data dictionary
        embedder: Embedder instance (must support embed_with_id)
    
    Returns:
        Embedding vector
    """
    text_rep = _get_job_text_representation(job_data)
    
    # Use ID-based caching if available
    if hasattr(embedder, 'embed_with_id'):
        return embedder.embed_with_id(text_rep, job_id, 'job')
    else:
        # Fallback to regular embedding
        logger.warning(f"Embedder does not support embed_with_id, using embed_query")
        return embedder.embed_query(text_rep)


def save_job_with_embedding(
    job_data: Dict[str, Any],
    owner_id: Optional[int],
    session: Session,
    embedder: Embedder,
    compute_async: bool = False
) -> Job:
    """
    Save job to database with embedding.
    
    Args:
        job_data: Job data dictionary
        owner_id: ID of the user creating the job
        session: Database session
        embedder: Embedder instance
        compute_async: If True, return job without embedding (to be computed in background)
    
    Returns:
        Created Job instance
    """
    # Generate job_id if not provided or None
    job_id = job_data.get('job_id')
    if not job_id:
        job_id = str(uuid.uuid4())
    
    # Create Job instance
    job = Job(
        job_id=job_id,
        owner_id=owner_id,
        title=job_data['title'],
        role=job_data.get('role'),
        company=job_data['company'],
        description=job_data['description'],
        experience=job_data.get('experience'),
        qualifications=job_data.get('qualifications'),
        skills=job_data.get('skills'),
        salary_range=job_data.get('salary_range'),
        benefits=job_data.get('benefits'),
        location=job_data.get('location'),
        country=job_data.get('country'),
        latitude=job_data.get('latitude'),
        longitude=job_data.get('longitude'),
        work_type=job_data.get('work_type'),
        company_size=job_data.get('company_size'),
        job_posting_date=job_data.get('job_posting_date'),
        preference=job_data.get('preference'),
        contact_person=job_data.get('contact_person'),
        contact=job_data.get('contact'),
        job_portal=job_data.get('job_portal'),
        responsibilities=job_data.get('responsibilities'),
        company_profile=job_data.get('company_profile')
    )
    
    # Compute embedding synchronously or mark for async
    if not compute_async:
        logger.info(f"Computing embedding synchronously for job {job_id}")
        job.embedding = compute_job_embedding(job_id, job_data, embedder)
    else:
        logger.info(f"Job {job_id} will have embedding computed asynchronously")
    
    session.add(job)
    session.commit()
    session.refresh(job)
    
    return job


def update_job_embedding(job_id: str, session: Session, embedder: Embedder) -> bool:
    """
    Update job embedding (used by background tasks).
    
    Args:
        job_id: Unique job identifier
        session: Database session
        embedder: Embedder instance
    
    Returns:
        True if successful, False otherwise
    """
    from sqlmodel import select
    
    job = session.exec(select(Job).where(Job.job_id == job_id)).first()
    if not job:
        logger.error(f"Job {job_id} not found")
        return False
    
    # Convert job to dict for embedding computation
    job_data = {
        'title': job.title,
        'role': job.role,
        'company': job.company,
        'description': job.description,
        'experience': job.experience,
        'qualifications': job.qualifications,
        'skills': job.skills,
        'salary_range': job.salary_range,
        'benefits': job.benefits,
        'location': job.location,
        'country': job.country,
        'work_type': job.work_type,
        'responsibilities': job.responsibilities,
    }
    
    logger.info(f"Computing embedding for job {job_id}")
    job.embedding = compute_job_embedding(job_id, job_data, embedder)
    
    session.add(job)
    session.commit()
    
    logger.info(f"Successfully updated embedding for job {job_id}")
    return True
