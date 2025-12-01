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


@celery_app.task
def process_pending_embeddings():
    """
    Background task to process CVs that were deferred (Smart Batching).
    Finds CVs with no embedding and computes them.
    """
    from core.db.engine import engine
    from core.db.models import CV
    from core.services.cv_service import compute_cv_embedding
    from core.matching.embeddings import EmbeddingFactory
    
    logger = celery_app.log.get_default_logger()
    
    try:
        with Session(engine) as session:
            # Find CVs with no embedding but with content
            # Note: checking for None embedding. 
            # In a real app, we might want a 'status' field on CV to distinguish 'failed' from 'pending'
            cvs = session.exec(select(CV).where(CV.embedding == None).where(CV.content != None).limit(10)).all()
            
            if not cvs:
                return "No pending embeddings"
                
            logger.info(f"Processing {len(cvs)} pending embeddings...")
            
            embedder = EmbeddingFactory.get_embedder()
            
            for cv in cvs:
                try:
                    # We need cv_id to use ID-based caching/logging
                    # Assuming filename is {cv_id}.pdf
                    cv_id = cv.filename.replace(".pdf", "")
                    
                    embedding = compute_cv_embedding(cv_id, cv.content, embedder)
                    cv.embedding = embedding
                    session.add(cv)
                    session.commit()
                    logger.info(f"Computed embedding for {cv.filename}")
                    
                except Exception as e:
                    logger.error(f"Failed to compute embedding for {cv.filename}: {e}")
                    
            return f"Processed {len(cvs)} CVs"
            
    except Exception as e:
        logger.error(f"Pending embedding task failed: {e}")
    except Exception as e:
        logger.error(f"Pending embedding task failed: {e}")
        return str(e)


@celery_app.task
def submit_batch_embeddings_task():
    """
    Collects CVs with embedding_status='pending_batch' and submits a batch job to OpenAI.
    """
    from core.db.engine import engine
    from core.db.models import CV, BatchRequest
    from core.services.batch_service import BatchService
    import os
    
    logger = celery_app.log.get_default_logger()
    batch_service = BatchService()
    
    if not batch_service.client:
        logger.warning("BatchService not available (OpenAI client missing). Skipping batch submission.")
        return
        
    try:
        with Session(engine) as session:
            # 1. Find pending batch CVs
            # Limit to 50000 or reasonable chunk
            cvs = session.exec(select(CV).where(CV.embedding_status == "pending_batch").limit(1000)).all()
            
            if not cvs:
                return "No pending batch CVs"
                
            logger.info(f"Found {len(cvs)} CVs for batch processing")
            
            # 2. Prepare requests
            requests = batch_service.prepare_embedding_requests(cvs)
            if not requests:
                logger.warning("No valid requests generated from CVs")
                return
                
            # 3. Create JSONL file
            timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            filename = f"batch_embeddings_{timestamp}.jsonl"
            file_path = f"/tmp/{filename}" # Use tmp for now
            
            batch_service.create_batch_file(requests, file_path)
            
            # 4. Upload file
            file_id = batch_service.upload_batch_file(file_path)
            logger.info(f"Uploaded batch file {file_id}")
            
            # 5. Create Batch
            batch_req = batch_service.create_batch(
                input_file_id=file_id, 
                endpoint="/v1/embeddings",
                metadata={"type": "embedding", "count": str(len(cvs))}
            )
            
            # 6. Save BatchRequest to DB
            session.add(batch_req)
            
            # 7. Update CV statuses
            for cv in cvs:
                cv.embedding_status = "processing"
                session.add(cv)
                
            session.commit()
            
            # Cleanup
            if os.path.exists(file_path):
                os.remove(file_path)
                
            return f"Submitted batch {batch_req.batch_api_id} with {len(cvs)} items"
            
    except Exception as e:
        logger.error(f"Batch submission failed: {e}")
        return str(e)


@celery_app.task
def submit_batch_job_embeddings_task():
    """
    Collects Jobs with embedding_status='pending_batch' and submits a batch job.
    """
    from core.db.engine import engine
    from core.db.models import Job, BatchRequest
    from core.services.batch_service import BatchService
    import os
    
    logger = celery_app.log.get_default_logger()
    batch_service = BatchService()
    
    if not batch_service.client:
        return
        
    try:
        with Session(engine) as session:
            jobs = session.exec(select(Job).where(Job.embedding_status == "pending_batch").limit(1000)).all()
            
            if not jobs:
                return "No pending batch Jobs"
                
            logger.info(f"Found {len(jobs)} Jobs for batch processing")
            
            requests = batch_service.prepare_job_embedding_requests(jobs)
            if not requests:
                return
                
            timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            filename = f"batch_jobs_{timestamp}.jsonl"
            file_path = f"/tmp/{filename}"
            
            batch_service.create_batch_file(requests, file_path)
            file_id = batch_service.upload_batch_file(file_path)
            
            batch_req = batch_service.create_batch(
                input_file_id=file_id, 
                endpoint="/v1/embeddings",
                metadata={"type": "job_embedding", "count": str(len(jobs))}
            )
            
            session.add(batch_req)
            for job in jobs:
                job.embedding_status = "processing"
                session.add(job)
            session.commit()
            
            if os.path.exists(file_path):
                os.remove(file_path)
                
            return f"Submitted job batch {batch_req.batch_api_id}"
            
    except Exception as e:
        logger.error(f"Job batch submission failed: {e}")
        return str(e)


@celery_app.task
def check_batch_status_task():
    """
    Checks status of active batch jobs and processes results.
    """
    from core.db.engine import engine
    from core.db.models import BatchRequest, CV, Job
    from core.services.batch_service import BatchService
    
    logger = celery_app.log.get_default_logger()
    batch_service = BatchService()
    
    if not batch_service.client:
        return
        
    try:
        with Session(engine) as session:
            # Find active batches
            active_statuses = ["validating", "in_progress", "finalizing"]
            batches = session.exec(select(BatchRequest).where(BatchRequest.status.in_(active_statuses))).all()
            
            for batch_req in batches:
                # Check status
                remote_batch = batch_service.retrieve_batch(batch_req.batch_api_id)
                
                # Update DB record
                batch_req.status = remote_batch.status
                batch_req.request_counts = remote_batch.request_counts
                batch_req.output_file_id = remote_batch.output_file_id
                batch_req.error_file_id = remote_batch.error_file_id
                
                if remote_batch.status == "completed" and batch_req.output_file_id:
                    # Process Results
                    logger.info(f"Processing results for batch {batch_req.batch_api_id}")
                    results = batch_service.retrieve_results(batch_req.output_file_id)
                    
                    for res in results:
                        custom_id = res.get("custom_id")
                        if not custom_id:
                            continue
                            
                        # Parse ID
                        if custom_id.startswith("cv-"):
                            cv_id = int(custom_id.replace("cv-", ""))
                            cv = session.get(CV, cv_id)
                            if cv:
                                try:
                                    embedding = res["response"]["body"]["data"][0]["embedding"]
                                    cv.embedding = embedding
                                    cv.embedding_status = "completed"
                                    cv.last_updated = datetime.utcnow()
                                    session.add(cv)
                                except Exception as e:
                                    logger.error(f"Failed to update CV {cv_id}: {e}")
                                    cv.embedding_status = "failed"
                                    session.add(cv)
                        
                        elif custom_id.startswith("job-"):
                            job_id = int(custom_id.replace("job-", ""))
                            job = session.get(Job, job_id)
                            if job:
                                try:
                                    embedding = res["response"]["body"]["data"][0]["embedding"]
                                    job.embedding = embedding
                                    job.embedding_status = "completed"
                                    session.add(job)
                                except Exception as e:
                                    logger.error(f"Failed to update Job {job_id}: {e}")
                                    job.embedding_status = "failed"
                                    session.add(job)
                                    
                    batch_req.completed_at = datetime.utcnow()
                    
                elif remote_batch.status in ["failed", "expired", "cancelled"]:
                    batch_req.completed_at = datetime.utcnow()
                    # TODO: Handle failed items
                    
                session.add(batch_req)
                session.commit()
                
    except Exception as e:
        logger.error(f"Batch status check failed: {e}")
        return str(e)
