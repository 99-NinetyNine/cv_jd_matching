from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from typing import List
from core.db.engine import get_session
from core.db.models import Job, CV
from core.cache.redis_cache import redis_client


router = APIRouter(prefix="/jobs", tags=["hirer"])

@router.post("")
async def create_job(job: Job, session: Session = Depends(get_session)):
    # Generate embedding
    embeddings = get_embeddings()
    # Create a rich text representation for embedding
    job_text = f"Title: {job.title}\nCompany: {job.company}\nDescription: {job.description}"
    job.embedding = embeddings.embed_query(job_text)
    
    session.add(job)
    session.commit()
    session.refresh(job)
    
    # Cache embedding in Redis
    try:
        import numpy as np
        # Store as bytes
        redis_client.set(f"jd_embedding:{job.job_id}", np.array(job.embedding).tobytes(), ttl=604800)
    except Exception as e:
        print(f"Failed to cache JD embedding: {e}")
        
    return {"status": "Job created", "job": job}

@router.get("")
async def list_jobs(session: Session = Depends(get_session)):
    jobs = session.exec(select(Job)).all()
    return jobs
