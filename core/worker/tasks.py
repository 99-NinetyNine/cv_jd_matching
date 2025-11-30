from core.worker.celery_app import celery_app
from core.matching.semantic_matcher import HybridMatcher
from core.db.engine import get_session
from core.db.models import Job
from sqlmodel import select, Session
import json
import numpy as np
from core.cache.redis_cache import redis_client

@celery_app.task
def match_cv_task(cv_data):
    # Re-instantiate matcher inside task
    matcher = HybridMatcher()
    
    # We need a DB session to fetch jobs
    # Note: Creating a new engine/session here might be expensive if done per task, 
    # but for Celery it's typical to have a session per task or use a pool.
    # Since we are using sqlmodel's create_engine which has a pool, we should be fine.
    # However, we need to import the engine creation from core.db.engine
    from core.db.engine import engine
    
    with Session(engine) as session:
        # Fetch jobs (optimized retrieval logic could be duplicated here or shared)
        # For background task, we might want to be more thorough than the real-time one
        # But let's stick to the logic: Vector Search -> Rerank
        
        # 1. Get Embedding
        cv_embedding = None
        if "embedding" in cv_data and cv_data["embedding"]:
             cv_embedding = cv_data["embedding"]
        else:
            # If not provided, we might need to compute it. 
            # But we should try to pass it to avoid re-computing in worker if possible.
            # If we must compute:
            text_rep = ""
            if "basics" in cv_data:
                text_rep += f"{cv_data['basics'].get('name', '')} {cv_data['basics'].get('summary', '')} "
            if "skills" in cv_data:
                text_rep += " ".join([s.get("name", "") if isinstance(s, dict) else str(s) for s in cv_data.get("skills", [])])
            cv_embedding = embeddings.embed_query(text_rep)
            cv_data["embedding"] = cv_embedding

        # 2. Fetch Candidates
        if cv_embedding:
             jobs = session.exec(select(Job).order_by(Job.embedding.cosine_distance(cv_embedding)).limit(50)).all()
        else:
             jobs = session.exec(select(Job)).limit(50).all()

        job_candidates = []
        for job in jobs:
            j_dict = job.dict()
            if job.embedding:
                 j_dict["embedding"] = job.embedding
            else:
                cached_emb = redis_client.get(f"jd_embedding:{job.job_id}")
                if cached_emb:
                    j_dict["embedding"] = np.frombuffer(cached_emb, dtype=np.float64).tolist()
            job_candidates.append(j_dict)
            
        # 3. Match
        matches = matcher.match(cv_data, job_candidates)
        
        return matches
