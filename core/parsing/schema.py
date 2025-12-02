from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, HttpUrl, EmailStr

class Location(BaseModel):
    address: Optional[str] = ""
    postalCode: Optional[str] = ""
    city: Optional[str] = ""
    countryCode: Optional[str] = ""
    region: Optional[str] = ""

class Profile(BaseModel):
    network: Optional[str] = ""
    username: Optional[str] = ""
    url: Optional[str] = ""

class Basics(BaseModel):
    name: Optional[str] = ""
    label: Optional[str] = ""
    image: Optional[str] = ""
    email: Optional[str] = ""
    phone: Optional[str] = ""
    url: Optional[str] = ""
    summary: Optional[str] = ""
    location: Optional[Location] = Field(default_factory=Location)
    profiles: List[Profile] = Field(default_factory=list)

class Work(BaseModel):
    name: Optional[str] = ""
    position: Optional[str] = ""
    url: Optional[str] = ""
    startDate: Optional[str] = ""
    endDate: Optional[str] = ""
    summary: Optional[str] = ""
    highlights: List[str] = Field(default_factory=list)

class Volunteer(BaseModel):
    organization: Optional[str] = ""
    position: Optional[str] = ""
    url: Optional[str] = ""
    startDate: Optional[str] = ""
    endDate: Optional[str] = ""
    summary: Optional[str] = ""
    highlights: List[str] = Field(default_factory=list)

class Education(BaseModel):
    institution: Optional[str] = ""
    url: Optional[str] = ""
    area: Optional[str] = ""
    studyType: Optional[str] = ""
    startDate: Optional[str] = ""
    endDate: Optional[str] = ""
    score: Optional[str] = ""
    courses: List[str] = Field(default_factory=list)

class Award(BaseModel):
    title: Optional[str] = ""
    date: Optional[str] = ""
    awarder: Optional[str] = ""
    summary: Optional[str] = ""

class Certificate(BaseModel):
    name: Optional[str] = ""
    date: Optional[str] = ""
    issuer: Optional[str] = ""
    url: Optional[str] = ""

class Publication(BaseModel):
    name: Optional[str] = ""
    publisher: Optional[str] = ""
    releaseDate: Optional[str] = ""
    url: Optional[str] = ""
    summary: Optional[str] = ""

class Skill(BaseModel):
    name: Optional[str] = ""
    level: Optional[str] = ""
    keywords: List[str] = Field(default_factory=list)

class Language(BaseModel):
    language: Optional[str] = ""
    fluency: Optional[str] = ""

class Interest(BaseModel):
    name: Optional[str] = ""
    keywords: List[str] = Field(default_factory=list)

class Reference(BaseModel):
    name: Optional[str] = ""
    reference: Optional[str] = ""

class Project(BaseModel):
    name: Optional[str] = ""
    startDate: Optional[str] = ""
    endDate: Optional[str] = ""
    description: Optional[str] = ""
    highlights: List[str] = Field(default_factory=list)
    url: Optional[str] = ""

class Resume(BaseModel):
    basics: Optional[Basics] = Field(default_factory=Basics)
    work: List[Work] = Field(default_factory=list)
    volunteer: List[Volunteer] = Field(default_factory=list)
    education: List[Education] = Field(default_factory=list)
    awards: List[Award] = Field(default_factory=list)
    certificates: List[Certificate] = Field(default_factory=list)
    publications: List[Publication] = Field(default_factory=list)
    skills: List[Skill] = Field(default_factory=list)
    languages: List[Language] = Field(default_factory=list)
    interests: List[Interest] = Field(default_factory=list)
    references: List[Reference] = Field(default_factory=list)
    projects: List[Project] = Field(default_factory=list)


# Job Description Schema (compliant with Job Description JSON Schema)
class JobCreate(BaseModel):
    """
    Canonical job schema compliant with Job Description JSON Schema.
    Based on: http://json-schema.org/draft-04/schema#
    """
    # Required fields
    title: str  # e.g., "Web Developer"
    company: str  # e.g., "Microsoft"
    description: str

    # Optional fields following the JSON schema
    type: Optional[str] = None  # Full-time, part-time, contract, etc.
    date: Optional[str] = None  # ISO 8601: YYYY-MM-DD or YYYY-MM or YYYY
    location: Optional[Location] = Field(default_factory=Location)
    remote: Optional[str] = None  # Full, Hybrid, None
    salary: Optional[str] = None  # e.g., "100000"
    experience: Optional[str] = None  # Senior, Junior, Mid-level, or "5+ years"
    responsibilities: List[str] = Field(default_factory=list)
    qualifications: List[str] = Field(default_factory=list)
    skills: List[Skill] = Field(default_factory=list)  # Structured skills with name, level, keywords

    # Extended fields for backward compatibility with existing DB
    job_id: Optional[str] = None
    role: Optional[str] = None
    salary_range: Optional[str] = None
    benefits: Optional[List[str]] = None
    work_type: Optional[str] = None
    company_size: Optional[int] = None
    job_posting_date: Optional[str] = None
    preference: Optional[str] = None
    contact_person: Optional[str] = None
    contact: Optional[str] = None
    job_portal: Optional[str] = None
    company_profile: Optional[Dict[str, Any]] = None
    country: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
