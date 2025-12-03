from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlmodel import Session, select
from typing import List, Optional
from datetime import datetime
from core.db.engine import get_session
from core.db.models import Job, CV, UserInteraction, Application, User
from core.cache.redis_cache import redis_client
from core.matching.embeddings import EmbeddingFactory
from core.services.embedding_utils import prepare_ollama_embedding
from core.services.job_service import get_job_text_representation
from core.parsing.schema import JobCreate  # Import canonical schema
from api.routers.auth import get_current_user
import uuid
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["hirer"])


@router.post("")
async def create_job(
    job: JobCreate, 
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    is_test: bool = False,
):
    """
    Create a new job posting with comprehensive fields.
    
    This endpoint allows authenticated hirers to create job postings. The job
    embedding can be computed immediately (test mode) or queued for batch processing.
    
    Args:
        job: Job data following JobCreate schema with all required fields
        background_tasks: FastAPI background tasks (injected)
        session: Database session (injected)
        current_user: Authenticated user creating the job (injected)
        is_test: If True, compute embedding immediately; if False, queue for batch
    
    Returns:
        dict: Contains status message and created job_id
    
    Raises:
        HTTPException: 401 if user not authenticated
        HTTPException: 403 if user role is not 'hirer'
        HTTPException: 500 if job creation fails
    
    Note:
        Only users with 'hirer' role can create jobs.
        Job is automatically linked to the authenticated user.
    """
    # Authorization check
    if current_user.role != "hirer":
        raise HTTPException(
            status_code=403, 
            detail="Only hirers can create job postings"
        )
    
    try:
        # Generate job_id if not provided
        job_id =  str(uuid.uuid4())
        
        # Convert JobCreate to dict and prepare for Job model
        job_data = job.model_dump(exclude_unset=False)
        job_data.pop("job_id", None)  # REMOVE duplicate job_id

        # Convert Location object to dict if present
        if job.location:
            job_data['location'] = job.location.model_dump()
        
        # Convert Skill objects to dicts if present
        if job.skills:
            job_data['skills'] = [skill.model_dump() for skill in job.skills]
        
        # Get canonical text representation
        text_rep = get_job_text_representation(job_data)
        
        # Batch if not premium (or test)
        use_batch = not is_test
        
        # Create Job instance directly from JobCreate data
        db_job = Job(
            job_id=job_id,
            owner_id=current_user.id,  # Use authenticated user's ID
            **job_data,
            embedding_status="pending_batch" if use_batch else "completed",
            canonical_text=text_rep
        )

        # Compute embedding synchronously or mark for batch
        if use_batch:
            logger.info(f"Job {job_id} marked for batch processing")
        else:
            logger.info(f"Computing embedding synchronously for job {job_id}")
            embedder = EmbeddingFactory.get_embedder(provider="ollama")
            l = embedder.embed_query(text_rep)
            print("kength?",len(l))
            l = prepare_ollama_embedding(l)
            print("kength 2?",len(l))

            db_job.embedding = l
        
        session.add(db_job)
        session.commit()
        session.refresh(db_job)
        
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
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    List jobs for the authenticated hirer.
    
    Returns jobs created by the authenticated user.
    
    Args:
        session: Database session (injected)
        current_user: Authenticated user (injected)
    Returns:
        dict: Contains list of jobs and total count
    """
   
    # Show only user's own jobs
    jobs = session.exec(select(Job).where(Job.owner_id == current_user.id)).all()
    
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
    current_user: User = Depends(get_current_user),
):
    """
    Delete a job posting.
    
    Only the job owner or admin can delete a job posting.
    
    Args:
        job_id: Job identifier
        session: Database session (injected)
        current_user: Authenticated user (injected)
    
    Returns:
        dict: Status message and deleted job_id
    
    Raises:
        HTTPException: 404 if job not found
        HTTPException: 403 if user not authorized to delete
        HTTPException: 401 if user not authenticated
    """
    job = session.exec(select(Job).where(Job.job_id == job_id)).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Authorization check - only owner or admin can delete
    if job.owner_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=403, 
            detail="Not authorized to delete this job"
        )
    
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
    current_user: User = Depends(get_current_user),
    status_filter: Optional[str] = None,  # pending, accepted, rejected
):
    """
    Get all applications for a specific job.
    
    Only the job owner or admin can view applications for a job.
    Results can be filtered by application status.
    
    Args:
        job_id: Job identifier
        session: Database session (injected)
        current_user: Authenticated user (injected)
        status_filter: Optional filter - "pending", "accepted", or "rejected"
    
    Returns:
        dict: Contains job info, applications with candidate details, and count
    
    Raises:
        HTTPException: 404 if job not found
        HTTPException: 403 if user not authorized to view applications
        HTTPException: 401 if user not authenticated
    """
    # Verify job exists
    job = session.exec(select(Job).where(Job.job_id == job_id)).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Authorization check - only owner or admin can view applications
    if job.owner_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=403, 
            detail="Not authorized to view applications for this job"
        )
    
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

