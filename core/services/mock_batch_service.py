"""
Mock Batch Service for Testing

Simulates OpenAI Batch API behavior without making real API calls.
Useful for testing batch operations without cost or waiting.

Features:
- Saves batch files to local storage
- Simulates batch status transitions (validating → in_progress → completed)
- Generates mock responses based on request type (embeddings, parsing, explanations)
- Tracks batch metadata in JSON files
- Probabilistic failures to simulate real-world conditions
"""

import json
import os
import uuid
import random
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class MockBatch:
    """Simulates OpenAI Batch object."""

    def __init__(
        self,
        batch_id: str,
        input_file_id: str,
        endpoint: str,
        status: str = "validating",
        metadata: Optional[Dict] = None
    ):
        self.id = batch_id
        self.input_file_id = input_file_id
        self.endpoint = endpoint
        self.status = status
        self.created_at = int(datetime.utcnow().timestamp())
        self.metadata = metadata or {}
        self.request_counts = {"total": 0, "completed": 0, "failed": 0}
        self.output_file_id = None
        self.error_file_id = None


class MockBatchClient:
    """
    Mock OpenAI Batch API client.

    Stores batches in: .mock_batches/
    - input_files/{file_id}.jsonl - Input requests
    - output_files/{file_id}.jsonl - Output responses
    - batch_metadata/{batch_id}.json - Batch status/metadata
    """

    def __init__(self, mock_dir: str = ".mock_batches"):
        """
        Initialize mock batch client.

        Args:
            mock_dir: Directory to store mock batch files (added to .gitignore)
        """
        self.mock_dir = Path(mock_dir)
        self.input_dir = self.mock_dir / "input_files"
        self.output_dir = self.mock_dir / "output_files"
        self.metadata_dir = self.mock_dir / "batch_metadata"

        # Create directories
        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"MockBatchClient initialized at {self.mock_dir}")

    def create(
        self,
        input_file_id: str,
        endpoint: str,
        completion_window: str = "24h",
        metadata: Optional[Dict] = None
    ) -> MockBatch:
        """
        Simulate creating a batch job.

        Args:
            input_file_id: Input file ID
            endpoint: API endpoint
            completion_window: Completion window (ignored in mock)
            metadata: Batch metadata

        Returns:
            MockBatch object
        """
        batch_id = f"batch_mock_{uuid.uuid4().hex[:16]}"

        batch = MockBatch(
            batch_id=batch_id,
            input_file_id=input_file_id,
            endpoint=endpoint,
            status="validating",
            metadata=metadata
        )

        # Save batch metadata
        self._save_batch_metadata(batch)

        # Read input file and generate responses immediately (for testing speed)
        self._process_batch_immediately(batch)

        logger.info(f"Created mock batch {batch_id}")
        return batch

    def retrieve(self, batch_id: str) -> MockBatch:
        """
        Retrieve batch status.

        Args:
            batch_id: Batch ID

        Returns:
            MockBatch object
        """
        metadata_path = self.metadata_dir / f"{batch_id}.json"

        if not metadata_path.exists():
            raise ValueError(f"Batch {batch_id} not found")

        with open(metadata_path, "r") as f:
            data = json.load(f)

        batch = MockBatch(
            batch_id=data["id"],
            input_file_id=data["input_file_id"],
            endpoint=data["endpoint"],
            status=data["status"],
            metadata=data.get("metadata", {})
        )
        batch.created_at = data["created_at"]
        batch.request_counts = data["request_counts"]
        batch.output_file_id = data.get("output_file_id")
        batch.error_file_id = data.get("error_file_id")

        return batch

    def cancel(self, batch_id: str):
        """Cancel a batch (simulated)."""
        batch = self.retrieve(batch_id)
        batch.status = "cancelled"
        self._save_batch_metadata(batch)
        logger.info(f"Cancelled batch {batch_id}")

    def update_batch_status(self, batch_id: str, status: str):
        """
        Update batch status manually (for testing status transitions).

        Args:
            batch_id: Batch ID
            status: New status (validating, in_progress, finalizing, completed, failed, cancelled, expired)
        """
        valid_statuses = ["validating", "in_progress", "finalizing", "completed", "failed", "cancelled", "expired"]
        if status not in valid_statuses:
            raise ValueError(f"Invalid status: {status}. Must be one of {valid_statuses}")

        batch = self.retrieve(batch_id)
        batch.status = status
        self._save_batch_metadata(batch)
        logger.info(f"Updated batch {batch_id} status to {status}")

    def _save_batch_metadata(self, batch: MockBatch):
        """Save batch metadata to JSON file."""
        metadata_path = self.metadata_dir / f"{batch.id}.json"

        data = {
            "id": batch.id,
            "input_file_id": batch.input_file_id,
            "endpoint": batch.endpoint,
            "status": batch.status,
            "created_at": batch.created_at,
            "metadata": batch.metadata,
            "request_counts": batch.request_counts,
            "output_file_id": batch.output_file_id,
            "error_file_id": batch.error_file_id
        }

        with open(metadata_path, "w") as f:
            json.dump(data, indent=2, fp=f)

    def _process_batch_immediately(self, batch: MockBatch):
        """
        Process batch immediately (for testing).

        In real OpenAI, this takes hours. For testing, we do it instantly.
        """
        # Read input file
        input_path = self.input_dir / f"{batch.input_file_id}.jsonl"

        if not input_path.exists():
            batch.status = "failed"
            self._save_batch_metadata(batch)
            return

        requests = []
        with open(input_path, "r") as f:
            for line in f:
                if line.strip():
                    requests.append(json.loads(line))

        batch.request_counts["total"] = len(requests)

        # Generate responses based on endpoint
        responses = []
        errors = []

        for req in requests:
            # Simulate 5% failure rate
            if random.random() < 0.05:
                batch.request_counts["failed"] += 1
                # Generate error entry
                error_entry = {
                    "id": f"batch_req_error_{uuid.uuid4().hex[:16]}",
                    "custom_id": req.get("custom_id", "unknown"),
                    "response": None,
                    "error": {
                        "code": "rate_limit_exceeded",
                        "message": "Rate limit exceeded. Please retry after some time."
                    }
                }
                errors.append(error_entry)
                continue

            response = self._generate_mock_response(req, batch.endpoint)
            responses.append(response)
            batch.request_counts["completed"] += 1

        # Save output file (successful responses)
        output_file_id = f"file_mock_{uuid.uuid4().hex[:16]}"
        output_path = self.output_dir / f"{output_file_id}.jsonl"

        with open(output_path, "w") as f:
            for resp in responses:
                f.write(json.dumps(resp) + "\n")

        # Save error file (if any failures)
        error_file_id = None
        if errors:
            error_file_id = f"file_mock_error_{uuid.uuid4().hex[:16]}"
            error_path = self.output_dir / f"{error_file_id}.jsonl"

            with open(error_path, "w") as f:
                for error in errors:
                    f.write(json.dumps(error) + "\n")

        # Update batch status
        batch.status = "completed"
        batch.output_file_id = output_file_id
        batch.error_file_id = error_file_id
        self._save_batch_metadata(batch)

        logger.info(
            f"Processed batch {batch.id}: "
            f"{batch.request_counts['completed']} completed, "
            f"{batch.request_counts['failed']} failed"
        )

    def _generate_mock_response(self, request: Dict, endpoint: str) -> Dict:
        """
        Generate mock response based on request type.

        Args:
            request: Request object
            endpoint: API endpoint

        Returns:
            Mock response object
        """
        custom_id = request.get("custom_id", "unknown")
        body = request.get("body", {})

        if endpoint == "/v1/embeddings":
            # Mock embedding response
            # Determine dimensions based on model
            model = body.get("model", "text-embedding-3-small")

            if "3-large" in model:
                dims = 3072  # OpenAI large
            elif "gemini" in model or "nomic" in model:
                dims = 768   # Gemini/Ollama
            else:
                dims = 1536  # OpenAI small (default)

            embedding = [random.gauss(0, 0.1) for _ in range(dims)]
            response_body = {
                "object": "list",
                "data": [
                    {
                        "object": "embedding",
                        "embedding": embedding,
                        "index": 0
                    }
                ],
                "model": model,
                "usage": {
                    "prompt_tokens": 50,
                    "total_tokens": 50
                }
            }

        elif endpoint == "/v1/chat/completions":
            # Determine response type based on custom_id or metadata
            if "parse" in custom_id.lower():
                # CV Parsing response
                response_body = self._generate_mock_cv_parse()
            else:
                # Explanation response
                response_body = self._generate_mock_explanation(custom_id)

        else:
            # Generic response
            response_body = {"result": "mock_response"}

        return {
            "id": f"batch_req_mock_{uuid.uuid4().hex[:16]}",
            "custom_id": custom_id,
            "response": {
                "status_code": 200,
                "request_id": f"req_mock_{uuid.uuid4().hex[:16]}",
                "body": response_body
            },
            "error": None
        }

    def _generate_mock_cv_parse(self) -> Dict:
        """Generate mock CV parsing response."""
        content = json.dumps({
            "basics": {
                "name": "Mock Candidate",
                "label": "Software Engineer",
                "email": "mock@example.com",
                "phone": "+1234567890",
                "summary": "Experienced software engineer with expertise in Python and web development."
            },
            "work": [
                {
                    "company": "Mock Company",
                    "position": "Senior Developer",
                    "startDate": "2020-01",
                    "endDate": "2023-12",
                    "summary": "Led development of key features"
                }
            ],
            "education": [
                {
                    "institution": "Mock University",
                    "area": "Computer Science",
                    "studyType": "Bachelor",
                    "startDate": "2016",
                    "endDate": "2020"
                }
            ],
            "skills": [
                {"name": "Python", "level": "Expert", "keywords": ["Django", "Flask"]},
                {"name": "JavaScript", "level": "Advanced", "keywords": ["React", "Node.js"]}
            ]
        })

        return {
            "id": f"chatcmpl_mock_{uuid.uuid4().hex[:16]}",
            "object": "chat.completion",
            "created": int(datetime.utcnow().timestamp()),
            "model": "gpt-4o-mini",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": content
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 500,
                "completion_tokens": 300,
                "total_tokens": 800
            }
        }

    def _generate_mock_explanation(self, custom_id: str) -> Dict:
        """Generate mock explanation response."""
        content = "This candidate is a great match because they have relevant experience in software development and the required technical skills. Their background aligns well with the job requirements."

        return {
            "id": f"chatcmpl_mock_{uuid.uuid4().hex[:16]}",
            "object": "chat.completion",
            "created": int(datetime.utcnow().timestamp()),
            "model": "gpt-3.5-turbo",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": content
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150
            }
        }


class MockFileClient:
    """Mock OpenAI Files API client."""

    def __init__(self, mock_batch_client: MockBatchClient):
        self.mock_batch_client = mock_batch_client

    def create(self, file, purpose: str):
        """
        Simulate file upload.

        Args:
            file: File object (must have .read() method)
            purpose: File purpose (e.g., "batch")

        Returns:
            Mock file object with ID
        """
        file_id = f"file_mock_{uuid.uuid4().hex[:16]}"

        # Save file to input_files directory
        file_path = self.mock_batch_client.input_dir / f"{file_id}.jsonl"

        content = file.read()
        if isinstance(content, bytes):
            content = content.decode('utf-8')

        with open(file_path, "w") as f:
            f.write(content)

        logger.info(f"Created mock file {file_id}")

        # Return mock file object
        class MockFile:
            def __init__(self, file_id):
                self.id = file_id
                self.purpose = purpose
                self.created_at = int(datetime.utcnow().timestamp())

        return MockFile(file_id)

    def content(self, file_id: str):
        """
        Retrieve file content.

        Args:
            file_id: File ID

        Returns:
            Mock response with .text property
        """
        # Check output files first, then input files
        file_path = self.mock_batch_client.output_dir / f"{file_id}.jsonl"

        if not file_path.exists():
            file_path = self.mock_batch_client.input_dir / f"{file_id}.jsonl"

        if not file_path.exists():
            raise ValueError(f"File {file_id} not found")

        with open(file_path, "r") as f:
            content = f.read()

        class MockContent:
            def __init__(self, text):
                self.text = text

        return MockContent(content)


class MockOpenAIClient:
    """
    Mock OpenAI client that behaves like the real one.

    Usage:
        client = MockOpenAIClient()
        batch = client.batches.create(...)
        file = client.files.create(...)
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialize mock client (api_key is ignored)."""
        mock_batch_client = MockBatchClient()
        self.batches = MockBatchClient()
        self.files = MockFileClient(mock_batch_client)
        logger.info("MockOpenAIClient initialized")
