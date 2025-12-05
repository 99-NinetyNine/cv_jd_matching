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
    # Dimension supports OpenAI (1536), Gemini (768), Ollama (768-1024)
    # OpenAI text-embedding-3-small/large use 1536 dimensions
    embedding: List[float] = Field(default=None, sa_column=Column(Vector(1536)))

    # Statuses for different processing stages
    parsing_status: str = Field(default="pending") # pending, pending_batch, processing, completed, failed
    embedding_status: str = Field(default="pending") # pending, pending_batch, processing, completed, failed

    is_latest: bool = Field(default=True)
    last_analyzed: Optional[datetime] = Field(default=None)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Batch processing metadata
    batch_id: Optional[str] = None  # Links to batch job if processed in batch

    # Optimized fields for retrieval (like Job model)
    canonical_text: Optional[str] = None  # Pre-computed text representation

class Job(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: str = Field(unique=True)
    owner_id: Optional[int] = Field(default=None, foreign_key="user.id")

    # Core fields (matching JobCreate)
    title: str
    company: str
    description: str

    # Optional fields (matching JobCreate)
    type: Optional[str] = None  # Full-time, part-time, contract, etc.
    date: Optional[str] = None  # ISO 8601: YYYY-MM-DD or YYYY-MM or YYYY
    location: Optional[Dict] = Field(default=None, sa_column=Column(JSON))  # Location object {address, postalCode, city, countryCode, region}
    remote: Optional[str] = None  # Full, Hybrid, None
    salary: Optional[str] = None  # e.g., "100000"
    experience: Optional[str] = None  # Senior, Junior, Mid-level, or "5+ years"
    responsibilities: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))
    qualifications: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))
    skills: Optional[List[Dict]] = Field(default=None, sa_column=Column(JSON))  # Skill objects {name, level, keywords}

    # Extended fields (matching JobCreate extended fields)
    role: Optional[str] = None
    salary_range: Optional[str] = None
    benefits: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))
    company_size: Optional[int] = None
    job_posting_date: Optional[str] = None  # Changed to str to match JobCreate
    preference: Optional[str] = None
    contact_person: Optional[str] = None
    contact: Optional[str] = None
    job_portal: Optional[str] = None
    company_profile: Optional[Dict] = Field(default=None, sa_column=Column(JSON))
    country: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    
    # Embedding and metadata (DB-specific fields)
    # Dimension supports OpenAI (1536), Gemini (768), Ollama (768-1024)
    # OpenAI text-embedding-3-small/large use 1536 dimensions
    embedding: List[float] = Field(default=None, sa_column=Column(Vector(1536)))
    embedding_status: str = Field(default="completed") # pending, pending_batch, processing, completed, failed
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Optimized fields for retrieval
    canonical_text: Optional[str] = None  # Pre-computed text representation
    canonical_json: Optional[Dict] = Field(default=None, sa_column=Column(JSON)) 
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

    created_at: datetime = Field(default_factory=datetime.utcnow)  # Batch submission time
    completed_at: Optional[datetime] = None  # Batch completion time (runtime = completed_at - created_at)

    # Type of batch: 'embedding', 'explanation', etc.
    batch_type: str = "embedding"

class Prediction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    prediction_id: str = Field(unique=True, index=True)
    cv_id: str = Field(index=True)
    matches: List[Dict] = Field(default=[], sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Generation time tracking
    matching_completed_at: Optional[datetime] = Field(default=None)  # When matches were generated
    explanation_completed_at: Optional[datetime] = Field(default=None)  # When explanations were added
    is_first_prediction: bool = Field(default=False)  # True if this is the CV's first prediction

# Engine creation
# database_url = "postgresql://postgres:postgres@localhost:5432/cv_matching"
# engine = create_engine(database_url)

