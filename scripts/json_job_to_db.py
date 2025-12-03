import sys
import os
import json
import glob
from pathlib import Path
from typing import Dict, Any

# Add the parent directory to sys.path to allow importing from core
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, select
from core.db.engine import engine
from core.db.models import Job, User
from core.services.job_service import get_job_text_representation
from core.auth.security import get_password_hash

def get_or_create_owner(session: Session) -> int:
    """Get an existing hirer/admin or create a default one."""
    # Try to find a hirer first
    user = session.exec(select(User).where(User.role == "hirer")).first()
    if user:
        return user.id
    
    # Try admin
    user = session.exec(select(User).where(User.role == "admin")).first()
    if user:
        return user.id
        
    # Create a default hirer
    print("Creating default hirer user...")
    default_email = "hirer@example.com"
    default_password = "password123"
    
    user = User(
        email=default_email,
        password_hash=get_password_hash(default_password),
        role="hirer",
        is_admin=False
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    print(f"Created user {default_email} with ID {user.id}")
    return user.id

def import_jobs():
    """Import jobs from JSON files in tests/test_job_desc/"""
    
    # Path to JSON files
    base_dir = Path(__file__).parent.parent
    json_dir = base_dir / "tests" / "test_job_desc"
    
    if not json_dir.exists():
        print(f"Directory not found: {json_dir}")
        return

    json_files = list(json_dir.glob("*.json"))
    print(f"Found {len(json_files)} JSON files in {json_dir}")

    with Session(engine) as session:
        owner_id = get_or_create_owner(session)
        
        imported_count = 0
        skipped_count = 0
        
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                job_id = data.get("job_id")
                if not job_id:
                    print(f"Skipping {json_file.name}: No job_id found")
                    continue
                
                # Check if job already exists
                existing_job = session.exec(select(Job).where(Job.job_id == job_id)).first()
                if existing_job:
                    print(f"Skipping {job_id}: Already exists")
                    skipped_count += 1
                    continue
                
                # Prepare job data
                # We need to handle nested dictionaries like location, skills, company_profile
                # The Job model expects these as JSON fields (if defined as such) or flattened?
                # Let's check Job model definition again.
                # Job model has 'location' as JSON? No, let's check models.py again.
                # Wait, I saw models.py earlier. 
                # Job model has:
                # location: Optional[Dict] = Field(default=None, sa_column=Column(JSON))
                # skills: List[Dict] = Field(default=[], sa_column=Column(JSON))
                # company_profile: Optional[Dict] = Field(default=None, sa_column=Column(JSON))
                # So we can pass dicts directly.
                
                # Clean up data to match Job model fields
                # We can filter keys that are in the Job model, or just pass **data if we are sure.
                # But data might contain extra fields.
                # Safer to rely on SQLModel to ignore extras? No, it might error.
                # Let's just pass what we have, assuming JSONs match schema.
                
                # Calculate canonical text
                text_rep = get_job_text_representation(data)
                
                job = Job(
                    job_id=job_id,
                    owner_id=owner_id,
                    title=data.get("title"),
                    company=data.get("company"),
                    description=data.get("description"),
                    type=data.get("type"),
                    date=data.get("date"),
                    location=data.get("location"),
                    remote=data.get("remote"),
                    salary=data.get("salary"),
                    experience=data.get("experience"),
                    responsibilities=data.get("responsibilities"),
                    qualifications=data.get("qualifications"),
                    skills=data.get("skills"),
                    role=data.get("role"),
                    salary_range=data.get("salary_range"),
                    benefits=data.get("benefits"),
                    company_size=data.get("company_size"),
                    job_posting_date=data.get("job_posting_date"),
                    preference=data.get("preference"),
                    contact_person=data.get("contact_person"),
                    contact=data.get("contact"),
                    job_portal=data.get("job_portal"),
                    company_profile=data.get("company_profile"),
                    country=data.get("country"),
                    latitude=data.get("latitude"),
                    longitude=data.get("longitude"),
                    
                    embedding_status="pending_batch", # Mark for batch processing
                    canonical_text=text_rep
                )
                
                session.add(job)
                imported_count += 1
                print(f"Imported job: {job_id} - {job.title}")
                
            except Exception as e:
                print(f"Error importing {json_file.name}: {e}")
        
        session.commit()
        print(f"\nImport finished.")
        print(f"Imported: {imported_count}")
        print(f"Skipped: {skipped_count}")

if __name__ == "__main__":
    import_jobs()
