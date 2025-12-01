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
        if "embedding" in cv_data and cv_data["embedding"] is not None and len(cv_data["embedding"]) > 0:
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
             # Convert to list if NumPy array
             if isinstance(cv_embedding, np.ndarray):
                 cv_embedding = cv_embedding.tolist()
             jobs = session.exec(select(Job).order_by(Job.embedding.cosine_distance(cv_embedding)).limit(50)).all()
        else:
             jobs = session.exec(select(Job)).limit(50).all()

        job_candidates = []
        for job in jobs:
            j_dict = job.dict()
            if job.embedding is not None and len(job.embedding) > 0:
                 j_dict["embedding"] = job.embedding
            else:
                cached_emb = redis_client.get(f"jd_embedding:{job.job_id}")
                if cached_emb:
                    j_dict["embedding"] = np.frombuffer(cached_emb, dtype=np.float64).tolist()
            job_candidates.append(j_dict)
            
        # 3. Match
        matches = matcher.match(cv_data, job_candidates)
        
        matches = matcher.match(cv_data, job_candidates)
        
        return matches


@celery_app.task
def process_batch_upload(batch_id: str, zip_path: str):
    """
    Process a batch upload of CVs (ZIP file).
    """
    import zipfile
    import shutil
    from pathlib import Path
    from datetime import datetime
    from core.db.engine import engine
    from core.db.models import BatchJob, CV
    from core.services.cv_service import get_or_parse_cv, compute_cv_embedding
    from core.matching.embeddings import EmbeddingFactory
    
    logger = celery_app.log.get_default_logger()
    
    extract_dir = Path(zip_path).parent / f"extract_{batch_id}"
    extract_dir.mkdir(exist_ok=True)
    
    processed_count = 0
    errors = []
    
    try:
        with Session(engine) as session:
            # 1. Update status to processing
            batch_job = session.exec(select(BatchJob).where(BatchJob.batch_id == batch_id)).first()
            if not batch_job:
                logger.error(f"BatchJob {batch_id} not found")
                return
            
            batch_job.status = "processing"
            session.add(batch_job)
            session.commit()
            
            # 2. Extract ZIP
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
                
            files = list(extract_dir.glob("**/*.pdf"))
            batch_job.total_items = len(files)
            session.add(batch_job)
            session.commit()
            
            # 3. Process each file
            embedder = EmbeddingFactory.get_embedder()
            
            for file_path in files:
                try:
                    # Parse
                    # We need a unique ID for each CV
                    import uuid
                    cv_id = str(uuid.uuid4())
                    
                    # Copy to uploads dir (simulating upload)
                    # In real system, might want to keep organized structure
                    uploads_dir = Path("uploads")
                    uploads_dir.mkdir(exist_ok=True)
                    new_filename = f"{cv_id}.pdf"
                    new_path = uploads_dir / new_filename
                    shutil.copy(file_path, new_path)
                    
                    # Create CV record
                    cv = CV(filename=new_filename, content={})
                    session.add(cv)
                    session.commit()
                    
                    # Parse content
                    data = get_or_parse_cv(cv_id, new_path, session)
                    
                    # Compute embedding
                    cv_embedding = compute_cv_embedding(cv_id, data, embedder)
                    
                    # Update CV
                    cv.embedding = cv_embedding
                    session.add(cv)
                    session.commit()
                    
                    processed_count += 1
                    
                    # Update progress every 5 items
                    if processed_count % 5 == 0:
                        batch_job.processed_items = processed_count
                        session.add(batch_job)
                        session.commit()
                        
                except Exception as e:
                    logger.error(f"Error processing {file_path.name}: {e}")
                    errors.append(f"{file_path.name}: {str(e)}")
            
            # 4. Complete
            batch_job.status = "completed"
            batch_job.processed_items = processed_count
            batch_job.completed_at = datetime.utcnow()
            batch_job.results = {"errors": errors}
            session.add(batch_job)
            session.commit()
            
    except Exception as e:
        logger.error(f"Batch processing failed: {e}")
        with Session(engine) as session:
             batch_job = session.exec(select(BatchJob).where(BatchJob.batch_id == batch_id)).first()
             if batch_job:
                 batch_job.status = "failed"
                 batch_job.error = str(e)
                 session.add(batch_job)
                 session.commit()
    finally:
        # Cleanup
        if extract_dir.exists():
            shutil.rmtree(extract_dir)
        if Path(zip_path).exists():
            Path(zip_path).unlink()
