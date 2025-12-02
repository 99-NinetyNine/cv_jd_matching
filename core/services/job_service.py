"""
Shared service for job processing operations.
Handles embedding computation and caching for job postings.
"""
from typing import Dict, Any, Optional
from sqlmodel import Session
import logging
import uuid

from core.db.models import Job
from core.matching.embeddings import Embedder, EmbeddingFactory

logger = logging.getLogger(__name__)


def get_job_text_representation(job_data: Dict[str, Any]) -> str:
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


def compute_job_embedding(job_text:str) -> list:
    """
    Compute job embedding with ID-based caching.
    
    Args:
        job_id: Unique job identifier
        job_data: Job data dictionary
        embedder: Embedder instance (must support embed_with_id)
    
    Returns:
        Embedding vector
    """
    embedder = EmbeddingFactory.get_embedder(provider="ollama")
        
    em = embedder.embed_query(job_text)
    print("embeddings", em)

    return  em
    


def save_job_with_embedding(
    job_data: Dict[str, Any],
    owner_id: Optional[int],
    session: Session,
    batch_mode: bool = False
) -> Job:
    """
    Save job to database with embedding.
    
    Args:
        job_data: Job data dictionary
        owner_id: ID of the user creating the job
        session: Database session
        embedder: Embedder instance
        batch_mode: If True, mark for batch processing
    """
    # Generate job_id if not provided or None
    job_id = job_data.get('job_id')
    if not job_id:
        job_id = str(uuid.uuid4())
    text_rep = get_job_text_representation(job_data)
    
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
        company_profile=job_data.get('company_profile'),
        embedding_status= "pending_batch" if batch_mode else "completed",
        canonical_text=text_rep,
        data=job_data  # Store complete job data as JSON
    )
    
    # Compute embedding synchronously or mark for async/batch
    if batch_mode:
        logger.info(f"Job {job_id} marked for batch processing")
    else:
        logger.info(f"Computing embedding synchronously for job {job_id}")

        job.embedding = compute_job_embedding(text_rep)
    
    session.add(job)
    session.commit()
    session.refresh(job)
    
    return job

