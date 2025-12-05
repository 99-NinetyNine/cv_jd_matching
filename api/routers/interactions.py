"""
Unified interaction tracking for both candidates and hirers.
Simple, elegant, and sufficient for AI/analytics purposes.

Modular design with composable validators and handlers.
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from pydantic import BaseModel
from typing import Optional, Dict, Any, Union
from datetime import datetime
import logging

from core.db.engine import get_session
from core.db.models import UserInteraction, Application, User
from api.routers.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/interactions", tags=["interactions"])


# ==================== VALIDATORS ====================

def validate_action_for_user_type(user_type: str, action: str) -> None:
    """Validate that action is allowed for user type."""
    candidate_actions = ["viewed", "saved", "applied"]
    hirer_actions = ["shortlisted", "interviewed", "hired", "rejected"]

    if user_type == "candidate":
        if action not in candidate_actions:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid candidate action. Must be one of: {', '.join(candidate_actions)}"
            )
    elif user_type == "hirer":
        if action not in hirer_actions:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid hirer action. Must be one of: {', '.join(hirer_actions)}"
            )
    else:
        raise HTTPException(
            status_code=400,
            detail="user_type must be 'candidate' or 'hirer'"
        )


def check_duplicate_interaction(
    session: Session,
    user_id: int,
    job_id: str,
    action: str
) -> Optional[Dict[str, Any]]:
    """
    Check for duplicate interactions and return early response if duplicate found.

    Returns:
        None if no duplicate found (continue processing)
        Dict with response if duplicate found (return to client)
    """
    # Prevent duplicate "applied" actions
    if action == "applied":
        existing_apply = session.exec(
            select(UserInteraction).where(
                UserInteraction.user_id == user_id,
                UserInteraction.job_id == job_id,
                UserInteraction.action == "applied"
            )
        ).first()

        if existing_apply:
            logger.warning(f"User {user_id} already applied to job {job_id}")
            return {
                "status": "already_exists",
                "message": "You have already applied to this job",
                "application_id": None
            }

    # Prevent duplicate "saved" actions
    if action == "saved":
        existing_saved = session.exec(
            select(UserInteraction).where(
                UserInteraction.user_id == user_id,
                UserInteraction.job_id == job_id,
                UserInteraction.action == "saved"
            )
        ).first()

        if existing_saved:
            logger.info(f"User {user_id} already saved job {job_id}, skipping duplicate")
            return {
                "status": "already_exists",
                "message": "Job already saved",
                "application_id": None
            }

    # Limit "viewed" interactions to 1 per user per job
    if action == "viewed":
        existing_view = session.exec(
            select(UserInteraction).where(
                UserInteraction.user_id == user_id,
                UserInteraction.job_id == job_id,
                UserInteraction.action == "viewed"
            )
        ).first()

        if existing_view:
            logger.info(f"User {user_id} already viewed job {job_id}, skipping duplicate")
            return {
                "status": "already_exists",
                "message": "View already logged",
                "application_id": None
            }

    return None


# ==================== HANDLERS ====================

def build_metadata(interaction: "InteractionCreate", user_type: str) -> Dict[str, Any]:
    """Build enhanced metadata for interaction."""
    metadata = interaction.metadata or {}
    metadata.update({
        "user_type": user_type,
        "cv_id": interaction.cv_id,
        "prediction_id": interaction.prediction_id,
        "application_id": interaction.application_id,
        "timestamp": datetime.utcnow().isoformat()
    })
    return metadata


def handle_application_creation(
    session: Session,
    interaction: "InteractionCreate"
) -> Optional[int]:
    """
    Handle application creation for 'applied' action.

    Returns:
        application_id if created or found, None otherwise
    """
    if interaction.action != "applied" or not interaction.cv_id or not interaction.prediction_id:
        return interaction.application_id

    # Check for existing application
    existing_app = session.exec(
        select(Application).where(
            Application.cv_id == interaction.cv_id,
            Application.job_id == str(interaction.job_id)
        )
    ).first()

    if existing_app:
        logger.info(f"Application already exists: {existing_app.id}")
        return existing_app.id

    # Verify job exists before creating application
    from core.db.models import Job
    job_exists = session.exec(
        select(Job).where(Job.job_id == str(interaction.job_id))
    ).first()

    if not job_exists:
        logger.warning(f"Job {interaction.job_id} not found in database. Skipping application creation.")
        return None

    # Create new application
    application = Application(
        cv_id=interaction.cv_id,
        job_id=str(interaction.job_id),
        prediction_id=interaction.prediction_id,
        status="pending"
    )
    session.add(application)
    session.flush()
    logger.info(f"Created Application {application.id}")
    return application.id


def handle_application_status_update(
    session: Session,
    interaction: "InteractionCreate",
    user_type: str
) -> None:
    """Handle application status updates for hirer actions."""
    if user_type != "hirer" or not interaction.application_id:
        return

    application = session.get(Application, interaction.application_id)
    if not application:
        logger.warning(f"Application {interaction.application_id} not found")
        return

    # Map hirer actions to application statuses
    status_map = {
        "shortlisted": "pending",
        "interviewed": "pending",
        "hired": "accepted",
        "rejected": "rejected"
    }

    new_status = status_map.get(interaction.action)
    if not new_status:
        return

    application.status = new_status
    if new_status in ["accepted", "rejected"]:
        application.decision_at = datetime.utcnow()

    session.add(application)
    logger.info(f"Updated Application {application.id} to {new_status}")


def create_interaction_record(
    session: Session,
    user_id: int,
    interaction: "InteractionCreate",
    metadata: Dict[str, Any]
) -> UserInteraction:
    """Create and persist interaction record."""
    db_interaction = UserInteraction(
        user_id=user_id,
        job_id=str(interaction.job_id),
        action=interaction.action,
        strategy="pgvector",
        interaction_metadata=metadata
    )
    session.add(db_interaction)
    return db_interaction


class InteractionCreate(BaseModel):
    """Unified interaction model for both candidates and hirers."""
    # Who (user_id and user_type are both injected from current_user)

    # What
    job_id: Union[str, int]
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
    - `viewed`: Candidate viewed a job recommendation (max 1 per user-job)
    - `saved`: Candidate bookmarked a job for later
    - `applied`: Candidate submitted an application (max 1 per user-job)

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
        - Prevents duplicate applies and excessive views

    Example:
        ```python
        # Candidate views a job
        POST /interactions/log
        {
            "job_id": "job_456",
            "action": "viewed",
            "prediction_id": "pred_789"
        }

        # Hirer shortlists a candidate
        POST /interactions/log
        {
            "job_id": "job_456",
            "action": "shortlisted",
            "application_id": 42
        }
        ```
    """

    # Step 1: Extract user info from auth
    user_id_int = current_user.id
    user_type = current_user.role  # "candidate", "hirer", or "admin"

    # Step 2: Validate action for user type
    validate_action_for_user_type(user_type, interaction.action)

    try:
        # Step 3: Check for duplicate interactions
        duplicate_check = check_duplicate_interaction(
            session, user_id_int, str(interaction.job_id), interaction.action
        )
        if duplicate_check:
            return duplicate_check

        # Step 3: Build metadata
        metadata = build_metadata(interaction, user_type)

        # Step 4: Handle application creation (for "applied" action)
        application_id = handle_application_creation(session, interaction)
        if application_id:
            metadata["application_id"] = application_id

        # Step 5: Handle application status updates (for hirer actions)
        handle_application_status_update(session, interaction, user_type)

        # Step 6: Create interaction record
        create_interaction_record(session, user_id_int, interaction, metadata)

        # Step 7: Commit transaction
        session.commit()

        logger.info(
            f"✓ Logged: {user_type} {user_id_int} "
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


@router.get("/my")
async def get_my_interactions(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get all interactions for the current user."""
    interactions = session.exec(
        select(UserInteraction).where(UserInteraction.user_id == current_user.id)
    ).all()
    
    return {
        "interactions": [
            {
                "job_id": i.job_id,
                "action": i.action,
                "timestamp": i.timestamp
            }
            for i in interactions
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
