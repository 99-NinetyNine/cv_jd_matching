from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlmodel import Session, select
from typing import List, Optional
from datetime import datetime
from core.db.engine import get_session
from core.db.models import Job, CV, UserInteraction, Application
from core.cache.redis_cache import redis_client
from core.matching.embeddings import EmbeddingFactory
from core.services.job_service import save_job_with_embedding
from core.parsing.schema import JobCreate  # Import canonical schema
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["hirer"])


@router.post("")
async def create_job(
    job: JobCreate, 
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    is_test: bool = False,
    owner_id: Optional[int] = None  # TODO: Get from authenticated user
):
    """
    Create a new job posting with comprehensive fields.
    Embedding computation happens in background for better performance.
    
    Args:
        job: Job data
        background_tasks: FastAPI background tasks
        session: Database session
        is_test: For testing purpose, if True, compute embedding immediately
        owner_id: ID of the user creating the job (from auth)
    """
    try:
        
        # Convert Pydantic model to dict
        job_data = job.model_dump()
        
        # Batch if not premium
        use_batch = not is_test
        
        # Save job with embedding computed in background or batch
        db_job = save_job_with_embedding(
            job_data=job_data,
            owner_id=owner_id,
            session=session,
            batch_mode=use_batch
        )
        
        
        logger.info(f"Job {db_job.job_id} created. Batch mode: {use_batch}")
        
        return {
            "status": "Job created successfully",
            "job_id": db_job.job_id,
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

# TODO: if JD is updated then may need have to recompute embeddings

@router.get("/{job_id}/applications")
async def get_job_applications(
    job_id: str,
    session: Session = Depends(get_session),
    owner_id: Optional[int] = None,  # TODO: Get from authenticated user
    status_filter: Optional[str] = None  # pending, accepted, rejected
):
    """
    Get all applications for a specific job.
    Only the job owner can view applications.
    """
    # Verify job exists
    job = session.exec(select(Job).where(Job.job_id == job_id)).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # TODO: Add authorization when auth is implemented
    # if owner_id and job.owner_id != owner_id:
    #     raise HTTPException(status_code=403, detail="Not authorized")
    
    # Get applications
    query = select(Application).where(Application.job_id == job_id)
    if status_filter:
        query = query.where(Application.status == status_filter)
    
    applications = session.exec(query.order_by(Application.applied_at.desc())).all()
    
    # Fetch CV details
    applications_with_cv = []
    for app in applications:
        cv = session.exec(select(CV).where(CV.filename == app.cv_id)).first()
        app_dict = {
            "id": app.id,
            "cv_id": app.cv_id,
            "job_id": app.job_id,
            "prediction_id": app.prediction_id,
            "status": app.status,
            "applied_at": app.applied_at,
            "decision_at": app.decision_at,
            "decided_by": app.decided_by,
            "notes": app.notes,
            "candidate": {
                "name": cv.content.get("basics", {}).get("name", "Unknown") if cv else "Unknown",
                "email": cv.content.get("basics", {}).get("email", "") if cv else "",
                "summary": cv.content.get("basics", {}).get("summary", "") if cv else "",
                "skills": cv.content.get("skills", []) if cv else [],
                "work": cv.content.get("work", [])[:2] if cv else []  # First 2 work experiences
            } if cv else None
        }
        applications_with_cv.append(app_dict)
    
    return {
        "job_id": job_id,
        "job_title": job.title,
        "applications": applications_with_cv,
        "count": len(applications_with_cv)
    }

