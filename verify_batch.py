import sys
import os
sys.path.append(os.getcwd())

from core.db.engine import engine
from core.db.models import CV, BatchRequest
from sqlmodel import Session, select
from core.worker.tasks import submit_batch_embeddings_task
from unittest.mock import MagicMock, patch

def test_batch_flow():
    print("Testing Batch Flow...")
    
    with Session(engine) as session:
        # 1. Create a dummy pending CV
        cv = CV(filename="test_batch.pdf", content={"basics": {"name": "Test User"}}, embedding_status="pending_batch")
        session.add(cv)
        session.commit()
        session.refresh(cv)
        cv_id = cv.id
        print(f"Created pending CV: {cv_id}")
        
    # 2. Mock BatchService to avoid real OpenAI calls
    with patch("core.services.batch_service.BatchService") as MockService:
        service_instance = MockService.return_value
        service_instance.client = MagicMock()
        service_instance.prepare_embedding_requests.return_value = [{"custom_id": f"cv-{cv_id}", "body": {}}]
        service_instance.upload_batch_file.return_value = "file-mock-123"
        
        mock_batch = MagicMock()
        mock_batch.id = "batch_mock_123"
        mock_batch.input_file_id = "file-mock-123"
        mock_batch.status = "validating"
        mock_batch.created_at = 1234567890
        mock_batch.metadata = {}
        
        service_instance.create_batch.return_value = BatchRequest(
            batch_api_id="batch_mock_123",
            input_file_id="file-mock-123",
            status="validating",
            batch_metadata={}
        )
        
        # 3. Trigger Submission Task
        print("Triggering submission task...")
        result = submit_batch_embeddings_task()
        print(f"Task Result: {result}")
        
        # 4. Verify DB state
        with Session(engine) as session:
            cv = session.get(CV, cv_id)
            print(f"CV Status after submission: {cv.embedding_status}")
            
            batch = session.exec(select(BatchRequest).where(BatchRequest.batch_api_id == "batch_mock_123")).first()
            if batch:
                print(f"Batch created: {batch.batch_api_id}, Status: {batch.status}")
            else:
                print("Batch NOT found in DB")
                
    # Test Job Batching
    print("\nTesting Job Batch Flow...")
    from core.db.models import Job
    from core.worker.tasks import submit_batch_job_embeddings_task
    
    with Session(engine) as session:
        # Create pending job
        job = Job(
            job_id="job_batch_test",
            title="Batch Developer",
            company="Batch Co",
            description="Testing batch processing",
            embedding_status="pending_batch"
        )
        session.add(job)
        session.commit()
        job_id = job.id
        print(f"Created pending Job: {job_id}")
        
    with patch("core.services.batch_service.BatchService") as MockService:
        service_instance = MockService.return_value
        service_instance.client = MagicMock()
        service_instance.prepare_job_embedding_requests.return_value = [{"custom_id": f"job-{job_id}", "body": {}}]
        service_instance.upload_batch_file.return_value = "file-mock-job"
        
        mock_batch = MagicMock()
        mock_batch.id = "batch_mock_job"
        mock_batch.input_file_id = "file-mock-job"
        mock_batch.status = "validating"
        mock_batch.created_at = 1234567890
        mock_batch.metadata = {}
        
        service_instance.create_batch.return_value = BatchRequest(
            batch_api_id="batch_mock_job",
            input_file_id="file-mock-job",
            status="validating",
            batch_metadata={}
        )
        
        print("Triggering job submission task...")
        result = submit_batch_job_embeddings_task()
        print(f"Task Result: {result}")
        
        with Session(engine) as session:
            job = session.get(Job, job_id)
            print(f"Job Status after submission: {job.embedding_status}")

if __name__ == "__main__":
    test_batch_flow()
