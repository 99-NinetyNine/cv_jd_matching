from typing import List, Optional
from pydantic import BaseModel, Field

class Location(BaseModel):
    city: Optional[str] = None
    countryCode: Optional[str] = None
    region: Optional[str] = None

class Basics(BaseModel):
    name: Optional[str] = None
    label: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    url: Optional[str] = None
    summary: Optional[str] = None
    location: Optional[Location] = None
    profiles: List[dict] = Field(default_factory=list)

class Work(BaseModel):
    name: Optional[str] = Field(None, alias="company")
    position: Optional[str] = None
    url: Optional[str] = None
    company: Optional[str] = Field(description="Company name")
    position: Optional[str] = Field(description="Position title")
    url: Optional[str] = None
    startDate: Optional[str] = Field(description="Start date YYYY-MM")
    endDate: Optional[str] = Field(description="End date YYYY-MM")
    summary: Optional[str] = Field(description="Summary of responsibilities")
    highlights: Optional[List[str]] = Field(description="Key achievements")

class Education(BaseModel):
    institution: Optional[str] = Field(description="Name of the institution")
    url: Optional[str] = None
    area: Optional[str] = Field(description="Area of study")
    studyType: Optional[str] = Field(description="Type of degree")
    startDate: Optional[str] = Field(description="Start date YYYY-MM")
    endDate: Optional[str] = Field(description="End date YYYY-MM")
    score: Optional[str] = Field(description="Grade or GPA")
    percentage: Optional[float] = Field(description="Percentage score if applicable")
    courses: List[str] = Field(default_factory=list)

class Skill(BaseModel):
    name: Optional[str] = None
    level: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)

class Language(BaseModel):
    language: Optional[str] = None
    fluency: Optional[str] = None

class Project(BaseModel):
    name: str
    description: Optional[str]
    url: Optional[str]

class Resume(BaseModel):
    basics: Optional[Basics] = Field(description="Basic information")
    work: Optional[List[Work]] = Field(description="Work experience")
    education: Optional[List[Education]] = Field(description="Education history")
    skills: Optional[List[Skill]] = Field(description="Skills")
    languages: Optional[List[Language]] = Field(description="Languages")
    projects: Optional[List[Project]] = Field(description="Projects")
    year_gap_duration: Optional[float] = Field(description="Total duration of career gaps in years")
    interests: List[dict] = Field(default_factory=list)
    references: List[dict] = Field(default_factory=list)
