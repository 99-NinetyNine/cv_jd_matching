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

# Engine creation
# database_url = "postgresql://postgres:postgres@localhost:5432/cv_matching"
# engine = create_engine(database_url)
