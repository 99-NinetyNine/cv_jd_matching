"""
Response models for API endpoints.
These models define the structure of API responses for FastAPI documentation.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


# Job-related responses
class JobCreateResponse(BaseModel):
    """Response model for job creation."""
    status: str = Field(description="Status message")
    job_id: str = Field(description="Unique identifier of the created job")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "status": "Job created successfully",
                "job_id": "550e8400-e29b-41d4-a716-446655440000"
            }]
        }
    }


class JobResponse(BaseModel):
    """Response model for single job retrieval."""
    job_id: str
    title: str
    company: str
    description: str
    type: Optional[str] = None
    location: Optional[Dict] = None
    remote: Optional[str] = None
    salary: Optional[str] = None
    experience: Optional[str] = None
    skills: Optional[List[Dict]] = None
    embedding_status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class JobListResponse(BaseModel):
    """Response model for job listing."""
    jobs: List[JobResponse] = Field(description="List of jobs")
    count: int = Field(description="Total number of jobs")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "jobs": [],
                "count": 0
            }]
        }
    }


class JobDeleteResponse(BaseModel):
    """Response model for job deletion."""
    status: str = Field(description="Status message")
    job_id: str = Field(description="ID of the deleted job")


# CV/Candidate-related responses
class CVUploadResponse(BaseModel):
    """Response model for CV upload."""
    cv_id: str = Field(description="Unique CV identifier")
    filename: str = Field(description="Uploaded filename")
    path: str = Field(description="Storage path")


class CVParseResponse(CVUploadResponse):
    """Response model for CV parsing."""
    data: Dict = Field(description="Parsed CV data in JSON Resume format")


class JobMatchResult(BaseModel):
    """Individual job match result."""
    job_id: str = Field(description="Job identifier")
    title: str = Field(description="Job title")
    company: str = Field(description="Company name")
    match_score: float = Field(description="Match score (0-1)", ge=-1.0, le=1.0)
    similarity: float = Field(description="Semantic similarity score", ge=-1, le=1)
    explanation: Optional[str] = Field(None, description="Match explanation")
    skills_match: Optional[Dict] = Field(None, description="Skills matching details")


class RecommendationsResponse(BaseModel):
    """Response model for job recommendations."""
    status: str = Field(default="complete", description="Processing status")
    candidate_id: str = Field(description="CV identifier")
    candidate_name: str = Field(description="Candidate name extracted from CV")
    recommendations: List[JobMatchResult] = Field(description="List of matched jobs")
    prediction_id: str = Field(description="Unique prediction session ID")
    cv_id: str = Field(description="CV identifier")
    count: int = Field(description="Number of recommendations", ge=0)

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "status": "complete",
                "candidate_id": "abc-123",
                "candidate_name": "John Doe",
                "recommendations": [
                    {
                        "job_id": "job-1",
                        "title": "Senior Developer",
                        "company": "TechCorp",
                        "match_score": 0.92,
                        "similarity": 0.88
                    }
                ],
                "prediction_id": "pred-456",
                "cv_id": "abc-123",
                "count": 1
            }]
        }
    }


# Application-related responses
class CandidateInfo(BaseModel):
    """Candidate information from CV."""
    name: str
    email: str
    summary: str
    skills: List[Any]
    work: List[Dict]


class ApplicationDetail(BaseModel):
    """Detailed application information."""
    id: int
    cv_id: str
    job_id: str
    prediction_id: str
    status: str
    applied_at: datetime
    decision_at: Optional[datetime]
    decided_by: Optional[int]
    notes: Optional[str]
    candidate: Optional[CandidateInfo]


class JobApplicationsResponse(BaseModel):
    """Response model for job applications listing."""
    job_id: str = Field(description="Job identifier")
    job_title: str = Field(description="Job title")
    applications: List[ApplicationDetail] = Field(description="List of applications")
    count: int = Field(description="Total number of applications")


# Admin-related responses
class BatchTriggerResponse(BaseModel):
    """Response for batch trigger operations."""
    status: str
    message: str
    batch_id: Optional[str] = None
    task_id: Optional[str] = None


class SystemHealthResponse(BaseModel):
    """System health status response."""
    status: str = Field(description="Overall system status: healthy, degraded, or error")
    timestamp: str = Field(description="ISO timestamp of health check")
    components: Dict[str, str] = Field(description="Individual component statuses")
    pending_work: Dict[str, int] = Field(description="Count of pending work items")
    recent_failures: int = Field(description="Number of recent failures")


# Generic responses
class ErrorResponse(BaseModel):
    """Standard error response."""
    detail: str = Field(description="Error message")


class SuccessResponse(BaseModel):
    """Generic success response."""
    status: str = Field(description="Success status message")
    message: Optional[str] = Field(None, description="Additional information")
