import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import os
from datetime import datetime

# Assuming we might use OpenAI client
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from core.db.models import BatchRequest, CV
from sqlmodel import Session, select

logger = logging.getLogger(__name__)

class BatchService:
    def __init__(self, api_key: str = None):
        if OpenAI:
            self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        else:
            self.client = None
            logger.warning("OpenAI library not installed. BatchService will fail if used.")

    def create_batch_file(self, requests: List[Dict[str, Any]], file_path: str) -> str:
        """
        Create a .jsonl file from a list of request dictionaries.
        """
        with open(file_path, 'w') as f:
            for req in requests:
                f.write(json.dumps(req) + '\n')
        return file_path

    def upload_batch_file(self, file_path: str) -> str:
        """
        Upload the .jsonl file to OpenAI. Returns file_id.
        """
        if not self.client:
            raise RuntimeError("OpenAI client not initialized")
            
        with open(file_path, "rb") as f:
            batch_input_file = self.client.files.create(
                file=f,
                purpose="batch"
            )
        return batch_input_file.id

    def create_batch(self, input_file_id: str, endpoint: str, metadata: Dict = None) -> BatchRequest:
        """
        Create a batch job in OpenAI.
        """
        if not self.client:
            raise RuntimeError("OpenAI client not initialized")

        batch = self.client.batches.create(
            input_file_id=input_file_id,
            endpoint=endpoint,
            completion_window="24h",
            metadata=metadata
        )
        
        # Convert to our DB model format
        return BatchRequest(
            batch_api_id=batch.id,
            input_file_id=batch.input_file_id,
            status=batch.status,
            created_at=datetime.fromtimestamp(batch.created_at) if batch.created_at else datetime.utcnow(),
            batch_metadata=batch.metadata
        )

    def retrieve_batch(self, batch_id: str):
        """
        Get batch status from OpenAI.
        """
        if not self.client:
            raise RuntimeError("OpenAI client not initialized")
        return self.client.batches.retrieve(batch_id)

    def retrieve_results(self, file_id: str) -> List[Dict]:
        """
        Download and parse results from OpenAI.
        """
        if not self.client:
            raise RuntimeError("OpenAI client not initialized")
            
        content = self.client.files.content(file_id).text
        results = []
        for line in content.split('\n'):
            if line.strip():
                results.append(json.loads(line))
        return results

    def cancel_batch(self, batch_id: str):
        if not self.client:
            raise RuntimeError("OpenAI client not initialized")
        self.client.batches.cancel(batch_id)

    def prepare_embedding_requests(self, cvs: List[CV], model: str = "text-embedding-3-small") -> List[Dict]:
        """
        Prepare batch requests for CV embeddings.
        """
        requests = []
        for cv in cvs:
            if not cv.content:
                continue
                
            # Construct text representation
            # This logic should match what's in tasks.py/cv_service.py
            text_rep = ""
            basics = cv.content.get('basics', {})
            skills = cv.content.get('skills', [])
            
            text_rep += f"{basics.get('name', '')} {basics.get('summary', '')} "
            text_rep += " ".join([s.get("name", "") if isinstance(s, dict) else str(s) for s in skills])
            
            # Truncate if necessary (simplified)
            text_rep = text_rep[:8000] 

            req = {
                "custom_id": f"cv-{cv.id}",
                "method": "POST",
                "url": "/v1/embeddings",
                "body": {
                    "model": model,
                    "input": text_rep
                }
            }
            requests.append(req)
        return requests

    def prepare_job_embedding_requests(self, jobs: List[Any], model: str = "text-embedding-3-small") -> List[Dict]:
        """
        Prepare batch requests for Job embeddings.
        """
        from core.services.job_service import get_job_text_representation
        
        requests = []
        for job in jobs:
            # Convert job object to dict if needed
            job_data = job.dict() if hasattr(job, 'dict') else job.__dict__
            
            text_rep = get_job_text_representation(job_data)
            # Truncate
            text_rep = text_rep[:8000]

            req = {
                "custom_id": f"job-{job.id}", # Use numeric ID for easier lookup
                "method": "POST",
                "url": "/v1/embeddings",
                "body": {
                    "model": model,
                    "input": text_rep
                }
            }
            requests.append(req)
        return requests

    def prepare_explanation_requests(self, matches: List[Dict], model: str = "gpt-3.5-turbo") -> List[Dict]:
        """
        Prepare batch requests for match explanations.
        """
        requests = []
        for match in matches:
            # match dict expected to have: cv_id, job_id, cv_text, job_text, score, factors
            custom_id = f"explain-{match['cv_id']}-{match['job_id']}"
            
            prompt = f"""You are an expert HR assistant. Explain why this candidate is a good match for the job.
            
            Candidate Profile:
            {match['cv_text'][:1000]}
            
            Job Description:
            {match['job_text'][:1000]}
            
            Match Score: {match['score']:.2f}
            Factors: {match['factors']}
            
            Provide a concise explanation (max 3 sentences) highlighting key matching skills and experience.
            """
            
            req = {
                "custom_id": custom_id,
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": "You are a helpful HR assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 150
                }
            }
            requests.append(req)
        return requests
