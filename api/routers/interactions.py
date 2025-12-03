"""
Unified interaction tracking for both candidates and hirers.
Simple, elegant, and sufficient for AI/analytics purposes.
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import logging

from core.db.engine import get_session
from core.db.models import UserInteraction, Application, User
from api.routers.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/interactions", tags=["interactions"])


class InteractionCreate(BaseModel):
    """Unified interaction model for both candidates and hirers."""
    # Who
    user_id: str  # Can be CV ID or user email/ID
    user_type: str  # "candidate" or "hirer"

    # What
    job_id: str
    action: str  # viewed, saved, applied, shortlisted, interviewed, hired, rejected

    # Context (optional)
    cv_id: Optional[str] = None  # For linking to specific CV
    prediction_id: Optional[str] = None  # For tracking recommendation quality
    application_id: Optional[int] = None  # For tracking application lifecycle

    # Additional metadata (flexible JSONB)
    metadata: Optional[dict] = None


@router.post("/log")
async def log_interaction(
    interaction: InteractionCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Unified interaction logging endpoint for both candidates and hirers.

    This endpoint tracks all user interactions with jobs and applications,
    enabling recommendation quality tracking, engagement analytics, and
    application lifecycle management.
    
    **Candidate actions**: 
    - `viewed`: Candidate viewed a job recommendation
    - `saved`: Candidate bookmarked a job for later
    - `applied`: Candidate submitted an application
    
    **Hirer actions**: 
    - `shortlisted`: Hirer marked candidate for further review
    - `interviewed`: Hirer scheduled/completed interview
    - `hired`: Hirer accepted the candidate
    - `rejected`: Hirer rejected the application

    Args:
        interaction: Interaction data including user_id, job_id, action, etc.
        session: Database session (injected)
        current_user: Authenticated user (injected)
    
    Returns:
        dict: Contains status, message, and application_id (if applicable)
    
    Raises:
        HTTPException: 400 if invalid action for user type
        HTTPException: 401 if user not authenticated
        HTTPException: 500 if logging fails
    
    Note:
        - Automatically creates Application records for 'applied' actions
        - Updates Application status for hirer actions
        - Tracks prediction_id for recommendation quality metrics
    
    Example:
        ```python
        # Candidate views a job
        POST /interactions/log
        {
            "user_id": "cv_123",
            "user_type": "candidate",
            "job_id": "job_456",
            "action": "viewed",
            "prediction_id": "pred_789"
        }
        
        # Hirer shortlists a candidate
        POST /interactions/log
        {
            "user_id": "hirer_123",
            "user_type": "hirer",
            "job_id": "job_456",
            "action": "shortlisted",
            "application_id": 42
        }
        ```
    """

    # Validate action based on user type
    candidate_actions = ["viewed", "saved", "applied"]
    hirer_actions = ["shortlisted", "interviewed", "hired", "rejected"]

    if interaction.user_type == "candidate":
        if interaction.action not in candidate_actions:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid candidate action. Must be one of: {', '.join(candidate_actions)}"
            )
    elif interaction.user_type == "hirer":
        if interaction.action not in hirer_actions:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid hirer action. Must be one of: {', '.join(hirer_actions)}"
            )
    else:
        raise HTTPException(
            status_code=400,
            detail="user_type must be 'candidate' or 'hirer'"
        )

    try:
        # Convert user_id to integer (hash if string)
        try:
            user_id_int = int(interaction.user_id)
        except ValueError:
            user_id_int = hash(interaction.user_id) % (10 ** 8)

        # Build enhanced metadata
        enhanced_metadata = interaction.metadata or {}
        enhanced_metadata.update({
            "user_type": interaction.user_type,
            "cv_id": interaction.cv_id,
            "prediction_id": interaction.prediction_id,
            "application_id": interaction.application_id,
            "timestamp": datetime.utcnow().isoformat()
        })

        # Handle application creation/update for "applied" action
        application_id = interaction.application_id

        if interaction.action == "applied" and interaction.cv_id and interaction.prediction_id:
            # Create application record if doesn't exist
            from sqlmodel import select

            existing_app = session.exec(
                select(Application).where(
                    Application.cv_id == interaction.cv_id,
                    Application.job_id == interaction.job_id
                )
            ).first()

            if not existing_app:
                application = Application(
                    cv_id=interaction.cv_id,
                    job_id=interaction.job_id,
                    prediction_id=interaction.prediction_id,
                    status="pending"
                )
                session.add(application)
                session.flush()
                application_id = application.id
                enhanced_metadata["application_id"] = application_id
                logger.info(f"Created Application {application_id}")
            else:
                application_id = existing_app.id
                enhanced_metadata["application_id"] = application_id

        # Handle application status updates for hirer actions
        if interaction.user_type == "hirer" and interaction.application_id:
            application = session.get(Application, interaction.application_id)

            if application:
                # Update application status based on action
                status_map = {
                    "shortlisted": "pending",  # Still pending but flagged
                    "interviewed": "pending",  # Still pending
                    "hired": "accepted",
                    "rejected": "rejected"
                }

                new_status = status_map.get(interaction.action)
                if new_status:
                    application.status = new_status
                    if new_status in ["accepted", "rejected"]:
                        application.decision_at = datetime.utcnow()
                    session.add(application)
                    logger.info(f"Updated Application {application.id} to {new_status}")

        # Create interaction record
        db_interaction = UserInteraction(
            user_id=user_id_int,
            job_id=interaction.job_id,
            action=interaction.action,
            strategy="pgvector",  # Can be parameterized if needed
            interaction_metadata=enhanced_metadata
        )
        session.add(db_interaction)
        session.commit()

        logger.info(
            f"Logged interaction: {interaction.user_type} {interaction.user_id} "
            f"{interaction.action} job {interaction.job_id}"
        )

        return {
            "status": "success",
            "message": f"Interaction '{interaction.action}' logged successfully",
            "application_id": application_id
        }

    except Exception as e:
        logger.error(f"Failed to log interaction: {e}")
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/{user_id}")
async def get_user_interaction_stats(
    user_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Get interaction statistics for a specific user.
    
    Provides comprehensive analytics on user engagement patterns,
    including action breakdowns and recent activity history.
    
    Args:
        user_id: User identifier (can be CV ID or user email/ID)
        session: Database session (injected)
        current_user: Authenticated user (injected)
    
    Returns:
        dict: Contains:
            - user_id: The queried user ID
            - total_interactions: Total number of interactions
            - actions: Dictionary of action counts
            - recent_interactions: Last 10 interactions with details
    
    Raises:
        HTTPException: 401 if user not authenticated
        HTTPException: 403 if user tries to access others' stats (non-admin)
    
    Note:
        Users can only view their own stats unless they are admin.
    """
    from sqlmodel import select, func

    # Authorization check - users can only view their own stats unless admin
    try:
        user_id_int = int(user_id)
    except ValueError:
        user_id_int = hash(user_id) % (10 ** 8)
    
    # Check if user is requesting their own stats or is admin
    current_user_id_int = current_user.id
    if user_id_int != current_user_id_int and not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to view other users' statistics"
        )

    # Get all interactions for this user
    interactions = session.exec(
        select(UserInteraction).where(UserInteraction.user_id == user_id_int)
    ).all()

    if not interactions:
        return {
            "user_id": user_id,
            "total_interactions": 0,
            "actions": {}
        }

    # Aggregate by action
    action_counts = {}
    for interaction in interactions:
        action = interaction.action
        action_counts[action] = action_counts.get(action, 0) + 1

    return {
        "user_id": user_id,
        "total_interactions": len(interactions),
        "actions": action_counts,
        "recent_interactions": [
            {
                "job_id": i.job_id,
                "action": i.action,
                "timestamp": i.timestamp.isoformat()
            }
            for i in interactions[-10:]  # Last 10 interactions
        ]
    }


@router.get("/job/{job_id}/stats")
async def get_job_interaction_stats(
    job_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Get interaction statistics for a specific job posting.
    
    Provides engagement metrics for hirers to understand how candidates
    are interacting with their job postings.
    
    Args:
        job_id: Job identifier
        session: Database session (injected)
        current_user: Authenticated user (injected)
    
    Returns:
        dict: Contains:
            - job_id: The queried job ID
            - total_interactions: Total interaction count
            - actions: Breakdown by action type
            - engagement_rate: Percentage of views that led to applications
            - unique_users: Number of unique candidates who interacted
    
    Raises:
        HTTPException: 401 if user not authenticated
        HTTPException: 403 if user doesn't own the job (non-admin)
        HTTPException: 404 if job not found
    
    Note:
        Only job owner or admin can view job statistics.
    """
    from sqlmodel import select
    from core.db.models import Job
    
    # Verify job exists and check authorization
    job = session.exec(select(Job).where(Job.job_id == job_id)).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Authorization check - only owner or admin can view stats
    if job.owner_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to view statistics for this job"
        )

    interactions = session.exec(
        select(UserInteraction).where(UserInteraction.job_id == job_id)
    ).all()

    if not interactions:
        return {
            "job_id": job_id,
            "total_interactions": 0,
            "actions": {},
            "engagement_rate": 0
        }

    # Aggregate by action
    action_counts = {}
    for interaction in interactions:
        action = interaction.action
        action_counts[action] = action_counts.get(action, 0) + 1

    # Calculate engagement rate (applied / viewed)
    viewed = action_counts.get("viewed", 0)
    applied = action_counts.get("applied", 0)
    engagement_rate = (applied / viewed * 100) if viewed > 0 else 0

    return {
        "job_id": job_id,
        "total_interactions": len(interactions),
        "actions": action_counts,
        "engagement_rate": round(engagement_rate, 2),
        "unique_users": len(set(i.user_id for i in interactions))
    }
