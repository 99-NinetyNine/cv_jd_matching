"""
Batch CV Parsing System

Efficiently processes multiple CVs using:
1. Parallel text extraction (local)
2. Batch OpenAI API calls for structured parsing
3. Quality metrics and validation

Flow:
1. Extract text from all PDFs in parallel (local, fast)
2. Create batch request file for OpenAI parsing
3. Submit to OpenAI Batch API
4. Poll for completion
5. Update database with parsed results
"""

import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import os

from core.parsing.extractors.naive.pdf_parser import PDFParser
from core.db.models import CV, BatchRequest
from core.services.batch_service import BatchService
from sqlmodel import Session

logger = logging.getLogger(__name__)


class BatchCVParser:
    """Handles batch parsing of CVs with text extraction + OpenAI batch API."""

    def __init__(self, max_workers: int = 5):
        """
        Initialize batch parser.

        Args:
            max_workers: Number of parallel workers for text extraction
        """
        self.pdf_parser = PDFParser()
        self.batch_service = BatchService()
        self.max_workers = max_workers

    def extract_text_parallel(
        self,
        cv_records: List[CV],
        uploads_dir: Path = Path("uploads")
    ) -> Dict[int, Dict[str, Any]]:
        """
        Extract text from multiple PDFs in parallel.

        Args:
            cv_records: List of CV database records
            uploads_dir: Directory containing uploaded PDFs

        Returns:
            Dictionary mapping cv.id -> {"text": str, "status": str, "error": Optional[str]}
        """
        results = {}

        def extract_one(cv: CV) -> tuple[int, Dict[str, Any]]:
            """Extract text from a single CV."""
            try:
                file_path = uploads_dir / cv.filename
                if not file_path.exists():
                    return cv.id, {
                        "text": None,
                        "status": "failed",
                        "error": f"File not found: {file_path}"
                    }

                # Use PDFParser's text extraction logic
                text = self.pdf_parser._extract_text(str(file_path))
                self.pdf_parser._validate_content(text)

                return cv.id, {
                    "text": text,
                    "status": "success",
                    "error": None
                }
            except Exception as e:
                logger.error(f"Text extraction failed for CV {cv.id}: {e}")
                return cv.id, {
                    "text": None,
                    "status": "failed",
                    "error": str(e)
                }

        # Execute in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(extract_one, cv): cv for cv in cv_records}

            for future in as_completed(futures):
                cv_id, result = future.result()
                results[cv_id] = result
                logger.info(f"Extracted text for CV {cv_id}: {result['status']}")

        return results

    def prepare_parsing_batch_requests(
        self,
        extracted_texts: Dict[int, Dict[str, Any]],
        model: str = "gpt-4o-mini"
    ) -> List[Dict[str, Any]]:
        """
        Prepare OpenAI batch requests for structured parsing.

        Args:
            extracted_texts: Dictionary from extract_text_parallel()
            model: OpenAI model to use for parsing

        Returns:
            List of batch request objects for OpenAI Batch API
        """
        requests = []

        # Import schema for format instructions
        from core.parsing.schema import Resume
        from pydantic import TypeAdapter

        # Get JSON schema for Resume
        adapter = TypeAdapter(Resume)
        schema = adapter.json_schema()

        for cv_id, data in extracted_texts.items():
            if data["status"] != "success" or not data["text"]:
                continue

            # Truncate text if too long (OpenAI limits)
            cv_text = data["text"][:15000]  # Leave room for prompt

            # Enhanced prompt with ReAct-style instructions
            prompt = f"""You are an expert CV parser. Extract ALL information from the CV into structured JSON format.

TASK: Parse the following CV and extract information according to the JSON Resume schema.

INSTRUCTIONS:
1. Read the CV carefully and identify all sections
2. Extract information for each field in the schema
3. For dates, use ISO 8601 format (YYYY-MM-DD or YYYY-MM or YYYY)
4. For skills, create structured objects with name, level, and keywords
5. Do not hallucinate - only extract information present in the CV
6. If a field is not present, omit it (don't use null or empty values)

CV TEXT:
{cv_text}

OUTPUT FORMAT (JSON Resume Schema):
{json.dumps(schema, indent=2)}

Respond with valid JSON matching the schema above. Extract ALL relevant information.
"""

            req = {
                "custom_id": f"cv-parse-{cv_id}",
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": {
                    "model": model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are an expert CV parser. Extract structured information from CVs following the JSON Resume schema. Always respond with valid JSON."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0,
                    "max_tokens": 4096
                }
            }
            requests.append(req)

        logger.info(f"Prepared {len(requests)} batch parsing requests")
        return requests

    def submit_batch_parsing_job(
        self,
        cv_records: List[CV],
        session: Session,
        uploads_dir: Path = Path("uploads")
    ) -> Optional[BatchRequest]:
        """
        Complete flow: Extract text -> Create batch -> Submit to OpenAI.

        Args:
            cv_records: List of CV records to parse
            session: Database session
            uploads_dir: Directory containing PDF files

        Returns:
            BatchRequest record or None if failed
        """
        try:
            # Step 1: Extract text in parallel (FAST - local operation)
            logger.info(f"Extracting text from {len(cv_records)} CVs in parallel...")
            extracted_texts = self.extract_text_parallel(cv_records, uploads_dir)

            # Step 2: Prepare batch requests
            logger.info("Preparing batch parsing requests...")
            requests = self.prepare_parsing_batch_requests(extracted_texts)

            if not requests:
                logger.warning("No valid CVs to parse")
                return None

            # Step 3: Create JSONL file
            timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            filename = f"batch_cv_parsing_{timestamp}.jsonl"
            file_path = f"/tmp/{filename}"

            self.batch_service.create_batch_file(requests, file_path)
            logger.info(f"Created batch file: {file_path}")

            # Step 4: Upload to OpenAI
            file_id = self.batch_service.upload_batch_file(file_path)
            logger.info(f"Uploaded batch file: {file_id}")

            # Step 5: Create batch job
            batch_req = self.batch_service.create_batch(
                input_file_id=file_id,
                endpoint="/v1/chat/completions",
                metadata={"type": "cv_parsing", "count": str(len(requests))}
            )

            # Step 6: Save to database
            session.add(batch_req)

            # Update CV statuses to processing
            for cv in cv_records:
                if cv.id in extracted_texts and extracted_texts[cv.id]["status"] == "success":
                    cv.parsing_status = "processing"
                    session.add(cv)
                else:
                    # Mark as failed if text extraction failed
                    cv.parsing_status = "failed"
                    session.add(cv)

            session.commit()

            # Cleanup temp file
            if os.path.exists(file_path):
                os.remove(file_path)

            logger.info(f"Submitted batch parsing job: {batch_req.batch_api_id}")
            return batch_req

        except Exception as e:
            logger.error(f"Batch parsing submission failed: {e}")
            return None

    def process_parsing_results(
        self,
        batch_request: BatchRequest,
        session: Session
    ) -> Dict[str, Any]:
        """
        Process completed batch parsing results and update CV records.

        Args:
            batch_request: BatchRequest record (status must be 'completed')
            session: Database session

        Returns:
            Summary statistics
        """
        if batch_request.status != "completed":
            raise ValueError(f"Batch not completed yet: {batch_request.status}")

        if not batch_request.output_file_id:
            raise ValueError("No output file available")

        # Retrieve results from OpenAI
        results = self.batch_service.retrieve_results(batch_request.output_file_id)

        stats = {
            "total": len(results),
            "successful": 0,
            "failed": 0,
            "errors": []
        }

        for result in results:
            custom_id = result.get("custom_id")
            if not custom_id or not custom_id.startswith("cv-parse-"):
                continue

            # Extract CV ID
            cv_id = int(custom_id.replace("cv-parse-", ""))
            cv = session.get(CV, cv_id)

            if not cv:
                logger.warning(f"CV {cv_id} not found in database")
                continue

            try:
                # Extract parsed JSON from response
                response_body = result.get("response", {}).get("body", {})
                choices = response_body.get("choices", [])

                if not choices:
                    raise ValueError("No choices in response")

                content = choices[0].get("message", {}).get("content", "")

                if not content:
                    raise ValueError("Empty content")

                # Parse JSON
                parsed_data = json.loads(content)

                # Validate against schema (optional but recommended)
                from core.parsing.schema import Resume
                Resume(**parsed_data)  # This will raise if invalid

                # Update CV record
                cv.content = parsed_data
                cv.parsing_status = "completed"
                session.add(cv)

                stats["successful"] += 1
                logger.info(f"Successfully parsed CV {cv_id}")

            except Exception as e:
                logger.error(f"Failed to process result for CV {cv_id}: {e}")
                cv.parsing_status = "failed"
                session.add(cv)
                stats["failed"] += 1
                stats["errors"].append({"cv_id": cv_id, "error": str(e)})

        # Update batch request status
        batch_request.status = "processed"
        batch_request.completed_at = datetime.utcnow()
        session.add(batch_request)

        session.commit()

        logger.info(f"Batch parsing results processed: {stats}")
        return stats
