from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, WebSocket, WebSocketDisconnect
from pathlib import Path
import uuid
import json
import asyncio
from sqlmodel import Session, select
from pydantic import BaseModel
from core.db.engine import get_session
from core.db.models import Job, CV, ParsingCorrection, UserInteraction
from core.matching.semantic_matcher import HybridMatcher
from core.cache.redis_cache import redis_client
from core.llm.factory import get_embeddings
from core.parsing.main import RESUME_PARSER
from core.worker.tasks import match_cv_task
from celery.result import AsyncResult
from core.monitoring.metrics import track_time_async, log_metric
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
async def match_candidate(cv_data: dict, session: Session = Depends(get_session)):
    # Check cache first
    import hashlib
    # Create a hash of the CV data to use as cache key
    cv_hash = hashlib.md5(json.dumps(cv_data, sort_keys=True).encode()).hexdigest()
    cache_key = f"match_results:{cv_hash}"
    cached_results = redis_client.get(cache_key)
    
    if cached_results:
        return {"matches": json.loads(cached_results)}

    # Get top 50 candidates using vector search
    # We need to compute CV embedding first if not present
    cv_embedding = None
    if "embedding" in cv_data:
        cv_embedding = cv_data["embedding"]
    else:
        # Compute embedding
        embeddings = get_embeddings()
        text_rep = ""
        if "basics" in cv_data:
            text_rep += f"{cv_data['basics'].get('name', '')} {cv_data['basics'].get('summary', '')} "
        if "skills" in cv_data:
            text_rep += " ".join([s.get("name", "") if isinstance(s, dict) else str(s) for s in cv_data.get("skills", [])])
        cv_embedding = embeddings.embed_query(text_rep)

    # Query DB for top 50 matches
    jobs = session.exec(select(Job).order_by(Job.embedding.cosine_distance(cv_embedding)).limit(50)).all()
    
    # Prepare job candidates with embeddings
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
    
    matcher = HybridMatcher()
    # Pass embedding to matcher to avoid re-computing
    cv_data_with_emb = cv_data.copy()
    cv_data_with_emb["embedding"] = cv_embedding
    matches = matcher.match(cv_data_with_emb, job_candidates)
    
    # Cache results
    redis_client.set(cache_key, json.dumps(matches), ttl=3600)
    
    return {"matches": matches}

@router.websocket("/ws/candidate/{cv_id}")
async def websocket_endpoint(websocket: WebSocket, cv_id: str, session: Session = Depends(get_session)):
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

        # 2. Parse
        parser = RESUME_PARSER
        data = parser.parse(file_path)
        
        # Update CV record
        cv = session.exec(select(CV).where(CV.filename == filename)).first()
        if cv:
            cv.content = data
            # Compute embedding
            embeddings = get_embeddings()
            # Create text representation for embedding
            text_rep = ""
            if "basics" in data:
                text_rep += f"{data['basics'].get('name', '')} {data['basics'].get('summary', '')} "
            if "skills" in data:
                text_rep += " ".join([s.get("name", "") if isinstance(s, dict) else str(s) for s in data.get("skills", [])])
            
            cv.embedding = embeddings.embed_query(text_rep)
            session.add(cv)
            session.commit()
            
            # Cache embedding
            redis_client.set(f"cv_embedding:{cv_id}", np.array(cv.embedding).tobytes(), ttl=86400)
            
        await websocket.send_json({"status": "parsing_complete", "data": data})
        
        # Wait for user confirmation (Review Step)
        # We expect a message from client: {"action": "confirm", "data": {...}}
        try:
            msg = await websocket.receive_json()
            if msg.get("action") == "confirm":
                confirmed_data = msg.get("data")
                
                # Check for corrections
                if confirmed_data != data:
                    # Save correction
                    correction = ParsingCorrection(
                        cv_id=cv_id,
                        original_data=data,
                        corrected_data=confirmed_data
                    )
                    session.add(correction)
                    session.commit()
                    
                    # Update CV with confirmed data
                    if cv:
                        cv.content = confirmed_data
                        # Re-compute embedding if text changed significantly
                        # For simplicity, let's assume we re-compute
                        embeddings = get_embeddings()
                        text_rep = ""
                        if "basics" in confirmed_data:
                            text_rep += f"{confirmed_data['basics'].get('name', '')} {confirmed_data['basics'].get('summary', '')} "
                        if "skills" in confirmed_data:
                            text_rep += " ".join([s.get("name", "") if isinstance(s, dict) else str(s) for s in confirmed_data.get("skills", [])])
                        
                        cv.embedding = embeddings.embed_query(text_rep)
                        session.add(cv)
                        session.commit()
                        
                        # Cache embedding
                        redis_client.set(f"cv_embedding:{cv_id}", np.array(cv.embedding).tobytes(), ttl=86400)
                
                data = confirmed_data # Use confirmed data for matching
            else:
                # If not confirm, maybe cancel or just proceed?
                # Let's assume proceed with original if something else comes (or handle error)
                pass
                
        except Exception as e:
            print(f"Error waiting for confirmation: {e}")
            # Proceed with original data if error receiving confirmation (or close)
        
        # 3. Matching Started
        await websocket.send_json({"status": "matching_started", "message": "Finding best matches..."})
        
        # Trigger matching via Celery
        task = match_cv_task.delay(data)
        
        # Wait for result (polling or blocking)
        # Since we are in an async WS handler, we can't block with .get() efficiently without blocking the event loop
        # But for this demo, let's use a simple loop with sleep
        while not task.ready():
            await asyncio.sleep(0.5)
            
        matches = task.get()
        
        # Log metric: Recommendation Count
        log_metric("recommendation_count", len(matches), {"cv_id": cv_id})
        
        await websocket.send_json({"status": "complete", "matches": matches})
        
    except Exception as e:
        await websocket.send_json({"status": "error", "message": str(e)})

class InteractionCreate(BaseModel):
    user_id: int
    job_id: str
    action: str

@router.post("/interact")
async def log_interaction(interaction: InteractionCreate, session: Session = Depends(get_session)):
    try:
        db_interaction = UserInteraction(
            user_id=interaction.user_id, 
            job_id=interaction.job_id, 
            action=interaction.action
        )
        session.add(db_interaction)
        session.commit()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/parse_sync")
async def parse_cv_sync(cv_id: str, session: Session = Depends(get_session)):
    # Find the file
    filename = f"{cv_id}.pdf"
    file_path = UPLOAD_DIR / filename
    
    if not file_path.exists():
         raise HTTPException(status_code=404, detail="CV file not found.")

    parser =RESUME_PARSER
    try:
        data = parser.parse(file_path)
        
        # Update CV record with parsed content
        # We need to find the CV by filename (which contains the ID)
        cv = session.exec(select(CV).where(CV.filename == filename)).first()
        if cv:
            cv.content = data
            # Generate embedding
            embeddings = get_embeddings()
            text_rep = ""
            if "basics" in data:
                text_rep += f"{data['basics'].get('name', '')} {data['basics'].get('summary', '')} "
            if "skills" in data:
                text_rep += " ".join([s.get("name", "") if isinstance(s, dict) else str(s) for s in data.get("skills", [])])
            
            cv.embedding = embeddings.embed_query(text_rep)
            
            session.add(cv)
            session.commit()
            
            # Cache embedding
            try:
                redis_client.set(f"cv_embedding:{cv_id}", np.array(cv.embedding).tobytes(), ttl=86400)
            except Exception as e:
                print(f"Failed to cache CV embedding: {e}")
            
        return data
    except Exception as e:
        print(f"Parsing error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Parsing failed: {str(e)}")
