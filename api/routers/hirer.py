from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlmodel import Session, select
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from core.db.engine import get_session
from core.db.models import Job, CV, UserInteraction, Application
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
        
        # Check if premium (mock)
        is_premium = False # TODO: Fetch from User model
        
        # Batch if not premium
        use_batch = not is_premium
        
        # Save job with embedding computed in background or batch
        db_job = save_job_with_embedding(
            job_data=job_data,
            owner_id=owner_id,
            session=session,
            embedder=embedder,
            compute_async=not use_batch,  # If batch, we don't need async task immediately
            batch_mode=use_batch
        )
        
        if not use_batch:
            # Schedule background task to compute embedding immediately
            background_tasks.add_task(
                update_job_embedding,
                job_id=db_job.job_id,
                session=session,
                embedder=embedder
            )
            message = "Embedding computation in progress"
        else:
            message = "Job queued for batch processing"
        
        logger.info(f"Job {db_job.job_id} created. Batch mode: {use_batch}")
        
        return {
            "status": "Job created successfully",
            "job_id": db_job.job_id,
            "message": message
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

# Hirer interaction tracking

class HirerInteractionCreate(BaseModel):
    """Track hirer actions on candidate applications."""
    cv_id: str  # Candidate CV ID
    job_id: str
    action: str  # shortlisted, interviewed, hired, rejected
    metadata: Optional[dict] = None  # e.g., {"interview_date": "2024-12-15", "rejection_reason": "..."}

@router.post("/interact")
async def log_hirer_interaction(
    interaction: HirerInteractionCreate,
    session: Session = Depends(get_session),
    owner_id: Optional[int] = None  # TODO: Get from authenticated user
):
    """
    Log hirer interactions with candidates for analytics and evaluation.
    
    Supported actions:
    - shortlisted: Candidate moved to shortlist
    - interviewed: Candidate was interviewed
    - hired: Candidate was hired
    - rejected: Candidate was rejected
    
    This data helps:
    - Evaluate matching algorithm effectiveness
    - Provide analytics to hirers
    - Improve future recommendations
    """
    # Validate action type
    valid_actions = ['shortlisted', 'interviewed', 'hired', 'rejected']
    if interaction.action not in valid_actions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid action. Must be one of: {', '.join(valid_actions)}"
        )
    
    try:
        # Convert CV ID to user_id (use hash for now)
        user_id_int = hash(interaction.cv_id) % (10 ** 8)
        
        db_interaction = UserInteraction(
            user_id=user_id_int,
            job_id=interaction.job_id,
            action=interaction.action,
            strategy='pgvector',
            metadata=interaction.metadata
        )
        session.add(db_interaction)
        session.commit()
        
        logger.info(f"Hirer interaction logged: cv={interaction.cv_id}, job={interaction.job_id}, action={interaction.action}")
        
        return {
            "status": "success",
            "message": f"Hirer action '{interaction.action}' logged successfully"
        }
    except Exception as e:
        logger.error(f"Failed to log hirer interaction: {e}")
        raise HTTPException(status_code=500, detail=str(e))# Application Management Endpoints - Append to hirer.py

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


@router.post("/{job_id}/applications/{application_id}/accept")
async def accept_application(
    job_id: str,
    application_id: int,
    session: Session = Depends(get_session),
    owner_id: Optional[int] = None,  # TODO: Get from authenticated user
):
    """Accept a job application (owner only)."""
    # Verify job exists
    job = session.exec(select(Job).where(Job.job_id == job_id)).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Get application
    application = session.exec(
        select(Application).where(
            Application.id == application_id,
            Application.job_id == job_id
        )
    ).first()
    
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    if application.status != "pending":
        raise HTTPException(status_code=400, detail=f"Application already {application.status}")
    
    # Update application
    application.status = "accepted"
    application.decision_at = datetime.utcnow()
    application.decided_by = owner_id
    session.add(application)
    session.commit()
    
    # Log interaction as 'hired'
    user_id_int = hash(application.cv_id) % (10 ** 8)
    interaction = UserInteraction(
        user_id=user_id_int,
        job_id=job_id,
        action="hired",
        strategy="pgvector",
        metadata={
            "prediction_id": application.prediction_id,
            "cv_id": application.cv_id,
            "application_id": application.id
        }
    )
    session.add(interaction)
    session.commit()
    
    logger.info(f"Application {application_id} accepted for job {job_id}")
    
    return {"status": "success", "message": "Application accepted"}


@router.post("/{job_id}/applications/{application_id}/reject")
async def reject_application(
    job_id: str,
    application_id: int,
    session: Session = Depends(get_session),
    owner_id: Optional[int] = None,
):
    """Reject a job application (owner only)."""
    # Verify job exists
    job = session.exec(select(Job).where(Job.job_id == job_id)).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Get application
    application = session.exec(
        select(Application).where(
            Application.id == application_id,
            Application.job_id == job_id
        )
    ).first()
    
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    if application.status != "pending":
        raise HTTPException(status_code=400, detail=f"Application already {application.status}")
    
    # Update application
    application.status = "rejected"
    application.decision_at = datetime.utcnow()
    application.decided_by = owner_id
    session.add(application)
    session.commit()
    
    # Log interaction as 'rejected'
    user_id_int = hash(application.cv_id) % (10 ** 8)
    interaction = UserInteraction(
        user_id=user_id_int,
        job_id=job_id,
        action="rejected",
        strategy="pgvector",
        metadata={
            "prediction_id": application.prediction_id,
            "cv_id": application.cv_id,
            "application_id": application.id
        }
    )
    session.add(interaction)
    session.commit()
    
    logger.info(f"Application {application_id} rejected for job {job_id}")
    
    return {"status": "success", "message": "Application rejected"}
