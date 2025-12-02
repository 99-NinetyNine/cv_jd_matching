from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, WebSocket, WebSocketDisconnect
from pathlib import Path
import uuid
import json
from sqlmodel import Session, select
from pydantic import BaseModel
from typing import Optional
from core.db.engine import get_session
from core.db.models import Job, CV, ParsingCorrection, UserInteraction, Prediction
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
        
    # 2 Create CV record
    cv = CV(
        filename=filename,
        content={},
        embedding_status="pending",
        parsing_status="pending",
        is_latest=True
    )
    session.add(cv)
    session.commit()
    session.refresh(cv)
    
    return {"cv_id": cv_id, "filename": filename, "path": str(file_path)}


# TODO: allow for admin only, for testing manually: upload and parse both
@router.post("/upload_and_parse")
async def upload_and_parse_cv(file: UploadFile = File(...), session: Session = Depends(get_session)):
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
        
    # 2 Create CV record
    cv = CV(
        filename=filename,
        content={},
        embedding_status="pending",
        is_latest=True
    )
    session.add(cv)
    session.commit()
    session.refresh(cv)
    
    data = get_or_parse_cv(cv_id, file_path, session)
        
    return {"cv_id": cv_id, "filename": filename, "path": str(file_path), "data": data}


# TODO: can be removed for testing matching result immediately after upload
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
        # this can be batched if cv is blindly assumed to be ok, like in linkedin 
        data = get_or_parse_cv(cv_id, file_path, session)
        
        cv = session.exec(select(CV).where(CV.filename == filename)).first()
        if not cv:
             await websocket.send_json({"status": "error", "message": "CV record not found"})
             return

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
                )
        except Exception as e:
            print(f"Error waiting for confirmation: {e}")
        # 3. Check for Batch vs Immediate Processing
        # Logic: Immediate if Premium OR last update > 1 month ago OR never
        # Determine Premium Status
        import datetime
        from core.db.models import User
        is_premium = False
        if cv.owner_id:
            user = session.get(User, cv.owner_id)
            if user:
                is_premium = user.is_premium
        
        # TODO: not cv last updated but the cv's owner last cv analyzed date
        needs_update = True
        if is_premium is False:
            last_updated = user.last_cv_analyzed
            if last_updated:
                delta = datetime.datetime.utcnow() - last_updated
                if delta.days < 30:
                    needs_update = False
        
        # Decision: Immediate vs Batch Processing
        should_process_immediately = is_premium or needs_update
        
        
        # Immediate Processing
        # Matching Started
        await websocket.send_json({"status": "matching_started", "message": "Finding best matches..."})
        
        # Call match_candidate logic directly (no Celery)
        strategy = "pgvector"
        cache_key = f"match_results:{strategy}:{cv_id}"
        cached_results = redis_client.get(cache_key)
        
        if cached_results:
            matches = json.loads(cached_results)
        
        else:
            if should_process_immediately:
                # Refresh CV from database
                cv = session.exec(select(CV).where(CV.filename == filename)).first()
                if not cv or not cv.content:
                    await websocket.send_json({"status": "error", "message": "CV not found"})
                    return
                
                # Match using HybridMatcher
                matcher = HybridMatcher(strategy=strategy)
                matches = matcher.match(cv_id=cv_id)
                
                # Cache results
                redis_client.set(cache_key, json.dumps(matches), ttl=3600)
            
                # Generate unique prediction_id for this matching session
                prediction_id = str(uuid.uuid4())
                
                # Save predictions to DB
                prediction = Prediction(
                    prediction_id=prediction_id,
                    cv_id=cv_id,
                    matches=matches
                )
                session.add(prediction)
                session.commit()
                
                logger.info(f"Generated prediction_id {prediction_id} for CV {cv_id} with {len(matches)} matches")
                
                # Log metric
                log_metric("recommendation_count", len(matches), {"cv_id": cv_id, "prediction_id": prediction_id})
            else:
                # Batch Mode - Queue for batch processing
                cv.embedding_status = "pending_batch"
                session.add(cv)
                session.commit()
                
                # Try to get stored predictions for that CV from the Database
                # This is useful if the user refreshes the page while batch is processing or if they have old predictions
                latest_prediction = session.exec(
                    select(Prediction)
                    .where(Prediction.cv_id == cv_id)
                    .order_by(Prediction.created_at.desc())
                ).first()
                
                if latest_prediction:
                    matches = latest_prediction.matches
                    prediction_id = latest_prediction.prediction_id
                    logger.info(f"Using stored predictions for CV {cv_id} (Batch Mode)")
                else:
                    matches = []
                    prediction_id = None
                    logger.info(f"No stored predictions for CV {cv_id} (Batch Mode)")
                

        # Extract candidate name from CV data
        candidate_name = "Unknown"
        if cv and cv.content:
            basics = cv.content.get("basics", {})
            if isinstance(basics, dict):
                candidate_name = basics.get("name", "Unknown")
        
        # anyways return the matches
        await websocket.send_json({
            "status": "complete",
            "candidate_id": cv_id,
            "candidate_name": candidate_name,
            "recommendations": matches,  # Renamed from 'matches' to match spec
            "prediction_id": prediction_id,  # Send to frontend
            "cv_id": cv_id
        })
        
    except Exception as e:
        await websocket.send_json({"status": "error", "message": str(e)})


@router.get("/recommendations")
async def get_recommendations(session: Session = Depends(get_session)):
    """
    Get job recommendations for the user's latest CV.
    Uses cached results if available, otherwise computes new matches.
    """
    # 1. Find the latest CV (using is_latest flag)
    cv = session.exec(
        select(CV)
        .where(CV.is_latest == True)
        .where(CV.embedding_status == "completed")
        .order_by(CV.created_at.desc())
    ).first()
    
    if not cv:
        raise HTTPException(status_code=404, detail="No CV found. Please upload a CV first.")
    
    cv_id = str(cv.id)
        
    # 2. Check Cache
    strategy = "pgvector"
    cache_key = f"match_results:{strategy}:{cv_id}"
    cached_results = redis_client.get(cache_key)
    
    if cached_results:
        matches = json.loads(cached_results)
        logger.info(f"Returning cached matches for CV {cv_id}")
        
        # Get prediction_id from DB
        latest_prediction = session.exec(
            select(Prediction)
            .where(Prediction.cv_id == cv_id)
            .order_by(Prediction.created_at.desc())
        ).first()
        
        # Extract candidate name
        candidate_name = "Unknown"
        if cv and cv.content:
            basics = cv.content.get("basics", {})
            if isinstance(basics, dict):
                candidate_name = basics.get("name", "Unknown")
        
        return {
            "candidate_id": cv_id,
            "candidate_name": candidate_name,
            "recommendations": matches,
            "prediction_id": latest_prediction.prediction_id if latest_prediction else None,
            "count": len(matches)
        }
    
    # 3. Check DB for recent predictions
    latest_prediction = session.exec(
        select(Prediction)
        .where(Prediction.cv_id == cv_id)
        .order_by(Prediction.created_at.desc())
    ).first()
    
    # Use stored prediction if available
    if latest_prediction:
         matches = latest_prediction.matches
         prediction_id = latest_prediction.prediction_id
         logger.info(f"Returning stored DB matches for CV {cv_id}")
         
         # Cache for next time
         redis_client.set(cache_key, json.dumps(matches), ttl=3600)
         
         # Extract candidate name
         candidate_name = "Unknown"
         if cv and cv.content:
             basics = cv.content.get("basics", {})
             if isinstance(basics, dict):
                 candidate_name = basics.get("name", "Unknown")
         
         return {
            "candidate_id": cv_id,
            "candidate_name": candidate_name,
            "recommendations": matches,
            "prediction_id": prediction_id,
            "count": len(matches)
        }

    # 4. No cached or stored results - compute new matches
    if not cv.content:
        raise HTTPException(status_code=400, detail="CV content not parsed yet")
        
    


