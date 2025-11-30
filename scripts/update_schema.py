import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError

# Add parent directory to path to import core modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Get database URL from env or default
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/cv_matching")

def update_schema():
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        conn.execution_options(isolation_level="AUTOCOMMIT")
        
        print("Updating 'cv' table...")
        # Add owner_id to cv table
        try:
            conn.execute(text("ALTER TABLE cv ADD COLUMN IF NOT EXISTS owner_id INTEGER REFERENCES \"user\"(id);"))
            print("Added owner_id to cv")
        except Exception as e:
            print(f"Error adding owner_id to cv: {e}")

        try:
            conn.execute(text("ALTER TABLE cv ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (now() at time zone 'utc');"))
            print("Added created_at to cv")
        except Exception as e:
            print(f"Error adding created_at to cv: {e}")

        print("Updating 'job' table...")
        # Add owner_id to job table
        try:
            conn.execute(text("ALTER TABLE job ADD COLUMN IF NOT EXISTS owner_id INTEGER REFERENCES \"user\"(id);"))
            print("Added owner_id to job")
        except Exception as e:
            print(f"Error adding owner_id to job: {e}")

        # Add new job fields
        new_columns = [
            ("role", "VARCHAR"),
            ("experience", "VARCHAR"),
            ("qualifications", "VARCHAR"),
            ("skills", "JSON"),
            ("salary_range", "VARCHAR"),
            ("benefits", "JSON"),
            ("location", "VARCHAR"),
            ("country", "VARCHAR"),
            ("latitude", "FLOAT"),
            ("longitude", "FLOAT"),
            ("work_type", "VARCHAR"),
            ("company_size", "INTEGER"),
            ("job_posting_date", "TIMESTAMP WITHOUT TIME ZONE"),
            ("preference", "VARCHAR"),
            ("contact_person", "VARCHAR"),
            ("contact", "VARCHAR"),
            ("job_portal", "VARCHAR"),
            ("responsibilities", "JSON"),
            ("company_profile", "JSON"),
            ("created_at", "TIMESTAMP WITHOUT TIME ZONE DEFAULT (now() at time zone 'utc')")
        ]

        for col_name, col_type in new_columns:
            try:
                conn.execute(text(f"ALTER TABLE job ADD COLUMN IF NOT EXISTS {col_name} {col_type};"))
                print(f"Added {col_name} to job")
            except Exception as e:
                print(f"Error adding {col_name} to job: {e}")
                
    print("Schema update complete.")

if __name__ == "__main__":
    update_schema()
