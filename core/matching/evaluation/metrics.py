from typing import List, Dict, Any, Optional
import time
import numpy as np
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# --- Quality Metrics ---

def calculate_precision_at_k(recommended: List[str], relevant: List[str], k: int) -> float:
    if not relevant:
        return 0.0
    recommended_k = recommended[:k]
    relevant_set = set(relevant)
    intersection = [doc for doc in recommended_k if doc in relevant_set]
    return len(intersection) / k

def calculate_recall_at_k(recommended: List[str], relevant: List[str], k: int) -> float:
    if not relevant:
        return 0.0
    recommended_k = recommended[:k]
    relevant_set = set(relevant)
    intersection = [doc for doc in recommended_k if doc in relevant_set]
    return len(intersection) / len(relevant)

def calculate_ndcg_at_k(recommended: List[str], relevant: List[str], k: int) -> float:
    dcg = 0
    idcg = 0
    relevant_set = set(relevant)
    
    for i, doc_id in enumerate(recommended[:k]):
        if doc_id in relevant_set:
            dcg += 1 / np.log2(i + 2)
            
    # Ideal DCG
    for i in range(min(len(relevant), k)):
        idcg += 1 / np.log2(i + 2)
        
    return dcg / idcg if idcg > 0 else 0

def calculate_mrr(recommended: List[str], relevant: List[str]) -> float:
    relevant_set = set(relevant)
    for i, doc_id in enumerate(recommended):
        if doc_id in relevant_set:
            return 1 / (i + 1)
    return 0

class Evaluator:
    """Evaluates recommendation quality."""
    
    def evaluate(self, ground_truth: Dict[str, List[str]], predictions: Dict[str, List[str]], k: int = 5):
        precisions = []
        recalls = []
        ndcgs = []
        mrrs = []
        
        for query_id, relevant_ids in ground_truth.items():
            if query_id in predictions:
                pred_ids = predictions[query_id]
                p = calculate_precision_at_k(pred_ids, relevant_ids, k)
                r = calculate_recall_at_k(pred_ids, relevant_ids, k)
                ndcg = calculate_ndcg_at_k(pred_ids, relevant_ids, k)
                mrr = calculate_mrr(pred_ids, relevant_ids)
                
                precisions.append(p)
                recalls.append(r)
                ndcgs.append(ndcg)
                mrrs.append(mrr)
                
        return {
            "mean_precision_at_k": np.mean(precisions) if precisions else 0,
            "mean_recall_at_k": np.mean(recalls) if recalls else 0,
            "mean_ndcg_at_k": np.mean(ndcgs) if ndcgs else 0,
            "mrr": np.mean(mrrs) if mrrs else 0
        }

# --- Performance Metrics ---

class PerformanceMonitor:
    """Tracks and reports system performance metrics."""
    
    def __init__(self, session=None):
        self.session = session
        
    def get_system_metrics(self) -> Dict[str, Any]:
        """
        Get aggregated system metrics from the database.
        Returns latency, throughput, and DB performance.
        """
        if not self.session:
            return {}
            
        from core.db.models import SystemMetric
        from sqlmodel import select, func
        
        # 1. Average Latency (last 100 requests)
        latency_metrics = self.session.exec(
            select(SystemMetric)
            .where(SystemMetric.name == "match_latency")
            .order_by(SystemMetric.timestamp.desc())
            .limit(100)
        ).all()
        
        avg_latency = sum([m.value for m in latency_metrics]) / len(latency_metrics) if latency_metrics else 0
        
        # 2. Throughput (requests per minute)
        # Count metrics in the last hour / 60
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        throughput_count = self.session.exec(
            select(func.count(SystemMetric.id))
            .where(SystemMetric.name == "match_latency")
            .where(SystemMetric.timestamp > one_hour_ago)
        ).one()
        
        throughput_rpm = throughput_count / 60.0
        
        # 3. DB Query Performance (if tracked)
        db_metrics = self.session.exec(
            select(SystemMetric)
            .where(SystemMetric.name == "db_query_latency")
            .order_by(SystemMetric.timestamp.desc())
            .limit(100)
        ).all()
        
        avg_db_latency = sum([m.value for m in db_metrics]) / len(db_metrics) if db_metrics else 0
        
        return {
            "avg_latency_ms": round(avg_latency * 1000, 2), # Convert to ms
            "throughput_rpm": round(throughput_rpm, 2),
            "avg_db_latency_ms": round(avg_db_latency * 1000, 2),
            "latency_history": [
                {"time": m.timestamp.strftime("%H:%M:%S"), "value": m.value * 1000} 
                for m in latency_metrics[:20]
            ]
        }
    
    def log_latency(self, name: str, duration_seconds: float, tags: Dict = None):
        """Log a latency metric to the database."""
        if not self.session:
            return
            
        from core.db.models import SystemMetric
        
        metric = SystemMetric(
            name=name,
            value=duration_seconds,
            tags=tags or {},
            timestamp=datetime.utcnow()
        )
        self.session.add(metric)
        self.session.commit()

