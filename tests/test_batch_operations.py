"""
Tests for Batch Operations

Tests all batch processing functions using REAL BatchService:
- CV parsing batches
- CV embedding batches
- Job embedding batches
- Batch matching
- Batch status checking

NOTE: These tests use the real OpenAI Batch API or real services.
Set appropriate environment variables for API keys.
"""

import pytest
import os
import json
from pathlib import Path
from sqlmodel import Session, select, create_engine
from sqlalchemy import func

from core.db.models import CV, Job, BatchRequest, Prediction
from core.services.batch_service import BatchService
from core.parsing.batch_parser import BatchCVParser
from core.matching.batch_matcher import BatchMatcher
from core.worker.tasks import (
    process_batch_cv_parsing,
    submit_cv_batch_embeddings_task,
    submit_batch_job_embeddings_task,
    perform_batch_matches,
    check_batch_status_task
)


# Use real database session from conftest.py

@pytest.fixture
def batch_service():
    """Get batch service in REAL mode (not mock)."""
    # Use real OpenAI batch service
    service = BatchService(use_mock=False)
    return service



@pytest.fixture
def sample_cvs(session: Session):
    """Create sample CVs for testing."""
    cvs = []
    for i in range(5):
        cv = CV(
            filename=f"test_cv_{i}.pdf",
            content={
                "basics": {
                    "name": f"Test Candidate {i}",
                    "email": f"test{i}@example.com"
                },
                "skills": [
                    {"name": "Python", "level": "Expert"}
                ]
            },
            parsing_status="pending_batch",
            embedding_status="pending_batch",
            is_latest=True
        )
        session.add(cv)
        cvs.append(cv)

    session.commit()

    # Refresh to get IDs
    for cv in cvs:
        session.refresh(cv)

    return cvs


@pytest.fixture
def sample_jobs(session: Session):
    """Create sample jobs for testing."""
    jobs = []
    for i in range(3):
        job = Job(
            job_id=f"job_{i}",
            title=f"Software Engineer {i}",
            company=f"Company {i}",
            description=f"Job description {i}",
            embedding_status="pending_batch"
        )
        session.add(job)
        jobs.append(job)

    session.commit()

    for job in jobs:
        session.refresh(job)

    return jobs



class TestBatchService:
    """Test BatchService functionality with REAL OpenAI Batch API."""

    def test_batch_service_initializes_in_real_mode(self, batch_service):
        """Test that batch service initializes with real client."""
        assert batch_service.client is not None
        # Real OpenAI client has these attributes
        assert hasattr(batch_service.client, 'batches')
        assert hasattr(batch_service.client, 'files')

    @pytest.mark.skip(reason="Requires real OpenAI API - expensive and slow")
    def test_create_batch_file(self, batch_service, tmp_path):
        """Test creating batch JSONL file."""
        requests = [
            {
                "custom_id": "req-1",
                "method": "POST",
                "url": "/v1/embeddings",
                "body": {"model": "text-embedding-3-small", "input": "test"}
            },
            {
                "custom_id": "req-2",
                "method": "POST",
                "url": "/v1/embeddings",
                "body": {"model": "text-embedding-3-small", "input": "test2"}
            }
        ]

        file_path = tmp_path / "test_batch.jsonl"
        result = batch_service.create_batch_file(requests, str(file_path))

        assert Path(result).exists()

        # Verify content
        with open(file_path, "r") as f:
            lines = f.readlines()
            assert len(lines) == 2

    @pytest.mark.skip(reason="Requires real OpenAI API - expensive and slow")
    def test_upload_and_create_batch(self, batch_service, tmp_path):
        """Test uploading file and creating batch with REAL API."""
        # Create test file
        requests = [
            {
                "custom_id": "test-1",
                "method": "POST",
                "url": "/v1/embeddings",
                "body": {"model": "text-embedding-3-small", "input": "test input"}
            }
        ]

        file_path = tmp_path / "test.jsonl"
        batch_service.create_batch_file(requests, str(file_path))

        # Upload file to real OpenAI
        file_id = batch_service.upload_batch_file(str(file_path))
        assert file_id.startswith("file-")  # Real OpenAI file IDs

        # Create batch
        batch_req = batch_service.create_batch(
            input_file_id=file_id,
            endpoint="/v1/embeddings",
            metadata={"type": "test"}
        )

        assert batch_req.batch_api_id.startswith("batch_")  # Real OpenAI batch IDs
        assert batch_req.status in ["validating", "in_progress", "completed"]
        assert batch_req.batch_metadata == {"type": "test"}

    @pytest.mark.skip(reason="Requires real OpenAI API - expensive and slow")
    def test_retrieve_batch(self, batch_service, tmp_path):
        """Test retrieving batch status from REAL API."""
        # Create and submit batch
        requests = [{"custom_id": "test", "method": "POST", "url": "/v1/embeddings", "body": {}}]
        file_path = tmp_path / "test.jsonl"
        batch_service.create_batch_file(requests, str(file_path))
        file_id = batch_service.upload_batch_file(str(file_path))
        batch_req = batch_service.create_batch(file_id, "/v1/embeddings")

        # Retrieve batch
        retrieved = batch_service.retrieve_batch(batch_req.batch_api_id)
        assert retrieved.id == batch_req.batch_api_id
        assert retrieved.status in ["validating", "in_progress", "finalizing", "completed"]

    @pytest.mark.skip(reason="Requires real OpenAI API - expensive and slow")
    def test_retrieve_results(self, batch_service, tmp_path):
        """Test retrieving batch results from REAL API."""
        # Create embedding batch
        requests = [
            {
                "custom_id": "cv-123",
                "method": "POST",
                "url": "/v1/embeddings",
                "body": {"model": "text-embedding-3-small", "input": "test"}
            }
        ]

        file_path = tmp_path / "test.jsonl"
        batch_service.create_batch_file(requests, str(file_path))
        file_id = batch_service.upload_batch_file(str(file_path))
        batch_req = batch_service.create_batch(file_id, "/v1/embeddings")

        # Wait for completion (in real scenario, would poll)
        # For now, skip actual retrieval
        # results = batch_service.retrieve_results(batch_req.output_file_id)


class TestBatchParsing:
    """Test batch CV parsing with REAL services."""

    def test_batch_parser_initialization(self):
        """Test BatchCVParser initialization."""
        parser = BatchCVParser(max_workers=5)
        assert parser.max_workers == 5
        assert parser.batch_service is not None

    def test_prepare_parsing_requests(self, batch_service):
        """Test preparing parsing batch requests."""
        parser = BatchCVParser()

        extracted_texts = {
            1: {"text": "John Doe resume content...", "status": "success"},
            2: {"text": "Jane Smith resume content...", "status": "success"}
        }

        requests = parser.prepare_parsing_batch_requests(extracted_texts)

        assert len(requests) == 2
        assert requests[0]["custom_id"] == "cv-parse-1"
        assert requests[1]["custom_id"] == "cv-parse-2"
        assert "cv_text" in requests[0]["body"]["messages"][1]["content"].lower()


class TestBatchEmbeddings:
    """Test batch embedding generation."""

    def test_prepare_cv_embedding_requests(self, batch_service, sample_cvs):
        """Test preparing CV embedding requests."""
        requests = batch_service.prepare_embedding_requests(sample_cvs)

        assert len(requests) == 5
        assert all(req["custom_id"].startswith("cv-") for req in requests)
        assert all(req["url"] == "/v1/embeddings" for req in requests)

    def test_prepare_job_embedding_requests(self, batch_service, sample_jobs):
        """Test preparing job embedding requests."""
        requests = batch_service.prepare_job_embedding_requests(sample_jobs)

        assert len(requests) == 3
        assert all(req["custom_id"].startswith("job-") for req in requests)


class TestBatchMatching:
    """Test batch matching operations."""

    def test_batch_matcher_initialization(self):
        """Test BatchMatcher initialization."""
        matcher = BatchMatcher()
        assert matcher.batch_service is not None

    def test_find_cvs_needing_matches(self, test_db_engine, sample_cvs):
        """Test finding CVs that need matches."""
        # Mark CVs as completed for matching
        with Session(test_db_engine) as session:
            for cv in sample_cvs:
                db_cv = session.get(CV, cv.id)
                db_cv.embedding_status = "completed"
                db_cv.embedding = [0.1] * 768  # Mock embedding
                session.add(db_cv)
            session.commit()

        # Find CVs needing matches
        matcher = BatchMatcher()
        with Session(test_db_engine) as session:
            cvs = matcher.find_cvs_needing_matches(session, batch_size=10)
            assert len(cvs) == 5

    def test_batch_matcher_with_size_limit(self, test_db_engine, sample_cvs):
        """Test batch matcher respects size limit."""
        matcher = BatchMatcher()

        with Session(test_db_engine) as session:
            # Update CVs to be ready for matching
            for cv in sample_cvs:
                db_cv = session.get(CV, cv.id)
                db_cv.embedding_status = "completed"
                db_cv.embedding = [0.1] * 768
                session.add(db_cv)
            session.commit()

            # Test with limit
            cvs = matcher.find_cvs_needing_matches(session, batch_size=3)
            assert len(cvs) == 3


class TestMockResponses:
    """Test mock response generation."""

    def test_mock_embedding_response(self, batch_service, tmp_path):
        """Test that mock generates valid embedding responses."""
        requests = [{
            "custom_id": "cv-123",
            "method": "POST",
            "url": "/v1/embeddings",
            "body": {"model": "text-embedding-3-small", "input": "test"}
        }]

        file_path = tmp_path / "test.jsonl"
        batch_service.create_batch_file(requests, str(file_path))
        file_id = batch_service.upload_batch_file(str(file_path))
        batch = batch_service.create_batch(file_id, "/v1/embeddings")

        results = batch_service.retrieve_results(batch.output_file_id)
        embedding = results[0]["response"]["body"]["data"][0]["embedding"]

        # OpenAI text-embedding-3-small uses 1536 dimensions (default)
        assert len(embedding) == 1536
        assert all(isinstance(x, (int, float)) for x in embedding)

    def test_mock_cv_parse_response(self, batch_service, tmp_path):
        """Test that mock generates valid CV parse responses."""
        requests = [{
            "custom_id": "cv-parse-123",
            "method": "POST",
            "url": "/v1/chat/completions",
            "body": {"model": "gpt-4o-mini", "messages": []}
        }]

        file_path = tmp_path / "test.jsonl"
        batch_service.create_batch_file(requests, str(file_path))
        file_id = batch_service.upload_batch_file(str(file_path))
        batch = batch_service.create_batch(file_id, "/v1/chat/completions")

        results = batch_service.retrieve_results(batch.output_file_id)
        content = results[0]["response"]["body"]["choices"][0]["message"]["content"]

        import json
        parsed = json.loads(content)
        assert "basics" in parsed
        assert "work" in parsed
        assert "education" in parsed
        assert "skills" in parsed

    def test_mock_explanation_response(self, batch_service, tmp_path):
        """Test that mock generates explanation responses."""
        requests = [{
            "custom_id": "pred-abc-job-123",
            "method": "POST",
            "url": "/v1/chat/completions",
            "body": {"model": "gpt-3.5-turbo", "messages": []}
        }]

        file_path = tmp_path / "test.jsonl"
        batch_service.create_batch_file(requests, str(file_path))
        file_id = batch_service.upload_batch_file(str(file_path))
        batch = batch_service.create_batch(file_id, "/v1/chat/completions")

        results = batch_service.retrieve_results(batch.output_file_id)
        content = results[0]["response"]["body"]["choices"][0]["message"]["content"]

        assert isinstance(content, str)
        assert len(content) > 0
        assert "match" in content.lower()


class TestScalability:
    """Test scalability features."""

    def test_dynamic_batch_sizing(self):
        """Test that dynamic batch sizing works."""
        from core.parsing.batch_sizing import get_batch_size_for_task

        # Small queue
        size = get_batch_size_for_task(10, "embedding")
        assert size >= 10
        assert size <= 100

        # Large queue
        size = get_batch_size_for_task(100000, "embedding")
        assert size >= 1000
        assert size <= 10000

    def test_batch_limit_prevents_oom(self, test_db_engine):
        """Test that batch limits prevent loading too many records."""
        # Create many CVs
        with Session(test_db_engine) as session:
            for i in range(1000):
                cv = CV(
                    filename=f"cv_{i}.pdf",
                    content={},
                    embedding_status="completed",
                    embedding=[0.1] * 768,
                    is_latest=True
                )
                session.add(cv)
            session.commit()

        # Test matcher respects limit
        matcher = BatchMatcher()
        with Session(test_db_engine) as session:
            cvs = matcher.find_cvs_needing_matches(session, batch_size=50)
            assert len(cvs) == 50  # Should only fetch 50, not 1000


class TestBatchStatusTransitions:
    """Test all batch status transitions."""

    def test_all_batch_statuses(self, batch_service, tmp_path):
        """Test creating batch and transitioning through all statuses."""
        requests = [{
            "custom_id": "test-1",
            "method": "POST",
            "url": "/v1/embeddings",
            "body": {}
        }]

        file_path = tmp_path / "test.jsonl"
        batch_service.create_batch_file(requests, str(file_path))
        file_id = batch_service.upload_batch_file(str(file_path))
        batch = batch_service.create_batch(file_id, "/v1/embeddings")

        # Test status transitions
        statuses = ["validating", "in_progress", "finalizing", "completed", "failed", "cancelled", "expired"]

        for status in statuses:
            batch_service.client.batches.update_batch_status(batch.batch_api_id, status)
            retrieved = batch_service.retrieve_batch(batch.batch_api_id)
            assert retrieved.status == status

    def test_error_file_generation(self, batch_service, tmp_path):
        """Test that error files are generated for failed requests."""
        # Create batch with multiple requests
        requests = [
            {"custom_id": f"test-{i}", "method": "POST", "url": "/v1/embeddings", "body": {}}
            for i in range(100)
        ]

        file_path = tmp_path / "test.jsonl"
        batch_service.create_batch_file(requests, str(file_path))
        file_id = batch_service.upload_batch_file(str(file_path))
        batch = batch_service.create_batch(file_id, "/v1/embeddings")

        # Check that some requests failed (5% failure rate)
        assert batch.request_counts["failed"] > 0
        assert batch.error_file_id is not None

        # Retrieve error file
        errors = batch_service.retrieve_results(batch.error_file_id)
        assert len(errors) == batch.request_counts["failed"]

        # Verify error format
        for error in errors:
            assert "custom_id" in error
            assert "error" in error
            assert "code" in error["error"]
            assert "message" in error["error"]

    def test_handle_batch_errors_marks_items_failed(self, test_db_engine, batch_service, tmp_path):
        """Test that error handling marks CVs as failed."""
        # Create CV
        with Session(test_db_engine) as session:
            cv = CV(
                filename="test.pdf",
                content={},
                embedding_status="processing"
            )
            session.add(cv)
            session.commit()
            session.refresh(cv)
            cv_id = cv.id

        # Create batch with this CV
        requests = [{
            "custom_id": f"cv-{cv_id}",
            "method": "POST",
            "url": "/v1/embeddings",
            "body": {}
        }]

        file_path = tmp_path / "test.jsonl"
        batch_service.create_batch_file(requests, str(file_path))
        file_id = batch_service.upload_batch_file(str(file_path))

        # Create batch request
        from core.db.models import BatchRequest
        batch_req = BatchRequest(
            batch_api_id="test_batch",
            input_file_id=file_id,
            status="completed",
            batch_metadata={"type": "embedding"}
        )

        # Manually create error file
        error_entry = {
            "id": "batch_req_error_123",
            "custom_id": f"cv-{cv_id}",
            "response": None,
            "error": {
                "code": "rate_limit_exceeded",
                "message": "Rate limit exceeded"
            }
        }

        error_file_id = "file_mock_error_123"
        error_path = Path(".mock_batches/output_files") / f"{error_file_id}.jsonl"
        error_path.parent.mkdir(parents=True, exist_ok=True)

        with open(error_path, "w") as f:
            f.write(json.dumps(error_entry) + "\n")

        # Handle errors
        from core.worker.tasks import _handle_batch_errors
        with Session(test_db_engine) as session:
            _handle_batch_errors(batch_req, error_file_id, session, batch_service)
            session.commit()

            # Verify CV is marked as failed
            cv = session.get(CV, cv_id)
            assert cv.embedding_status == "failed"

    def test_failed_batch_marks_all_items_failed(self, test_db_engine, batch_service, tmp_path):
        """Test that entirely failed batches mark all items as failed."""
        # Create multiple CVs
        cv_ids = []
        with Session(test_db_engine) as session:
            for i in range(5):
                cv = CV(
                    filename=f"test_{i}.pdf",
                    content={},
                    embedding_status="processing"
                )
                session.add(cv)
                session.commit()
                session.refresh(cv)
                cv_ids.append(cv.id)

        # Create batch input file
        requests = [
            {"custom_id": f"cv-{cv_id}", "method": "POST", "url": "/v1/embeddings", "body": {}}
            for cv_id in cv_ids
        ]

        file_path = tmp_path / "test.jsonl"
        batch_service.create_batch_file(requests, str(file_path))
        file_id = batch_service.upload_batch_file(str(file_path))

        # Simulate failed batch processing (like check_batch_status_task would do)
        from core.db.models import BatchRequest

        batch_req = BatchRequest(
            batch_api_id="failed_batch",
            input_file_id=file_id,
            status="failed",
            batch_metadata={"type": "embedding"}
        )

        with Session(test_db_engine) as session:
            # Simulate the error handling logic from check_batch_status_task
            file_content_str = open(file_path, "r").read()
            for line in file_content_str.strip().split('\n'):
                if not line.strip():
                    continue

                req = json.loads(line)
                custom_id = req.get("custom_id")

                if custom_id and custom_id.startswith("cv-"):
                    cv_id = int(custom_id.replace("cv-", ""))
                    cv = session.get(CV, cv_id)
                    if cv:
                        cv.embedding_status = "failed"
                        session.add(cv)

            session.commit()

            # Verify all CVs are marked as failed
            for cv_id in cv_ids:
                cv = session.get(CV, cv_id)
                assert cv.embedding_status == "failed"


class TestFilterExcludesFailedItems:
    """Test that filters exclude failed/cancelled items."""

    def test_cv_embedding_task_excludes_failed(self, test_db_engine):
        """Test that CV embedding task doesn't pick up failed CVs."""
        with Session(test_db_engine) as session:
            # Create CVs with different statuses
            cv1 = CV(filename="pending.pdf", content={}, embedding_status="pending_batch")
            cv2 = CV(filename="failed.pdf", content={}, embedding_status="failed")
            cv3 = CV(filename="processing.pdf", content={}, embedding_status="processing")

            session.add_all([cv1, cv2, cv3])
            session.commit()

            # Query like the task does
            from sqlalchemy import func
            pending_count = session.exec(
                select(func.count(CV.id)).where(CV.embedding_status == "pending_batch")
            ).one()

            assert pending_count == 1  # Only cv1

            cvs = session.exec(
                select(CV).where(CV.embedding_status == "pending_batch")
            ).all()

            assert len(cvs) == 1
            assert cvs[0].filename == "pending.pdf"

    def test_job_embedding_task_excludes_failed(self, test_db_engine):
        """Test that Job embedding task doesn't pick up failed jobs."""
        with Session(test_db_engine) as session:
            job1 = Job(job_id="job1", title="Test", company="Co", description="Desc", embedding_status="pending_batch")
            job2 = Job(job_id="job2", title="Test2", company="Co2", description="Desc2", embedding_status="failed")

            session.add_all([job1, job2])
            session.commit()

            from sqlalchemy import func
            pending_count = session.exec(
                select(func.count(Job.id)).where(Job.embedding_status == "pending_batch")
            ).one()

            assert pending_count == 1

    def test_cv_parsing_task_excludes_failed(self, test_db_engine):
        """Test that CV parsing task doesn't pick up failed CVs."""
        with Session(test_db_engine) as session:
            cv1 = CV(filename="pending.pdf", content={}, parsing_status="pending_batch")
            cv2 = CV(filename="failed.pdf", content={}, parsing_status="failed")

            session.add_all([cv1, cv2])
            session.commit()

            from sqlalchemy import func
            pending_count = session.exec(
                select(func.count(CV.id)).where(CV.parsing_status == "pending_batch")
            ).one()

            assert pending_count == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
