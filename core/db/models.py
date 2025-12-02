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

    # Statuses for different processing stages
    parsing_status: str = Field(default="pending") # pending, pending_batch, processing, completed, failed
    embedding_status: str = Field(default="pending") # pending, pending_batch, processing, completed, failed

    is_latest: bool = Field(default=True)
    last_analyzed: Optional[datetime] = Field(default=None)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Batch processing metadata
    batch_id: Optional[str] = None  # Links to batch job if processed in batch

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
    embedding_status: str = Field(default="completed") # pending, pending_batch, processing, completed, failed
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Optimized fields for retrieval
    canonical_text: Optional[str] = None  # Pre-computed text representation
    data: Optional[Dict] = Field(default=None, sa_column=Column(JSON))  # Complete job data as JSON
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
    is_premium: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_cv_analyzed: Optional[datetime] = None

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

class BatchJob(SQLModel, table=True):
    """Track batch processing jobs."""
    id: Optional[int] = Field(default=None, primary_key=True)
    batch_id: str = Field(unique=True, index=True)
    type: str = "cv_bulk_upload"
    status: str = "pending"  # pending, processing, completed, failed
    total_items: int = 0
    processed_items: int = 0
    results: Optional[Dict] = Field(default={}, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    error: Optional[str] = None

class BatchRequest(SQLModel, table=True):
    """Track OpenAI Batch API requests."""
    id: Optional[int] = Field(default=None, primary_key=True)
    batch_api_id: str = Field(unique=True, index=True) # OpenAI Batch ID (batch_abc123)
    input_file_id: str # OpenAI File ID (file-abc123)
    output_file_id: Optional[str] = None
    error_file_id: Optional[str] = None
    
    status: str = "validating" # validating, failed, in_progress, finalizing, completed, expired, cancelling, cancelled
    request_counts: Optional[Dict] = Field(default={}, sa_column=Column(JSON)) # {total, completed, failed}
    batch_metadata: Optional[Dict] = Field(default={}, sa_column=Column(JSON))
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    # Type of batch: 'embedding', 'explanation', etc.
    batch_type: str = "embedding"

class Prediction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    prediction_id: str = Field(unique=True, index=True)
    cv_id: str = Field(index=True)
    matches: List[Dict] = Field(default=[], sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)

# Engine creation
# database_url = "postgresql://postgres:postgres@localhost:5432/cv_matching"
# engine = create_engine(database_url)

