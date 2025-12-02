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
