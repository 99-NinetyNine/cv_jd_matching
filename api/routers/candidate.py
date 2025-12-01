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
import logging

logger = logging.getLogger(__name__)

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
        
        # Generate unique prediction_id for this matching session
        prediction_id = str(uuid.uuid4())
        logger.info(f"Generated prediction_id {prediction_id} for CV {cv_id} with {len(matches)} matches")
        
        # Log metric
        log_metric("recommendation_count", len(matches), {"cv_id": cv_id, "prediction_id": prediction_id})
        
        await websocket.send_json({
            "status": "complete", 
            "matches": matches,
            "prediction_id": prediction_id,  # Send to frontend
            "cv_id": cv_id
        })
        
    except Exception as e:
        await websocket.send_json({"status": "error", "message": str(e)})


# Interaction tracking for evaluation and analytics

class InteractionCreate(BaseModel):
    user_id: str  # CV ID or user ID
    job_id: str
    action: str  # viewed, applied, saved, shortlisted, interviewed, hired, rejected
    strategy: str = "pgvector"
    prediction_id: Optional[str] = None  # Unique ID for this prediction session
    cv_id: Optional[str] = None  # Explicit CV ID for tracking
    interaction_metadata: Optional[dict] = None  # Additional context (e.g., rejection reason, interview date)

@router.post("/interact")
async def log_interaction(interaction: InteractionCreate, session: Session = Depends(get_session)):
    """
    Log user interactions with job postings for analytics and model evaluation.
    
    Supported actions:
    - Candidate actions: viewed, applied, saved
    - Hirer actions: shortlisted, interviewed, hired, rejected
    
    This data can be used to:
    - Evaluate recommendation quality
    - Train better matching models
    - Provide analytics to hirers
    - Improve user experience
    """
    from core.db.models import Application
    
    # Validate action type
    valid_actions = ['viewed', 'applied', 'saved', 'shortlisted', 'interviewed', 'hired', 'rejected']
    if interaction.action not in valid_actions:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalidaction. Must be one of: {', '.join(valid_actions)}"
        )
    
    try:
        # Convert user_id to int if it's numeric, otherwise use hash
        try:
            user_id_int = int(interaction.user_id)
        except ValueError:
            # Use hash of CV ID as user_id for now
            user_id_int = hash(interaction.user_id) % (10 ** 8)
        
        # Enhance metadata with prediction_id and cv_id if provided
        enhanced_metadata = interaction.interaction_metadata or {}
        if interaction.prediction_id:
            enhanced_metadata['prediction_id'] = interaction.prediction_id
        if interaction.cv_id:
            enhanced_metadata['cv_id'] = interaction.cv_id
        
        # If action is 'applied', create Application record
        application_id = None
        if interaction.action == 'applied' and interaction.cv_id and interaction.prediction_id:
            # Check if application already exists
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
                session.flush()  # Get the ID
                application_id = application.id
                enhanced_metadata['application_id'] = application_id
                logger.info(f"Created Application {application_id} for CV {interaction.cv_id}, Job {interaction.job_id}")
            else:
                application_id = existing_app.id
                enhanced_metadata['application_id'] = application_id
        
        db_interaction = UserInteraction(
            user_id=user_id_int, 
            job_id=interaction.job_id, 
            action=interaction.action,
            strategy=interaction.strategy,
            interaction_metadata=enhanced_metadata if enhanced_metadata else None
        )
        session.add(db_interaction)
        session.commit()
        
        logger.info(
            f"Logged interaction: user={interaction.user_id}, job={interaction.job_id}, "
            f"action={interaction.action}, prediction_id={interaction.prediction_id}, "
            f"application_id={application_id}"
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


