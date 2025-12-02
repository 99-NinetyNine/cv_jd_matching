"""
Enhanced admin endpoints with comprehensive evaluation and performance metrics.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, func
from core.db.engine import get_session
from core.db.models import User, CV, Job, SystemMetric, UserInteraction, Prediction, Application, BatchJob
from core.auth.security import verify_password
from api.routers.auth import get_current_user
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/evaluation_metrics")
async def get_evaluation_metrics(
    session: Session = Depends(get_session),
    days: int = 30
):
    """
    Get comprehensive evaluation metrics for the recommendation system.
    Includes CTR, conversion rates, intrinsic/extrinsic factors.

    Args:
        days: Number of days to analyze (default 30)
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    # Get all interactions in time period
    interactions = session.exec(
        select(UserInteraction).where(UserInteraction.timestamp >= cutoff_date)
    ).all()

    # Calculate CTR (Click-Through Rate)
    viewed_count = len([i for i in interactions if i.action == "viewed"])
    clicked_count = len([i for i in interactions if i.action in ["applied", "saved"]])
    ctr = (clicked_count / viewed_count * 100) if viewed_count > 0 else 0

    # Calculate Application Rate
    applications = session.exec(
        select(Application).where(Application.applied_at >= cutoff_date)
    ).all()
    application_rate = (len(applications) / viewed_count * 100) if viewed_count > 0 else 0

    # Conversion funnel
    viewed_jobs = len(set(i.job_id for i in interactions if i.action == "viewed"))
    applied_jobs = len(set(i.job_id for i in interactions if i.action == "applied"))
    hired_count = len([i for i in interactions if i.action == "hired"])

    # Calculate acceptance rate (hirer perspective)
    accepted_apps = len([a for a in applications if a.status == "accepted"])
    acceptance_rate = (accepted_apps / len(applications) * 100) if applications else 0

    # Intrinsic factors (from system design)
    intrinsic_factors = {
        "skills_match_weight": 0.35,
        "experience_match_weight": 0.25,
        "education_match_weight": 0.15,
        "semantic_similarity_weight": 0.25,
        "reranker_enabled": True,
        "embedding_model": "nomic-embed-text",
        "nlp_skills_extraction": True,
        "semantic_skills_matching": True
    }

    # Extrinsic factors (user behavior)
    applied_interactions = [i for i in interactions if i.action == "applied" and i.interaction_metadata]
    hired_interactions = [i for i in interactions if i.action == "hired" and i.interaction_metadata]

    # Extract match scores if available in metadata
    avg_match_score_applied = 0.0
    avg_match_score_hired = 0.0

    if applied_interactions:
        scores = [
            i.interaction_metadata.get("match_score", 0)
            for i in applied_interactions
            if i.interaction_metadata and "match_score" in i.interaction_metadata
        ]
        avg_match_score_applied = sum(scores) / len(scores) if scores else 0.0

    if hired_interactions:
        scores = [
            i.interaction_metadata.get("match_score", 0)
            for i in hired_interactions
            if i.interaction_metadata and "match_score" in i.interaction_metadata
        ]
        avg_match_score_hired = sum(scores) / len(scores) if scores else 0.0

    # Time-based metrics
    peak_hour = _get_peak_hour(interactions)

    # Top performing jobs
    job_interactions = {}
    for interaction in interactions:
        job_id = interaction.job_id
        if job_id not in job_interactions:
            job_interactions[job_id] = {"viewed": 0, "applied": 0, "hired": 0, "saved": 0}
        action = interaction.action
        if action in job_interactions[job_id]:
            job_interactions[job_id][action] += 1

    top_jobs = sorted(
        job_interactions.items(),
        key=lambda x: x[1].get("applied", 0),
        reverse=True
    )[:10]

    # Calculate precision and recall (simplified)
    # Relevant = applied or hired
    relevant_count = len([i for i in interactions if i.action in ["applied", "hired"]])
    total_recommended = viewed_count

    precision = (relevant_count / total_recommended) if total_recommended > 0 else 0
    # Recall is harder to calculate without ground truth, use approximation
    recall = (relevant_count / (relevant_count + 10)) if relevant_count > 0 else 0  # Approximation
    f1_score = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0

    return {
        "period_days": days,
        "generated_at": datetime.utcnow().isoformat(),
        "summary": {
            "total_interactions": len(interactions),
            "total_views": viewed_count,
            "total_applications": len(applications),
            "total_hired": hired_count,
            "ctr_percent": round(ctr, 2),
            "application_rate_percent": round(application_rate, 2),
            "acceptance_rate_percent": round(acceptance_rate, 2)
        },
        "quality_metrics": {
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "f1_score": round(f1_score, 3)
        },
        "conversion_funnel": {
            "viewed": viewed_jobs,
            "applied": applied_jobs,
            "hired": hired_count,
            "view_to_apply_percent": round((applied_jobs / viewed_jobs * 100), 2) if viewed_jobs > 0 else 0,
            "apply_to_hire_percent": round((hired_count / applied_jobs * 100), 2) if applied_jobs > 0 else 0
        },
        "intrinsic_factors": intrinsic_factors,
        "extrinsic_factors": {
            "avg_match_score_applied": round(avg_match_score_applied, 3),
            "avg_match_score_hired": round(avg_match_score_hired, 3),
            "peak_interaction_hour": peak_hour,
            "user_engagement_score": round((clicked_count / viewed_count), 3) if viewed_count > 0 else 0
        },
        "top_jobs": [
            {
                "job_id": job_id,
                "views": stats["viewed"],
                "applications": stats["applied"],
                "hired": stats.get("hired", 0),
                "saved": stats.get("saved", 0),
                "engagement_rate": round((stats["applied"] + stats.get("saved", 0)) / stats["viewed"] * 100, 2) if stats["viewed"] > 0 else 0
            }
            for job_id, stats in top_jobs
        ],
        "actions_breakdown": {
            action: len([i for i in interactions if i.action == action])
            for action in ["viewed", "applied", "saved", "shortlisted", "interviewed", "hired", "rejected"]
        }
    }


def _get_peak_hour(interactions: List[UserInteraction]) -> int:
    """Get the hour of day with most interactions."""
    if not interactions:
        return 0

    hour_counts = {}
    for interaction in interactions:
        hour = interaction.timestamp.hour
        hour_counts[hour] = hour_counts.get(hour, 0) + 1

    return max(hour_counts.items(), key=lambda x: x[1])[0] if hour_counts else 0


@router.get("/performance_dashboard")
async def get_performance_dashboard(session: Session = Depends(get_session)):
    """
    Get comprehensive performance metrics for the admin dashboard.
    Includes parsing, embedding, matching, and database performance.
    """
    cutoff_24h = datetime.utcnow() - timedelta(hours=24)

    # Parsing performance
    recent_cvs = session.exec(
        select(CV).where(CV.created_at >= cutoff_24h)
    ).all()

    parsing_completed = len([cv for cv in recent_cvs if cv.parsing_status == "completed"])
    parsing_failed = len([cv for cv in recent_cvs if cv.parsing_status == "failed"])
    parsing_pending = len([cv for cv in recent_cvs if cv.parsing_status in ["pending", "pending_batch", "processing"]])

    # Embedding performance
    embedding_completed = len([cv for cv in recent_cvs if cv.embedding_status == "completed"])
    embedding_failed = len([cv for cv in recent_cvs if cv.embedding_status == "failed"])
    embedding_pending = len([cv for cv in recent_cvs if cv.embedding_status in ["pending", "pending_batch", "processing"]])

    # Get recent system metrics
    metrics = session.exec(
        select(SystemMetric).where(SystemMetric.timestamp >= cutoff_24h).order_by(SystemMetric.timestamp.desc()).limit(1000)
    ).all()

    # Group by metric name
    metric_groups = {}
    for metric in metrics:
        if metric.name not in metric_groups:
            metric_groups[metric.name] = []
        metric_groups[metric.name].append(metric.value)

    # Calculate averages and percentiles
    avg_metrics = {}
    p95_metrics = {}
    for name, values in metric_groups.items():
        if values:
            avg_metrics[name] = round(sum(values) / len(values), 2)
            sorted_values = sorted(values)
            p95_index = int(len(sorted_values) * 0.95)
            p95_metrics[name] = round(sorted_values[p95_index], 2) if p95_index < len(sorted_values) else 0

    # Batch job status
    recent_batches = session.exec(
        select(BatchJob).where(BatchJob.created_at >= cutoff_24h)
    ).all()

    batch_summary = {
        "total": len(recent_batches),
        "pending": len([b for b in recent_batches if b.status == "pending"]),
        "processing": len([b for b in recent_batches if b.status == "processing"]),
        "completed": len([b for b in recent_batches if b.status == "completed"]),
        "failed": len([b for b in recent_batches if b.status == "failed"])
    }

    # Database sizes
    total_cvs = session.exec(select(func.count(CV.id))).one()
    total_jobs = session.exec(select(func.count(Job.id))).one()
    total_predictions = session.exec(select(func.count(Prediction.id))).one()
    total_interactions = session.exec(select(func.count(UserInteraction.id))).one()

    return {
        "period": "Last 24 hours",
        "timestamp": datetime.utcnow().isoformat(),
        "parsing": {
            "total_processed": len(recent_cvs),
            "completed": parsing_completed,
            "failed": parsing_failed,
            "pending": parsing_pending,
            "success_rate_percent": round((parsing_completed / len(recent_cvs) * 100), 2) if recent_cvs else 0
        },
        "embedding": {
            "total_processed": len(recent_cvs),
            "completed": embedding_completed,
            "failed": embedding_failed,
            "pending": embedding_pending,
            "success_rate_percent": round((embedding_completed / len(recent_cvs) * 100), 2) if recent_cvs else 0
        },
        "performance_metrics": {
            "averages": avg_metrics,
            "p95_percentiles": p95_metrics
        },
        "batch_jobs": batch_summary,
        "database": {
            "total_cvs": total_cvs,
            "total_jobs": total_jobs,
            "total_predictions": total_predictions,
            "total_interactions": total_interactions,
            "cvs_with_embeddings": session.exec(
                select(func.count(CV.id)).where(CV.embedding_status == "completed")
            ).one(),
            "jobs_with_embeddings": session.exec(
                select(func.count(Job.id)).where(Job.embedding_status == "completed")
            ).one()
        }
    }


@router.post("/test_celery")
async def test_celery_worker():
    """Test if Celery worker is running."""
    try:
        from core.worker.tasks import test_celery_task
        result = test_celery_task.delay("Admin test message")
        return {
            "status": "success",
            "message": "Celery task queued successfully",
            "task_id": result.id,
            "note": "Check Celery worker logs to verify execution"
        }
    except Exception as e:
        logger.error(f"Celery test failed: {e}")
        return {
            "status": "error",
            "message": str(e),
            "note": "Celery worker may not be running. Start with: celery -A core.worker.celery_app worker --loglevel=info"
        }


@router.post("/trigger_batch_parsing")
async def trigger_batch_parsing():
    """Trigger batch CV parsing task."""
    try:
        from core.worker.tasks import process_batch_cv_parsing
        result = process_batch_cv_parsing.delay()
        return {
            "status": "success",
            "message": "Batch parsing task queued",
            "task_id": result.id,
            "note": "CVs with parsing_status='pending_batch' will be processed"
        }
    except Exception as e:
        logger.error(f"Batch parsing trigger failed: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


@router.get("/system_health")
async def get_system_health(session: Session = Depends(get_session)):
    """
    Get overall system health status.
    """
    try:
        # Database connectivity
        db_check = session.exec(select(func.count(CV.id))).one() is not None

        # Count pending items
        pending_parsing = session.exec(
            select(func.count(CV.id)).where(CV.parsing_status.in_(["pending", "pending_batch"]))
        ).one()

        pending_embedding = session.exec(
            select(func.count(CV.id)).where(CV.embedding_status.in_(["pending", "pending_batch"]))
        ).one()

        # Check for recent failures
        recent_failures = session.exec(
            select(func.count(CV.id)).where(
                CV.parsing_status == "failed",
                CV.created_at >= datetime.utcnow() - timedelta(hours=1)
            )
        ).one()

        # Celery health (attempt to check)
        celery_healthy = True
        try:
            from core.worker.celery_app import celery_app
            # Check if we can get celery stats
            inspect = celery_app.control.inspect()
            active_workers = inspect.active()
            celery_healthy = active_workers is not None and len(active_workers) > 0
        except Exception:
            celery_healthy = False

        overall_status = "healthy" if (db_check and celery_healthy and recent_failures < 10) else "degraded"

        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                "database": "healthy" if db_check else "unhealthy",
                "celery_workers": "healthy" if celery_healthy else "unhealthy",
                "api": "healthy"
            },
            "pending_work": {
                "parsing": pending_parsing,
                "embedding": pending_embedding
            },
            "recent_failures": recent_failures
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
