"""
Simple Batch Explanation Generator

ONE short sentence for everyone - clean and simple!

Example: "Strong match based on 5+ years AI/ML experience and expertise in LLMs"
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import os
import logging

from core.services.batch_service import BatchService
from core.db.models import Prediction, BatchRequest
from core.cache.redis_cache import redis_client
from sqlmodel import Session, select

logger = logging.getLogger(__name__)


class SimpleBatchExplainer:
    """Generate simple one-sentence explanations using batch API."""

    def __init__(self):
        self.batch_service = BatchService()

    def _format_simple_prompt(
        self,
        cv_data: dict,
        job_data: dict,
        factors: dict,
        matched_skills: list,
        missing_skills: list
    ) -> str:
        """Create ONE simple sentence explanation - ~15 words max."""
        match_score = int(factors.get("skills_match", 0) * 100)
        cv_years = len(cv_data.get("work", []))
        job_title = job_data.get("title", "this role")

        prompt = f"""Write ONE short sentence explaining why this candidate matches this job.

Job: {job_title}
Matched Skills: {', '.join(matched_skills[:3])}
Experience: {cv_years} positions
Score: {match_score}%

Examples:
"Strong match based on 5+ years AI/ML experience and expertise in LLMs"
"Good fit with React, Node.js skills and 3 years full-stack experience"
"Excellent match - senior Java developer with 8+ years enterprise experience"

Write ONLY ONE sentence, max 15 words:
"""
        return prompt

    def prepare_simple_explanation_requests(
        self,
        predictions: List[Prediction],
        model: str = "gpt-4o-mini"
    ) -> List[Dict[str, Any]]:
        """Prepare batch requests for simple explanations."""
        requests = []

        for prediction in predictions:
            cv_data = getattr(prediction, 'cv_data', {})

            for match in prediction.matches:
                job_data = match.get("job_data", {})
                factors = match.get("matching_factors", {})
                matched_skills = match.get("matched_skills", [])
                missing_skills = match.get("missing_skills", [])

                prompt = self._format_simple_prompt(
                    cv_data, job_data, factors, matched_skills, missing_skills
                )

                req = {
                    "custom_id": f"explain-{prediction.prediction_id}-{match['job_id']}",
                    "method": "POST",
                    "url": "/v1/chat/completions",
                    "body": {
                        "model": model,
                        "messages": [
                            {
                                "role": "system",
                                "content": "You write ultra-concise job match explanations. ONE sentence only. Maximum 15 words. Be specific about skills and experience."
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "temperature": 0.3,
                        "max_tokens": 50
                    }
                }
                requests.append(req)

        logger.info(f"Prepared {len(requests)} simple explanation requests")
        return requests

    def submit_batch_explanation_job(
        self,
        predictions: List[Prediction],
        session: Session
    ) -> Optional[BatchRequest]:
        """Submit batch job for simple explanations."""
        try:
            requests = self.prepare_simple_explanation_requests(predictions)

            if not requests:
                return None

            timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            file_path = f"/tmp/batch_simple_explanations_{timestamp}.jsonl"

            self.batch_service.create_batch_file(requests, file_path)
            file_id = self.batch_service.upload_batch_file(file_path)

            batch_req = self.batch_service.create_batch(
                input_file_id=file_id,
                endpoint="/v1/chat/completions",
                metadata={"type": "explanation_simple", "count": str(len(requests))}
            )

            session.add(batch_req)
            session.commit()

            if os.path.exists(file_path):
                os.remove(file_path)

            logger.info(f"Submitted simple explanation batch: {batch_req.batch_api_id}")
            return batch_req

        except Exception as e:
            logger.error(f"Failed to submit explanation batch: {e}")
            return None

    def process_explanation_results(
        self,
        batch_request: BatchRequest,
        session: Session
    ) -> Dict[str, Any]:
        """Process completed explanation batch."""
        if batch_request.status != "completed":
            raise ValueError(f"Batch not completed: {batch_request.status}")

        results = self.batch_service.retrieve_results(batch_request.output_file_id)
        stats = {"total": len(results), "successful": 0, "failed": 0}
        explanations = {}

        for result in results:
            custom_id = result.get("custom_id", "")
            if not custom_id.startswith("explain-"):
                continue

            try:
                parts = custom_id.replace("explain-", "").split("-", 1)
                prediction_id, job_id = parts[0], parts[1]

                response_body = result.get("response", {}).get("body", {})
                choices = response_body.get("choices", [])
                if not choices:
                    stats["failed"] += 1
                    continue

                explanation = choices[0].get("message", {}).get("content", "").strip()

                if prediction_id not in explanations:
                    explanations[prediction_id] = {}
                explanations[prediction_id][job_id] = explanation
                stats["successful"] += 1

            except Exception as e:
                logger.error(f"Failed to parse result {custom_id}: {e}")
                stats["failed"] += 1

        # Track CVs that need cache invalidation
        updated_cv_ids = set()
        explanation_completion_time = datetime.utcnow()

        # Update predictions
        for pred_id, job_explanations in explanations.items():
            prediction = session.exec(
                select(Prediction).where(Prediction.prediction_id == pred_id)
            ).first()

            if prediction:
                # Track the CV ID for cache invalidation
                updated_cv_ids.add(prediction.cv_id)

                for match in prediction.matches:
                    job_id = str(match.get("job_id"))
                    if job_id in job_explanations:
                        match["explanation"] = job_explanations[job_id]

                # Set explanation completion timestamp
                prediction.explanation_completed_at = explanation_completion_time
                session.add(prediction)

        session.commit()
        
        # Clear Redis cache for updated CVs
        strategy = "pgvector"  # Match the strategy used in candidate.py
        for cv_id in updated_cv_ids:
            cache_key = f"match_results:{strategy}:{cv_id}"
            redis_client.delete(cache_key)
            logger.info(f"Cleared cache for CV {cv_id} after explanation update")
        
        logger.info(f"Processed simple explanations: {stats}")
        logger.info(f"Cleared cache for {len(updated_cv_ids)} CVs")
        return stats
