import sys
import os

# Add the parent directory to sys.path to allow importing from core
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db.engine import create_db_and_tables, destroy_db_and_tables
from core.db import models # Import models to register them with SQLModel

if __name__ == "__main__":
    print("destroying tables...")
    destroy_db_and_tables()
    print("Creating tables...")
    
    create_db_and_tables()
    print("Tables created.")
