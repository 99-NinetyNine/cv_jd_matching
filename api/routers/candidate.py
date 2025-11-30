from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, WebSocket, WebSocketDisconnect
from pathlib import Path
import uuid
import json
from sqlmodel import Session, select
from pydantic import BaseModel
from typing import Optional
from core.db.engine import get_session
from core.db.models import Job, CV, ParsingCorrection, UserInteraction
from core.matching.semantic_matcher import HybridMatcher
from core.cache.redis_cache import redis_client
from core.monitoring.metrics import log_metric
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

@router.websocket("/ws/candidate/{cv_id}")
async def websocket_endpoint(websocket: WebSocket, cv_id: str, session: Session = Depends(get_session)):
    """Interactive CV processing and matching via WebSocket."""
    
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
        embedder = EmbeddingFactory.get_embedder()
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
        
        # Call match_candidate logic directly (no Celery)
        strategy = "pgvector"
        cache_key = f"match_results:{strategy}:{cv_id}"
        cached_results = redis_client.get(cache_key)
        
        if cached_results:
            matches = json.loads(cached_results)
        else:
            # Get CV from database
            cv = session.exec(select(CV).where(CV.filename == filename)).first()
            if not cv or not cv.content:
                await websocket.send_json({"status": "error", "message": "CV not found"})
                return
            
            cv_data = cv.content
            cv_embedding = cv.embedding if (cv.embedding is not None and len(cv.embedding) > 0) else compute_cv_embedding(cv_id, cv_data, embedder)
            
            # Match using HybridMatcher
            matcher = HybridMatcher(strategy=strategy)
            cv_data_with_emb = cv_data.copy()
            cv_data_with_emb["embedding"] = cv_embedding
            matches = matcher.match(cv_data_with_emb, cv_id=cv_id)
            
            # Cache results
            redis_client.set(cache_key, json.dumps(matches), ttl=3600)
        
        # Log metric
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

