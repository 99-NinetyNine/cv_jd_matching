"""
Migration script to add missing columns to user table.
"""
import sys
import os

# Add the parent directory to sys.path to allow importing from core
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from core.db.engine import engine

def add_missing_user_columns():
    """Add missing columns to user table if they don't exist."""
    
    with engine.connect() as conn:
        # Check and add is_premium column
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='user' AND column_name='is_premium'
        """))
        
        if not result.fetchone():
            print("Adding 'is_premium' column to 'user' table...")
            conn.execute(text("""
                ALTER TABLE "user" 
                ADD COLUMN is_premium BOOLEAN DEFAULT FALSE NOT NULL
            """))
            conn.commit()
            print("Column 'is_premium' added successfully!")
        else:
            print("Column 'is_premium' already exists in 'user' table.")
        
        # Check and add last_cv_analyzed column
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='user' AND column_name='last_cv_analyzed'
        """))
        
        if not result.fetchone():
            print("Adding 'last_cv_analyzed' column to 'user' table...")
            conn.execute(text("""
                ALTER TABLE "user" 
                ADD COLUMN last_cv_analyzed TIMESTAMP
            """))
            conn.commit()
            print("Column 'last_cv_analyzed' added successfully!")
        else:
            print("Column 'last_cv_analyzed' already exists in 'user' table.")

if __name__ == "__main__":
    add_missing_user_columns()
