import sys
import os

# Add the parent directory to sys.path to allow importing from core
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db.engine import create_db_and_tables, destroy_db_and_tables

# Import all models to register them with SQLModel metadata
from core.db.models import (
    User, CV, Job, Prediction, UserInteraction, 
    Application, Feedback, ExternalProfile, ParsingCorrection,
    BatchRequest
)

# RESETS everything
# TODO: in future, use of alembic or django is recommended to manage migrations

if __name__ == "__main__":
    print("Destroying tables...")
    destroy_db_and_tables()
    print("Creating tables...")
    
    create_db_and_tables()
    print("Tables created successfully!")

