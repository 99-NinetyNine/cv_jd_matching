"""
Migration script to add BatchJob table.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import create_engine, SQLModel
from core.db.models import BatchJob
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database URL
DATABASE_URL = "postgresql://postgres:postgres@db:5432/cv_matching"

def migrate():
    """Add BatchJob table."""
    engine = create_engine(DATABASE_URL, echo=True)
    
    try:
        logger.info("Starting database migration...")
        
        # Create BatchJob table
        logger.info("Creating BatchJob table...")
        BatchJob.metadata.create_all(engine)
        
        logger.info("Migration completed successfully!")
        logger.info("New BatchJob table created")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise

if __name__ == "__main__":
    migrate()
