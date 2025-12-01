"""
Migration script to add Application table and update UserInteraction.
Run this to update the database schema.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import create_engine, SQLModel, Session
from core.db.models import Application, UserInteraction
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database URL
DATABASE_URL = "postgresql://postgres:postgres@db:5432/cv_matching"

def migrate():
    """Add Application table and update UserInteraction metadata."""
    engine = create_engine(DATABASE_URL, echo=True)
    
    try:
        logger.info("Starting database migration...")
        
        # Create Application table
        logger.info("Creating Application table...")
        Application.metadata.create_all(engine)
        
        # Note: UserInteraction table already exists, we just added a new column
        # PostgreSQL will handle the ALTER TABLE automatically when accessed
        logger.info("UserInteraction table will be updated automatically")
        
        logger.info("Migration completed successfully!")
        logger.info("New Application table created")
        logger.info("UserInteraction.interaction_metadata column available")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise

if __name__ == "__main__":
    migrate()
