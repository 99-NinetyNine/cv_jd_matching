from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlmodel import Session, select
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from core.db.engine import get_session
from core.db.models import Job, CV
from core.cache.redis_cache import redis_client
from core.matching.embeddings import EmbeddingFactory
from core.services.job_service import save_job_with_embedding, update_job_embedding
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["hirer"])


class JobCreate(BaseModel):
    """Pydantic model for job creation with comprehensive fields."""
    # Core fields (required)
    title: str
    company: str
    description: str
    
    # Optional fields
    job_id: Optional[str] = None  # Auto-generated if not provided
    role: Optional[str] = None
    experience: Optional[str] = None  # e.g., "5 to 10 Years"
    qualifications: Optional[str] = None  # e.g., "BBA, MBA"
    skills: Optional[List[str]] = None
    salary_range: Optional[str] = None  # e.g., "$55K-$84K"
    benefits: Optional[List[str]] = None
    location: Optional[str] = None
    country: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    work_type: Optional[str] = None  # Contract, Full-Time, Part-Time
    company_size: Optional[int] = None
    job_posting_date: Optional[datetime] = None
    preference: Optional[str] = None
    contact_person: Optional[str] = None
    contact: Optional[str] = None
    job_portal: Optional[str] = None
    responsibilities: Optional[List[str]] = None
    company_profile: Optional[dict] = None


@router.post("")
async def create_job(
    job: JobCreate, 
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    owner_id: Optional[int] = None  # TODO: Get from authenticated user
):
    """
    Create a new job posting with comprehensive fields.
    Embedding computation happens in background for better performance.
    
    Args:
        job: Job data
        background_tasks: FastAPI background tasks
        session: Database session
        owner_id: ID of the user creating the job (from auth)
    """
    try:
        # Get embedder
        embedder = EmbeddingFactory.get_embedder(provider="ollama")
        
        # Convert Pydantic model to dict
        job_data = job.dict()
        
        # Save job with embedding computed in background
        db_job = save_job_with_embedding(
            job_data=job_data,
            owner_id=owner_id,
            session=session,
            embedder=embedder,
            compute_async=True  # Compute in background
        )
        
        # Schedule background task to compute embedding
        background_tasks.add_task(
            update_job_embedding,
            job_id=db_job.job_id,
            session=session,
            embedder=embedder
        )
        
        logger.info(f"Job {db_job.job_id} created, embedding computation scheduled")
        
        return {
            "status": "Job created successfully",
            "job_id": db_job.job_id,
            "message": "Embedding computation in progress"
        }
        
    except Exception as e:
        logger.error(f"Failed to create job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def list_jobs(
    owner_id: Optional[int] = None,  # TODO: Get from authenticated user
    session: Session = Depends(get_session)
):
    """
    List all jobs, optionally filtered by owner.
    
    Args:
        owner_id: Optional filter by job owner
        session: Database session
    """
    if owner_id:
        jobs = session.exec(select(Job).where(Job.owner_id == owner_id)).all()
    else:
        jobs = session.exec(select(Job)).all()
    
    return {"jobs": jobs, "count": len(jobs)}


@router.get("/{job_id}")
async def get_job(job_id: str, session: Session = Depends(get_session)):
    """Get a specific job by ID."""
    job = session.exec(select(Job).where(Job.job_id == job_id)).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.delete("/{job_id}")
async def delete_job(
    job_id: str,
    session: Session = Depends(get_session),
    owner_id: Optional[int] = None  # TODO: Get from authenticated user
):
    """
    Delete a job posting.
    
    Args:
        job_id: Job identifier
        session: Database session
        owner_id: ID of the authenticated user (for authorization)
    """
    job = session.exec(select(Job).where(Job.job_id == job_id)).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Authorization check (if owner_id provided)
    if owner_id and job.owner_id != owner_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this job")
    
    session.delete(job)
    session.commit()
    
    # Clear cache
    try:
        redis_client.delete(f"emb_ollama_nomic-embed-text_job:{job_id}")
    except Exception as e:
        logger.warning(f"Failed to clear cache for job {job_id}: {e}")
    
    return {"status": "Job deleted successfully", "job_id": job_id}
