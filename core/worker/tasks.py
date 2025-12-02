from core.worker.celery_app import celery_app
from core.matching.semantic_matcher import HybridMatcher
from core.db.engine import get_session
from core.db.models import Job
from sqlmodel import select, Session
import json
import numpy as np
from core.cache.redis_cache import redis_client
from datetime import datetime
import os
import logging

logger = logging.getLogger(__name__)


# TEST TASK - To verify Celery is working
@celery_app.task
def test_celery_task(message: str = "Hello from Celery!"):
    """
    Simple test task to verify Celery worker is running.
    Run with: test_celery_task.delay("Your message")
    """
    logger.info(f"TEST TASK EXECUTED: {message}")
    return {
        "status": "success",
        "message": message,
        "timestamp": datetime.utcnow().isoformat()
    }


# BATCH CV PARSING TASK
@celery_app.task
def process_batch_cv_parsing():
    """
    Process CVs with parsing_status='pending_batch' using efficient batch parsing.

    Flow:
    1. Find pending CVs
    2. Extract text from all PDFs in parallel (fast, local)
    3. Submit batch to OpenAI for structured parsing
    4. Results are processed by check_batch_status_task() when ready
    """
    from core.db.engine import engine
    from core.parsing.batch_parser import BatchCVParser
    from pathlib import Path

    logger.info("Starting batch CV parsing task...")

    try:
        with Session(engine) as session:
            # Count pending CVs
            from sqlalchemy import func
            pending_count = session.exec(
                select(func.count(CV.id)).where(CV.parsing_status == "pending_batch")
            ).one()

            if pending_count == 0:
                logger.info("No CVs pending batch parsing")
                return "No CVs to process"

            # Dynamic batch sizing based on queue depth and system resources
            from core.parsing.batch_sizing import get_batch_size_for_task
            batch_size = get_batch_size_for_task(pending_count, "cv_parsing")

            logger.info(f"Dynamic batch size: {batch_size} (total pending: {pending_count})")

            # Find CVs pending batch parsing
            cvs_to_parse = session.exec(
                select(CV).where(CV.parsing_status == "pending_batch").limit(batch_size)
            ).all()

            logger.info(f"Processing {len(cvs_to_parse)} CVs in this batch")

            # Use new batch parser with parallel text extraction
            batch_parser = BatchCVParser(max_workers=10)
            batch_request = batch_parser.submit_batch_parsing_job(
                cv_records=cvs_to_parse,
                session=session,
                uploads_dir=Path("uploads")
            )

            if batch_request:
                result = f"Submitted batch parsing job {batch_request.batch_api_id} with {len(cvs_to_parse)} CVs"
                logger.info(result)
                return result
            else:
                return "Failed to submit batch parsing job"

    except Exception as e:
        logger.error(f"Batch parsing task failed: {e}")
        return f"Error: {str(e)}"


# Commented out to prevent auto-execution during development
# @celery_app.task
def perform_batch_matches():
    """
    Periodically check for CVs that need fresh matches and process them in batch.
    1. Find CVs with no predictions or old predictions (> 7 days).
    2. Perform vector search for each.
    3. Save predictions (without explanations).
    4. Queue explanations for batch processing.
    """
    from core.db.engine import engine
    from core.db.models import CV, Prediction, BatchRequest
    from core.services.batch_service import BatchService
    from core.services.job_service import get_job_text_representation
    from core.services.cv_service import get_cv_text_representation
    import uuid
    
    logger = celery_app.log.get_default_logger()
    batch_service = BatchService()
    
    try:
        with Session(engine) as session:
            # 1. Find target CVs
            # Filter by:
            # - embedding_status = 'completed'
            # - is_latest = True (only process the latest CV for each user)
            # - last_analyzed is NULL OR older than 6 hours
            
            from datetime import timedelta
            cutoff_time = datetime.utcnow() - timedelta(hours=6)
            
            cvs = session.exec(
                select(CV).where(
                    CV.embedding_status == "completed",
                    CV.is_latest == True,
                    (CV.last_analyzed == None) | (CV.last_analyzed < cutoff_time)
                )
            ).all()
            
            target_cv_ids = [cv.id for cv in cvs]
                        
            if not target_cv_ids:
                return "No CVs need matching"
                
            logger.info(f"Found {len(target_cv_ids)} CVs for batch matching")
            
            # 2. Perform Batch Vector Search using CROSS JOIN LATERAL
            # This is much more efficient than looping
            from sqlalchemy import text
            
            # Ensure we have a list of IDs for the query
            cv_ids_str = ",".join([str(id) for id in target_cv_ids])
            
            query = text(f"""
                SELECT
                    c.id as cv_id,
                    j.job_id as job_id,
                    j.data as job_data,
                    j.canonical_text as job_text,
                    1 - (c.embedding <=> j.embedding) as similarity
                FROM cv c
                CROSS JOIN LATERAL (
                    SELECT id as job_id, data, canonical_text, embedding
                    FROM job j
                    WHERE j.embedding_status = 'completed'
                    ORDER BY j.embedding <=> c.embedding
                    LIMIT 10
                ) j
                WHERE c.id IN ({cv_ids_str})
                AND c.embedding_status = 'completed'
            """)
            
            results = session.exec(query).all()
            
            # Group results by cv_id
            matches_by_cv = {}
            for row in results:
                cv_id = str(row.cv_id)
                if cv_id not in matches_by_cv:
                    matches_by_cv[cv_id] = []

                matches_by_cv[cv_id].append({
                    "job_id": row.job_id,
                    "data": row.job_data,
                    "job_text": row.job_text,  # Use pre-computed canonical_text
                    "similarity": float(row.similarity)
                })
            
            explanation_requests = []
            
            for cv_id, matches in matches_by_cv.items():
                # Get CV content for prompt
                # We need to fetch it again or cache it. fetching for now.
                cv = session.get(CV, int(cv_id))
                if not cv: continue
                
                # 3. Save Predictions (Initial)
                prediction_id = str(uuid.uuid4())
                
                # Prepare matches with empty explanations
                final_matches = []
                for m in matches:
                    m["explanation"] = None # Pending
                    final_matches.append(m)

                    # Prepare explanation request
                    cv_text =  get_cv_text_representation(cv.content)
                    job_text = m["job_text"]  # Use pre-computed canonical_text
                    
                    req_id = f"pred-{prediction_id}-job-{m['job_id']}"
                    
                    # Construct prompt (simplified)
                    prompt = f"Explain why this candidate is a good match for the job.\nCandidate: {cv_text[:500]}\nJob: {job_text[:500]}\nMatch Score: {m['similarity']:.2f}"
                    
                    explanation_requests.append({
                        "custom_id": req_id,
                        "method": "POST",
                        "url": "/v1/chat/completions",
                        "body": {
                            "model": "gpt-3.5-turbo",
                            "messages": [{"role": "user", "content": prompt}],
                            "max_tokens": 150
                        }
                    })
                
                prediction = Prediction(
                    prediction_id=prediction_id,
                    cv_id=str(cv.id),
                    matches=final_matches
                )
                session.add(prediction)
                
                # Update last_analyzed timestamp
                cv.last_analyzed = datetime.utcnow()
                session.add(cv)
            
            session.commit()
            
            # 4. Submit Batch for Explanations
            if explanation_requests:
                # ... Batch submission logic similar to embeddings ...
                # Use BatchService
                timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
                filename = f"batch_explanations_{timestamp}.jsonl"
                file_path = f"/tmp/{filename}"
                
                batch_service.create_batch_file(explanation_requests, file_path)
                file_id = batch_service.upload_batch_file(file_path)
                
                batch_req = batch_service.create_batch(
                    input_file_id=file_id,
                    endpoint="/v1/chat/completions",
                    metadata={"type": "explanation", "count": str(len(explanation_requests))}
                )
                session.add(batch_req)
                session.commit()
                
                if os.path.exists(file_path):
                    os.remove(file_path)
                    
                return f"Submitted explanation batch {batch_req.batch_api_id} with {len(explanation_requests)} items"
                
    except Exception as e:
        logger.error(f"Batch matching failed: {e}")
        return str(e)


# Commented out to prevent auto-execution during development
# for cvs
# @celery_app.task
def submit_cv_batch_embeddings_task():
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

# Commented out to prevent auto-execution during development
# for jobs
# @celery_app.task
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

# Commented out to prevent auto-execution during development
# for both CVs and Jobs status polling!
# @celery_app.task
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
                
                if remote_batch.status == "completed":
                    if batch_req.batch_metadata.get("type") == "embedding":
                        # Handle Embedding Results
                        results = batch_service.retrieve_results(remote_batch.output_file_id)
                        
                        for res in results:
                            custom_id = res.get("custom_id")
                            if not custom_id: continue
                            
                            if custom_id.startswith("cv-"):
                                cv_id = int(custom_id.replace("cv-", ""))
                                cv = session.get(CV, cv_id)
                                if cv:
                                    try:
                                        embedding = res["response"]["body"]["data"][0]["embedding"]
                                        cv.embedding = embedding
                                        cv.embedding_status = "completed"
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

                    elif batch_req.batch_metadata.get("type") == "cv_parsing":
                        # Handle CV Parsing Results
                        logger.info(f"Processing CV parsing results for batch {batch_req.batch_api_id}")
                        from core.parsing.batch_parser import BatchCVParser

                        batch_parser = BatchCVParser()
                        stats = batch_parser.process_parsing_results(batch_req, session)
                        logger.info(f"CV parsing stats: {stats}")

                    elif batch_req.batch_metadata.get("type") == "explanation_simple":
                        # Handle Simple Explanation Results (ONE sentence!)
                        logger.info(f"Processing simple explanation results for batch {batch_req.batch_api_id}")
                        from core.matching.batch_explainer import SimpleBatchExplainer

                        explainer = SimpleBatchExplainer()
                        stats = explainer.process_explanation_results(batch_req, session)
                        logger.info(f"Simple explanation stats: {stats}")

                    elif batch_req.batch_metadata.get("type") == "explanation":
                         # Handle Explanation Results
                         logger.info(f"Processing explanation results for batch {batch_req.batch_api_id}")
                         results = batch_service.retrieve_results(remote_batch.output_file_id)
                         
                         # Group by prediction_id
                         updates = {} # prediction_id -> {job_id: explanation}
                         
                         for res in results:
                             custom_id = res.get("custom_id")
                             if not custom_id: continue
                             
                             try:
                                 # custom_id format: pred-{prediction_id}-job-{job_id}
                                 parts = custom_id.split("-job-")
                                 if len(parts) != 2: continue
                                 
                                 pred_part = parts[0].replace("pred-", "")
                                 job_id = parts[1]
                                 
                                 explanation = res["response"]["body"]["choices"][0]["message"]["content"]
                                 
                                 if pred_part not in updates:
                                     updates[pred_part] = {}
                                 updates[pred_part][job_id] = explanation
                             except Exception as e:
                                 logger.error(f"Failed to parse explanation result {custom_id}: {e}")
                                 
                         # Update Predictions
                         for pred_id, job_explanations in updates.items():
                             prediction = session.exec(select(Prediction).where(Prediction.prediction_id == pred_id)).first()
                             if prediction:
                                 # Update matches
                                 new_matches = []
                                 for m in prediction.matches:
                                     if m["job_id"] in job_explanations:
                                         m["explanation"] = job_explanations[m["job_id"]]
                                     new_matches.append(m)
                                 
                                 # Force update
                                 prediction.matches = list(new_matches) 
                                 session.add(prediction)

                    batch_req.completed_at = datetime.utcnow()
                    batch_req.status = remote_batch.status
                    batch_req.output_file_id = remote_batch.output_file_id
                    
                elif remote_batch.status in ["failed", "expired", "cancelled"]:
                    batch_req.completed_at = datetime.utcnow()
                    batch_req.status = remote_batch.status
                    # TODO: Handle failed items
                    # it depends...
                session.add(batch_req)
                session.commit()
                
    except Exception as e:
        logger.error(f"Batch status check failed: {e}")
        return str(e)
