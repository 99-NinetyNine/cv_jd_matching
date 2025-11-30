from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, WebSocket, WebSocketDisconnect
from pathlib import Path
import uuid
import json
import asyncio
from sqlmodel import Session, select
from pydantic import BaseModel
from typing import Optional
from core.db.engine import get_session
from core.db.models import Job, CV, ParsingCorrection, UserInteraction
from core.matching.semantic_matcher import HybridMatcher
from core.cache.redis_cache import redis_client
from core.parsing.main import RESUME_PARSER
from core.worker.tasks import match_cv_task
from celery.result import AsyncResult
from core.monitoring.metrics import track_time_async, log_metric
from core.matching.embeddings import EmbeddingFactory
from core.services.cv_service import get_or_parse_cv, compute_cv_embedding, update_cv_with_corrections
import numpy as np

router = APIRouter(tags=["candidate"])

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

@router.post("/upload")
async def upload_cv(file: UploadFile = File(...), session: Session = Depends(get_session)):
    # Validation
    if file.content_type != "application/pdf":
        # though we can expect user to upload docs and convert it into pdf 
        # or if user uploads text, then it's more simple, for now let's just allow pdf.
        # # NOTE: docx => pdf conversion works depending on host os(libreoffics for linux or word processors for windows or mac)
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")
        
    content = await file.read()
    if len(content) > 5 * 1024 * 1024: # 5MB
        raise HTTPException(status_code=400, detail="File is too large. Maximum size is 5MB.")
    
    file.file.seek(0)

    cv_id = str(uuid.uuid4())
    file_extension = Path(file.filename).suffix
    if not file_extension:
        file_extension = ".pdf"
        
    filename = f"{cv_id}{file_extension}"
    file_path = UPLOAD_DIR / filename
    
    with open(file_path, "wb") as buffer:
        buffer.write(content)
        
    # Create initial CV record
    cv = CV(filename=filename, content={})
    session.add(cv)
    session.commit()
    session.refresh(cv)
    
    return {"cv_id": cv_id, "filename": filename, "path": str(file_path)}

@router.post("/candidates/match")
async def match_candidate(cv_id: str, strategy: str = "pgvector", session: Session = Depends(get_session)):
    """
    Match candidate by CV ID against jobs.
    Uses cached CV data and embeddings for efficiency.
    
    Args:
        cv_id: Unique CV identifier
        strategy: Matching strategy ('pgvector' or 'naive')
    """
    # Get CV from database
    cv = session.exec(select(CV).where(CV.filename == f"{cv_id}.pdf")).first()
    if not cv or not cv.content:
        raise HTTPException(status_code=404, detail="CV not found or not parsed")
    
    cv_data = cv.content
    
    # Check cache for match results
    cache_key = f"match_results:{strategy}:{cv_id}"
    cached_results = redis_client.get(cache_key)
    
    if cached_results:
        return {"matches": json.loads(cached_results)}

    # Get CV embedding (should be cached from parsing)
    embedder = EmbeddingFactory.get_embedder(provider="ollama")
    cv_embedding = None
    
    if cv.embedding:
        cv_embedding = cv.embedding
    else:
        # Compute if not present
        cv_embedding = compute_cv_embedding(cv_id, cv_data, embedder)
        cv.embedding = cv_embedding
        session.add(cv)
        session.commit()
    
    # Prepare job candidates if using naive strategy
    job_candidates = []
    if strategy == "naive":
        jobs = session.exec(select(Job)).all()
        for job in jobs:
            j_dict = job.dict()
            if job.embedding:
                 j_dict["embedding"] = job.embedding
            job_candidates.append(j_dict)
    
    # Match using HybridMatcher with cv_id for caching
    matcher = HybridMatcher(strategy=strategy)
    cv_data_with_emb = cv_data.copy()
    cv_data_with_emb["embedding"] = cv_embedding
    matches = matcher.match(cv_data_with_emb, job_candidates, cv_id=cv_id)
    
    # Cache results
    redis_client.set(cache_key, json.dumps(matches), ttl=3600)
    
    return {"matches": matches}


@router.websocket("/ws/candidate/{cv_id}")
async def websocket_endpoint(websocket: WebSocket, cv_id: str, session: Session = Depends(get_session)):
    """ In order to make it interactive, we can use websocket"""
    
    await websocket.accept()
    try:
        # 1. Parsing Started
        await websocket.send_json({"status": "parsing_started", "message": "Parsing CV..."})
        
        # Find file
        filename = f"{cv_id}.pdf"
        file_path = UPLOAD_DIR / filename
        
        if not file_path.exists():
            await websocket.send_json({"status": "error", "message": "File not found"})
            await websocket.close()
            return

        # 2. Parse using shared service (checks DB first)
        data = get_or_parse_cv(cv_id, file_path, session)
        
        # 3. Compute embedding using shared service with ID-based caching
        embedder = EmbeddingFactory.get_embedder(provider="ollama")
        cv_embedding = compute_cv_embedding(cv_id, data, embedder)
        
        # Update CV record with embedding
        cv = session.exec(select(CV).where(CV.filename == filename)).first()
        if cv:
            cv.embedding = cv_embedding
            session.add(cv)
            session.commit()
            
        await websocket.send_json({"status": "parsing_complete", "data": data})
        
        # Wait for user confirmation (Review Step)
        try:
            msg = await websocket.receive_json()
            if msg.get("action") == "confirm":
                corrected_data = msg.get("data")
                
                # Use shared service to handle corrections
                data = update_cv_with_corrections(
                    cv_id, 
                    data, 
                    corrected_data, 
                    session,
                    embedder=embedder
                )
        except Exception as e:
            print(f"Error waiting for confirmation: {e}")
        
        # 3. Matching Started
        await websocket.send_json({"status": "matching_started", "message": "Finding best matches..."})
        
        # Trigger matching via Celery
        task = match_cv_task.delay(data)
        
        # Wait for result
        while not task.ready():
            await asyncio.sleep(0.5)
            
        matches = task.get()
        
        # Log metric: Recommendation Count
        log_metric("recommendation_count", len(matches), {"cv_id": cv_id})
        
        await websocket.send_json({"status": "complete", "matches": matches})
        
    except Exception as e:
        await websocket.send_json({"status": "error", "message": str(e)})

# to get feedback of recommendation, could be used to evaluate the quality of prediction

class InteractionCreate(BaseModel):
    user_id: int
    job_id: str
    action: str
    strategy: str = "pgvector"

@router.post("/interact")
async def log_interaction(interaction: InteractionCreate, session: Session = Depends(get_session)):
    try:
        db_interaction = UserInteraction(
            user_id=interaction.user_id, 
            job_id=interaction.job_id, 
            action=interaction.action,
            strategy=interaction.strategy
        )
        session.add(db_interaction)
        session.commit()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

