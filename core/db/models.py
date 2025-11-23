from typing import Optional, List, Dict
from sqlmodel import SQLModel, Field, create_engine, Session, JSON
from pgvector.sqlalchemy import Vector
from sqlalchemy import Column
from datetime import datetime

class CV(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    filename: str
    content: Dict = Field(default={}, sa_column=Column(JSON))
    embedding: List[float] = Field(default=None, sa_column=Column(Vector(768)))

class Job(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: str = Field(unique=True)
    title: str
    company: str
    description: str
    embedding: List[float] = Field(default=None, sa_column=Column(Vector(768)))

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
    action: str # "click", "apply", "dismiss"
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# Engine creation
# database_url = "postgresql://postgres:postgres@localhost:5432/cv_matching"
# engine = create_engine(database_url)
