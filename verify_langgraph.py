import sys
import os
import logging
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

from core.matching.semantic_matcher import GraphMatcher
from core.db.engine import engine
from sqlmodel import Session
from core.db.models import Job
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_langgraph():
    # 1. Create a dummy Job with completed embedding
    with Session(engine) as session:
        job_id = str(uuid.uuid4())
        job = Job(
            job_id=job_id,
            title="LangGraph Developer",
            company="AI Corp",
            description="We need a LangGraph expert.",
            embedding=[0.1] * 768,
            embedding_status="completed",
            created_at=datetime.utcnow()
        )
        session.add(job)
        session.commit()
        logger.info(f"Created Job {job.id}")

    # 2. Initialize Matcher
    matcher = GraphMatcher()
    
    # 3. Match
    cv_data = {
        "basics": {"name": "Test User", "summary": "I know LangGraph and Python."},
        "skills": ["LangGraph", "Python"]
    }
    
    logger.info("Running match...")
    results = matcher.match(cv_data)
    
    logger.info(f"Matches found: {len(results)}")
    if len(results) > 0:
        logger.info(f"Top match: {results[0]['job_title']} (Score: {results[0]['match_score']})")
        logger.info(f"Explanation: {results[0].get('explanation')}")
        
        if results[0]['job_id'] == job_id:
            logger.info("SUCCESS: Found the test job")
        else:
            logger.warning("WARNING: Did not find the test job as top match (might be expected if other jobs exist)")
    else:
        logger.error("FAILURE: No matches found")

if __name__ == "__main__":
    verify_langgraph()
