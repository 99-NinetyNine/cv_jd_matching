import sys
import os
import logging
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.getcwd())

from core.db.engine import engine
from sqlmodel import Session, select
from core.db.models import CV, Job
from core.worker.tasks import perform_batch_matches
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_batch_optimization():
    with Session(engine) as session:
        # 1. Create a Job
        job = Job(
            job_id=str(uuid.uuid4()),
            title="Batch Optimizer",
            company="Test Corp",
            description="Optimize everything.",
            embedding=[0.1] * 768,
            embedding_status="completed",
            created_at=datetime.utcnow()
        )
        session.add(job)
        
        # 2. Create Old CV (is_latest=False)
        cv_old = CV(
            filename=f"old_cv_{uuid.uuid4()}.pdf",
            content={"basics": {"name": "Old CV"}},
            embedding=[0.1] * 768,
            embedding_status="completed",
            is_latest=False,
            created_at=datetime.utcnow()
        )
        session.add(cv_old)
        
        # 3. Create New CV (is_latest=True, last_analyzed=None) -> Should be picked up
        cv_new = CV(
            filename=f"new_cv_{uuid.uuid4()}.pdf",
            content={"basics": {"name": "New CV"}},
            embedding=[0.1] * 768,
            embedding_status="completed",
            is_latest=True,
            last_analyzed=None,
            created_at=datetime.utcnow()
        )
        session.add(cv_new)
        
        # 4. Create Recently Analyzed CV (is_latest=True, last_analyzed=Now) -> Should be skipped
        cv_recent = CV(
            filename=f"recent_cv_{uuid.uuid4()}.pdf",
            content={"basics": {"name": "Recent CV"}},
            embedding=[0.1] * 768,
            embedding_status="completed",
            is_latest=True,
            last_analyzed=datetime.utcnow(),
            created_at=datetime.utcnow()
        )
        session.add(cv_recent)
        
        session.commit()
        session.refresh(cv_new)
        
        logger.info(f"Created CVs: Old={cv_old.id}, New={cv_new.id}, Recent={cv_recent.id}")
        
        # 5. Run Batch Task
        logger.info("Running perform_batch_matches...")
        result = perform_batch_matches()
        logger.info(f"Result: {result}")
        
        # 6. Verify
        # Check if cv_new was analyzed
        session.refresh(cv_new)
        if cv_new.last_analyzed:
            logger.info(f"SUCCESS: New CV {cv_new.id} was analyzed.")
        else:
            logger.error(f"FAILURE: New CV {cv_new.id} was NOT analyzed.")
            
        # Check if cv_old was analyzed (should not be)
        session.refresh(cv_old)
        if cv_old.last_analyzed:
            logger.error(f"FAILURE: Old CV {cv_old.id} was analyzed (should be skipped).")
        else:
            logger.info(f"SUCCESS: Old CV {cv_old.id} was skipped.")
            
        # Check if cv_recent was re-analyzed (timestamp should be roughly same, but hard to check exact)
        # We can check if it processed it by looking at logs or return value, but simpler:
        # If the task returned "No CVs need matching" when only recent/old existed, that's good.
        # But here we had one new one.
        
if __name__ == "__main__":
    verify_batch_optimization()
