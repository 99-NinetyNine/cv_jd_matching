from core.worker.celery_app import celery_app
from core.matching.semantic_matcher import HybridMatcher
from core.db.engine import get_session
from core.db.models import Job, CV, Prediction
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
#@celery_app.task
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
            # EXCLUDE failed/cancelled items (for data analyst review)
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
            # Note: Items with status='failed' are excluded (require manual review)
            cvs_to_parse = session.exec(
                select(CV)
                .where(CV.parsing_status == "pending_batch")
                .order_by(CV.created_at)  # Process oldest first
                .limit(batch_size)
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

    SCALABILITY: Uses dynamic batch sizing to prevent memory exhaustion.

    Uses BatchMatcher class for optimized batch matching:
    - Parameterized pgvector queries
    - Pre-computed canonical text
    - Bulk database operations
    - Batch explanation generation
    - Dynamic batch sizing based on queue depth and system resources

    Flow:
    1. Count pending CVs and calculate optimal batch size
    2. Find CVs with no predictions or old predictions (> 6 hours) - LIMIT to batch size
    3. Perform batch vector search using CROSS JOIN LATERAL
    4. Save predictions in bulk (without explanations)
    5. Queue explanations for batch processing
    """
    from core.db.engine import engine
    from core.matching.batch_matcher import BatchMatcher
    from sqlalchemy import func

    logger = celery_app.log.get_default_logger()

    try:
        with Session(engine) as session:
            # SCALABILITY: Count pending CVs first
            from datetime import timedelta
            cutoff_time = datetime.utcnow() - timedelta(hours=6)

            pending_count = session.exec(
                select(func.count(CV.id)).where(
                    CV.embedding_status == "completed",
                    CV.is_latest == True,
                    (CV.last_analyzed == None) | (CV.last_analyzed < cutoff_time)
                )
            ).one()

            if pending_count == 0:
                logger.info("No CVs need matching")
                return "No CVs need matching"

            # SCALABILITY: Calculate dynamic batch size
            from core.parsing.batch_sizing import get_batch_size_for_task
            batch_size = get_batch_size_for_task(pending_count, "matching")

            logger.info(f"Dynamic batch size: {batch_size} (total pending: {pending_count})")

            # Process batch with limit
            batch_matcher = BatchMatcher()
            result = batch_matcher.process_batch_matches(
                session=session,
                cutoff_hours=6,
                top_k=10,
                batch_size=batch_size  # Pass dynamic batch size
            )
            return result

    except Exception as e:
        logger.error(f"Batch matching failed: {e}")
        return str(e)


# Commented out to prevent auto-execution during development
# for cvs
# @celery_app.task
def submit_cv_batch_embeddings_task():
    """
    Collects CVs with embedding_status='pending_batch' and submits a batch job to OpenAI.

    SCALABILITY: Uses dynamic batch sizing to prevent memory exhaustion.
    """
    from core.db.engine import engine
    from core.db.models import CV, BatchRequest
    from core.services.batch_service import BatchService
    from sqlalchemy import func
    import os

    logger = celery_app.log.get_default_logger()
    batch_service = BatchService()

    if not batch_service.client:
        logger.warning("BatchService not available (OpenAI client missing). Skipping batch submission.")
        return

    try:
        with Session(engine) as session:
            # SCALABILITY: Count pending CVs first
            # EXCLUDE failed/cancelled items (for data analyst review)
            pending_count = session.exec(
                select(func.count(CV.id)).where(CV.embedding_status == "pending_batch")
            ).one()

            if pending_count == 0:
                return "No pending batch CVs"

            # SCALABILITY: Calculate dynamic batch size
            from core.parsing.batch_sizing import get_batch_size_for_task
            batch_size = get_batch_size_for_task(pending_count, "embedding")

            logger.info(f"CV embedding batch size: {batch_size} (total pending: {pending_count})")

            # Find pending batch CVs with LIMIT
            # Note: Items with status='failed' are excluded (require manual review)
            cvs = session.exec(
                select(CV)
                .where(CV.embedding_status == "pending_batch")
                .order_by(CV.created_at)  # Process oldest first
                .limit(batch_size)
            ).all()
            
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

    SCALABILITY: Uses dynamic batch sizing to prevent memory exhaustion.
    """
    from core.db.engine import engine
    from core.db.models import Job, BatchRequest
    from core.services.batch_service import BatchService
    from sqlalchemy import func
    import os

    logger = celery_app.log.get_default_logger()
    batch_service = BatchService()

    if not batch_service.client:
        return

    try:
        with Session(engine) as session:
            # SCALABILITY: Count pending jobs first
            # EXCLUDE failed/cancelled items (for data analyst review)
            pending_count = session.exec(
                select(func.count(Job.id)).where(Job.embedding_status == "pending_batch")
            ).one()

            if pending_count == 0:
                return "No pending batch Jobs"

            # SCALABILITY: Calculate dynamic batch size
            from core.parsing.batch_sizing import get_batch_size_for_task
            batch_size = get_batch_size_for_task(pending_count, "embedding")

            logger.info(f"Job embedding batch size: {batch_size} (total pending: {pending_count})")

            # Find pending batch jobs with LIMIT
            # Note: Items with status='failed' are excluded (require manual review)
            jobs = session.exec(
                select(Job)
                .where(Job.embedding_status == "pending_batch")
                .order_by(Job.created_at)  # Process oldest first
                .limit(batch_size)
            ).all()
            
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

def _handle_batch_errors(batch_req, error_file_id, session, batch_service):
    """
    Handle error file from batch: mark individual failed items.

    Error file format:
    {"id": "batch_req_123", "custom_id": "cv-456", "response": null, "error": {"code": "...", "message": "..."}}
    """
    try:
        errors = batch_service.retrieve_results(error_file_id)
        batch_type = batch_req.batch_metadata.get("type")

        for error_entry in errors:
            custom_id = error_entry.get("custom_id")
            if not custom_id:
                continue

            error_msg = error_entry.get("error", {}).get("message", "Unknown error")
            logger.warning(f"Batch error for {custom_id}: {error_msg}")

            # Mark item as failed based on type
            if batch_type == "embedding":
                if custom_id.startswith("cv-"):
                    cv_id = int(custom_id.replace("cv-", ""))
                    cv = session.get(CV, cv_id)
                    if cv:
                        cv.embedding_status = "failed"
                        session.add(cv)

                elif custom_id.startswith("job-"):
                    job_id = int(custom_id.replace("job-", ""))
                    job = session.get(Job, job_id)
                    if job:
                        job.embedding_status = "failed"
                        session.add(job)

            elif batch_type == "cv_parsing":
                if custom_id.startswith("cv-parse-"):
                    cv_id = int(custom_id.replace("cv-parse-", ""))
                    cv = session.get(CV, cv_id)
                    if cv:
                        cv.parsing_status = "failed"
                        session.add(cv)

        logger.info(f"Processed {len(errors)} errors from batch {batch_req.batch_api_id}")

    except Exception as e:
        logger.error(f"Failed to process error file: {e}")


# Commented out to prevent auto-execution during development
# for both CVs and Jobs status polling!
# @celery_app.task
def check_batch_status_task():
    """
    Checks status of active batch jobs and processes results.

    SCALABILITY: Limits number of batches checked per run to prevent overload.
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
            # SCALABILITY: Limit number of batches to check per run
            # Process oldest first (FIFO), limit to 50 to prevent API rate limits and timeouts
            active_statuses = ["validating", "in_progress", "finalizing"]
            batches = session.exec(
                select(BatchRequest)
                .where(BatchRequest.status.in_(active_statuses))
                .order_by(BatchRequest.created_at)  # Oldest first
                .limit(50)  # Prevent checking too many at once
            ).all()

            if not batches:
                logger.info("No active batches to check")
                return "No active batches"

            logger.info(f"Checking status of {len(batches)} active batches")
            
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

                    # HANDLE ERROR FILE: Process failed requests within successful batch
                    if remote_batch.error_file_id:
                        logger.warning(f"Batch {batch_req.batch_api_id} has errors. Processing error file...")
                        _handle_batch_errors(batch_req, remote_batch.error_file_id, session, batch_service)

                elif remote_batch.status in ["failed", "expired", "cancelled"]:
                    batch_req.completed_at = datetime.utcnow()
                    batch_req.status = remote_batch.status

                    # Mark all items in this batch as failed for data analyst review
                    logger.error(f"Batch {batch_req.batch_api_id} {remote_batch.status}. Marking items as failed.")

                    # Based on batch type, mark items as failed
                    batch_type = batch_req.batch_metadata.get("type")

                    if batch_type == "embedding":
                        # Read input file to get all CV/Job IDs
                        if batch_req.input_file_id:
                            try:
                                file_content = batch_service.retrieve_results(batch_req.input_file_id)
                                for line in file_content:
                                    custom_id = line.get("custom_id")
                                    if not custom_id:
                                        continue

                                    if custom_id.startswith("cv-"):
                                        cv_id = int(custom_id.replace("cv-", ""))
                                        cv = session.get(CV, cv_id)
                                        if cv:
                                            cv.embedding_status = "failed"
                                            session.add(cv)

                                    elif custom_id.startswith("job-"):
                                        job_id = int(custom_id.replace("job-", ""))
                                        job = session.get(Job, job_id)
                                        if job:
                                            job.embedding_status = "failed"
                                            session.add(job)
                            except Exception as e:
                                logger.error(f"Failed to process failed batch items: {e}")

                    elif batch_type == "cv_parsing":
                        # Mark CVs as failed for manual review
                        # Parse custom_ids from input file
                        try:
                            file_content = batch_service.retrieve_results(batch_req.input_file_id)
                            for line in file_content:
                                custom_id = line.get("custom_id")
                                if custom_id and custom_id.startswith("cv-parse-"):
                                    cv_id = int(custom_id.replace("cv-parse-", ""))
                                    cv = session.get(CV, cv_id)
                                    if cv:
                                        cv.parsing_status = "failed"
                                        session.add(cv)
                        except Exception as e:
                            logger.error(f"Failed to mark CVs as failed: {e}")

                    # Note: For failed/cancelled/expired batches, items are marked as "failed"
                    # and require manual review by data analysts. They are NOT retried automatically.

                session.add(batch_req)
                session.commit()
                
    except Exception as e:
        logger.error(f"Batch status check failed: {e}")
        return str(e)
