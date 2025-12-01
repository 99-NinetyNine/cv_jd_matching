from core.worker.celery_app import celery_app
from core.matching.semantic_matcher import HybridMatcher
from core.db.engine import get_session
from core.db.models import Job
from sqlmodel import select, Session
import json
import numpy as np
from core.cache.redis_cache import redis_client

@celery_app.task
def perform_batch_matches():
    # TODO
    # @ using for each cv a batch requests
    pass


# for cvs
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

# for jobs
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

# for both CVs and Jobs status polling!
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
                    batch_req.status = remote_batch.status
                    
                elif remote_batch.status in ["failed", "expired", "cancelled"]:
                    batch_req.completed_at = datetime.utcnow()
                    batch_req.status = remote_batch.status
                    # TODO: Handle failed items
                    # it depends...
                session.add(batch_req)
                session.commit()
                # I think we may need to perform upsort bulk here
    except Exception as e:
        logger.error(f"Batch status check failed: {e}")
        return str(e)
