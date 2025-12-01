from typing import Optional, List, Dict
from sqlmodel import SQLModel, Field, create_engine, Session, JSON
from pgvector.sqlalchemy import Vector
from sqlalchemy import Column
from datetime import datetime

class CV(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: Optional[int] = Field(default=None, foreign_key="user.id")
    filename: str
    content: Dict = Field(default={}, sa_column=Column(JSON))
    embedding: List[float] = Field(default=None, sa_column=Column(Vector(768)))
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Job(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: str = Field(unique=True)
    owner_id: Optional[int] = Field(default=None, foreign_key="user.id")
    
    # Core fields
    title: str
    role: Optional[str] = None
    company: str
    description: str
    
    # Requirements
    experience: Optional[str] = None  # e.g., "5 to 10 Years"
    qualifications: Optional[str] = None  # e.g., "BBA, MBA"
    skills: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))
    
    # Compensation & Benefits
    salary_range: Optional[str] = None  # e.g., "$55K-$84K"
    benefits: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))
    
    # Location
    location: Optional[str] = None  # City
    country: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    
    # Job Details
    work_type: Optional[str] = None  # Contract, Full-Time, Part-Time
    company_size: Optional[int] = None
    job_posting_date: Optional[datetime] = None
    
    # Additional Info
    preference: Optional[str] = None  # e.g., "Male", "Female", "Any"
    contact_person: Optional[str] = None
    contact: Optional[str] = None
    job_portal: Optional[str] = None
    responsibilities: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))
    company_profile: Optional[Dict] = Field(default=None, sa_column=Column(JSON))
    
    # Embedding
    embedding: List[float] = Field(default=None, sa_column=Column(Vector(768)))
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Feedback(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: str
    cv_filename: str
    score: int = Field(description="1 to 5 rating")
    comment: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ExternalProfile(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    url: str = Field(unique=True, index=True)
    platform: str # linkedin, github
    content: Dict = Field(default={}, sa_column=Column(JSON))
    last_fetched: datetime = Field(default_factory=datetime.utcnow)

class ParsingCorrection(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    cv_id: str
    original_data: Dict = Field(default={}, sa_column=Column(JSON))
    corrected_data: Dict = Field(default={}, sa_column=Column(JSON))
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    password_hash: str
    role: str = Field(default="candidate") # candidate, hirer, admin
    is_admin: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class SystemMetric(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True) # e.g., "db_query_latency", "llm_response_time"
    value: float
    tags: Dict = Field(default={}, sa_column=Column(JSON)) # e.g., {"operation": "match", "model": "llama3"}
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class UserInteraction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    job_id: str
    action: str # "viewed", "applied", "saved", "shortlisted", "interviewed", "hired", "rejected"
    strategy: Optional[str] = Field(default="pgvector") # "naive", "pgvector"
    interaction_metadata: Optional[Dict] = Field(default=None, sa_column=Column(JSON))  # prediction_id, cv_id, application_id
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class Application(SQLModel, table=True):
    """Track job applications from candidates."""
    id: Optional[int] = Field(default=None, primary_key=True)
    cv_id: str  # Candidate's CV ID
    job_id: str = Field(foreign_key="job.job_id")
    prediction_id: str  # Links to the prediction session that led to this application
    status: str = Field(default="pending")  # pending, accepted, rejected
    applied_at: datetime = Field(default_factory=datetime.utcnow)
    decision_at: Optional[datetime] = None
    decided_by: Optional[int] = Field(default=None, foreign_key="user.id")
    notes: Optional[str] = None

# Engine creation
# database_url = "postgresql://postgres:postgres@localhost:5432/cv_matching"
# engine = create_engine(database_url)

