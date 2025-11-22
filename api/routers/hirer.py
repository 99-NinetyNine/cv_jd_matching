from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from typing import List
from core.db.engine import get_session
from core.db.models import Job, CV

router = APIRouter(prefix="/jobs", tags=["hirer"])

@router.post("")
async def create_job(job: Job, session: Session = Depends(get_session)):
    # In a real app we'd generate embedding here too
    session.add(job)
    session.commit()
    session.refresh(job)
    return {"status": "Job created", "job": job}

@router.get("")
async def list_jobs(session: Session = Depends(get_session)):
    jobs = session.exec(select(Job)).all()
    return jobs
