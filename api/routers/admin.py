from fastapi import APIRouter, Depends
from sqlmodel import Session, select, func
from core.db.engine import get_session
from core.db.models import User, CV, Job, SystemMetric, UserInteraction, ParsingCorrection
from core.auth.security import verify_password
from api.routers.auth import get_current_user
from typing import List, Dict
import datetime

router = APIRouter(tags=["admin"])

def calculate_precision_recall(interactions: List[UserInteraction], total_recommendations: int):
    # Simplified logic for demo
    # Precision = Relevant (Clicked/Applied) / Total Recommended
    # Recall = Relevant (Clicked/Applied) / Total Relevant (Approximated by total interactions for now)
    
    relevant_count = len([i for i in interactions if i.action in ["click", "apply"]])
    
    precision = relevant_count / total_recommendations if total_recommendations > 0 else 0
    recall = relevant_count / (relevant_count + 5) if relevant_count > 0 else 0 # Mock total relevant
    
    return precision, recall

@router.get("/admin/metrics")
async def get_metrics(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    if not current_user.is_admin:
        # For demo, allow anyone or check specific admin flag
        # raise HTTPException(status_code=403, detail="Not authorized")
        pass

    # Counts
    total_users = session.exec(select(func.count(User.id))).one()
    total_cvs = session.exec(select(func.count(CV.id))).one()
    total_jobs = session.exec(select(func.count(Job.id))).one()
    
    # Latency (from SystemMetric)
    # Get average of last 100 'match_latency' metrics
    latency_metrics = session.exec(select(SystemMetric).where(SystemMetric.name == "match_latency").order_by(SystemMetric.timestamp.desc()).limit(100)).all()
    avg_latency = sum([m.value for m in latency_metrics]) / len(latency_metrics) if latency_metrics else 0
    
    # Precision/Recall
    interactions = session.exec(select(UserInteraction)).all()
    # We need total recommendations count. Let's approximate or fetch from metrics
    rec_metrics = session.exec(select(SystemMetric).where(SystemMetric.name == "recommendation_count")).all()
    total_recs = sum([m.value for m in rec_metrics])
    
    precision, recall = calculate_precision_recall(interactions, total_recs)
    
    return {
        "totalUsers": total_users,
        "totalCVs": total_cvs,
        "totalJobs": total_jobs,
        "avgLatency": round(avg_latency, 2),
        "precision": round(precision, 2),
        "recall": round(recall, 2),
        "latencyHistory": [{"time": m.timestamp.strftime("%H:%M"), "latency": m.value} for m in latency_metrics[:20]], # Last 20
        "matchQuality": [
            {"name": "Precision", "value": round(precision, 2)},
            {"name": "Recall", "value": round(recall, 2)},
            {"name": "F1 Score", "value": round(2 * (precision * recall) / (precision + recall), 2) if (precision + recall) > 0 else 0}
        ]
    }
