"""
Batch CV Matching System

Efficiently processes multiple CVs for job matching using:
1. Optimized pgvector queries with CROSS JOIN LATERAL
2. Pre-computed canonical text representations
3. Bulk database operations
4. Batch explanation generation via SimpleBatchExplainer

Flow:
1. Find CVs needing fresh matches (> 6 hours old or never analyzed)
2. Perform batch vector search across all jobs
3. Create predictions in bulk
4. Submit explanation requests via SimpleBatchExplainer (cache cleared when explanations complete)
"""

import logging
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict

from core.db.models import CV, Prediction
from sqlmodel import Session, select
from sqlalchemy import text

logger = logging.getLogger(__name__)


class BatchMatcher:
    """Handles batch matching of CVs to jobs with optimized queries."""

    def find_cvs_needing_matches(
        self,
        session: Session,
        cutoff_hours: int = 6,
        batch_size: Optional[int] = None
    ) -> List[CV]:
        """
        Find CVs that need fresh matches.

        SCALABILITY: Uses LIMIT to prevent loading all CVs into memory.

        Args:
            session: Database session
            cutoff_hours: Hours since last analysis to consider stale
            batch_size: Maximum number of CVs to fetch (prevents OOM)

        Returns:
            List of CV records needing matches (limited by batch_size)
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=cutoff_hours)

        query = select(CV).where(
            CV.embedding_status == "completed",
            CV.is_latest == True,
            (CV.last_analyzed == None) | (CV.last_analyzed < cutoff_time)
        ).order_by(CV.last_analyzed.asc().nullsfirst())  # Process oldest first

        if batch_size:
            query = query.limit(batch_size)

        cvs = session.exec(query).all()
        return cvs

    def perform_vector_search(
        self,
        session: Session,
        cv_ids: List[int],
        top_k: int = 10
    ) -> List[Any]:
        """
        Perform batch vector search using optimized pgvector query.

        OPTIMIZATIONS:
        - Parameterized query for SQL injection prevention and plan caching
        - CROSS JOIN LATERAL for efficient similarity search
        - Fetches both cv.canonical_text and job.canonical_text
        - Single query for all CVs

        Args:
            session: Database session
            cv_ids: List of CV IDs to match
            top_k: Number of top jobs to return per CV

        Returns:
            Query results with cv_id, cv_text, job_id, job_data, job_text, similarity
        """
        query = text("""
            SELECT
                c.id as cv_id,
                c.canonical_text as cv_text,
                j.job_id as job_id,
                j.canonical_json as job_data,
                j.canonical_text as job_text,
                1 - (c.embedding <=> j.embedding) as similarity
            FROM cv c
            CROSS JOIN LATERAL (
                SELECT id as job_id, canonical_json, canonical_text, embedding
                FROM job j
                WHERE j.embedding_status = 'completed'
                ORDER BY j.embedding <=> c.embedding
                LIMIT :top_k
            ) j
            WHERE c.id = ANY(:cv_ids)
            AND c.embedding_status = 'completed'
        """)

        results = session.exec(query, params={"cv_ids": cv_ids, "top_k": top_k}).all()
        return results

    def group_matches_by_cv(
        self,
        results: List[Any]
    ) -> Dict[int, Dict[str, Any]]:
        """
        Group vector search results by CV ID.

        Args:
            results: Query results from perform_vector_search

        Returns:
            Dictionary mapping cv_id -> {"cv_text": str, "matches": List[Dict]}
        """
        matches_by_cv = defaultdict(lambda: {"cv_text": None, "matches": []})

        for row in results:
            cv_id = row.cv_id
            if matches_by_cv[cv_id]["cv_text"] is None:
                # Store cv_text once per CV (from pre-computed canonical_text)
                matches_by_cv[cv_id]["cv_text"] = row.cv_text or ""

            matches_by_cv[cv_id]["matches"].append({
                "job_id": row.job_id,
                "data": row.job_data,
                "job_text": row.job_text,
                "similarity": float(row.similarity),
                "explanation": None  # Will be filled by batch explanation job
            })

        return dict(matches_by_cv)


    def create_predictions_bulk(
        self,
        session: Session,
        matches_by_cv: Dict[int, Dict[str, Any]]
    ) -> tuple[List[Prediction], List[CV]]:
        """
        Create prediction records in bulk.

        OPTIMIZATION: Single pass through data, no nested loops.

        Args:
            session: Database session
            matches_by_cv: Grouped matches from group_matches_by_cv

        Returns:
            Tuple of (predictions_to_add, cvs_to_update)
        """
        predictions_to_add = []
        cvs_to_update = []
        current_time = datetime.utcnow()

        for cv_id, data in matches_by_cv.items():
            cv = session.get(CV, cv_id)
            if not cv:
                logger.warning(f"CV {cv_id} not found")
                continue

            prediction_id = str(uuid.uuid4())
            matches = data["matches"]

            # Check if this is the CV's first prediction
            is_first = cv.last_analyzed is None

            # Create prediction with generation tracking
            prediction = Prediction(
                prediction_id=prediction_id,
                cv_id=str(cv.id),
                matches=matches,
                matching_completed_at=current_time,  # Track when matching completed
                is_first_prediction=is_first  # Track if this is first-time CV
            )
            predictions_to_add.append(prediction)

            # Update CV last_analyzed
            cv.last_analyzed = current_time
            cvs_to_update.append(cv)

        return predictions_to_add, cvs_to_update


    def process_batch_matches(
        self,
        session: Session,
        cutoff_hours: int = 6,
        top_k: int = 10,
        batch_size: Optional[int] = None
    ) -> str:
        """
        Main entry point: Find CVs, perform matches, create predictions, submit explanations.

        SCALABILITY: Accepts batch_size to limit memory usage.

        Args:
            session: Database session
            cutoff_hours: Hours since last analysis to consider stale
            top_k: Number of top jobs to return per CV
            batch_size: Maximum number of CVs to process (prevents OOM)

        Returns:
            Status message
        """
        try:
            # Step 1: Find CVs needing matches (with batch size limit)
            cvs = self.find_cvs_needing_matches(session, cutoff_hours, batch_size)

            if not cvs:
                return "No CVs need matching"

            cv_ids = [cv.id for cv in cvs]
            logger.info(f"Found {len(cv_ids)} CVs for batch matching")

            # Step 2: Perform vector search
            results = self.perform_vector_search(session, cv_ids, top_k)

            if not results:
                logger.warning("No matches found")
                return "No matches found"

            # Step 3: Group results
            matches_by_cv = self.group_matches_by_cv(results)

            # Step 4: Create predictions in bulk
            predictions_to_add, cvs_to_update = \
                self.create_predictions_bulk(session, matches_by_cv)

            # Step 5: Save to database
            session.add_all(predictions_to_add)
            session.add_all(cvs_to_update)
            session.commit()

            logger.info(f"Created {len(predictions_to_add)} predictions for {len(cvs_to_update)} CVs")

            # Step 6: Submit explanation batch using SimpleBatchExplainer
            if predictions_to_add:
                from core.matching.batch_explainer import SimpleBatchExplainer
                explainer = SimpleBatchExplainer()
                batch_req = explainer.submit_batch_explanation_job(predictions_to_add, session)
                if batch_req:
                    logger.info(f"Submitted simple explanation batch {batch_req.batch_api_id}")
                    return f"Processed {len(predictions_to_add)} predictions, submitted explanation batch {batch_req.batch_api_id}"

            return f"Processed {len(predictions_to_add)} predictions"

        except Exception as e:
            logger.error(f"Batch matching failed: {e}")
            raise
