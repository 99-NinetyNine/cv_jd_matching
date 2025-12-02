"""
Shared service for job processing operations.
Handles embedding computation and caching for job postings.
"""
from typing import Dict, Any, Optional
from sqlmodel import Session
import logging
import uuid

from core.db.models import Job

logger = logging.getLogger(__name__)


def get_job_text_representation(job_data: Dict[str, Any]) -> str:
    """Convert job data to text representation for embedding."""
    text = ""
    
    # Core fields
    text += f"Title: {job_data.get('title', '')} "
    text += f"Role: {job_data.get('role', '')} " if job_data.get('role') else ""
    text += f"Company: {job_data.get('company', '')} "
    text += f"Description: {job_data.get('description', '')} "
    
    # Requirements
    if job_data.get('experience'):
        text += f"Experience: {job_data['experience']} "
    
    # Handle qualifications (can be str or List[str])
    if job_data.get('qualifications'):
        quals = job_data['qualifications']
        if isinstance(quals, list):
            text += f"Qualifications: {', '.join(quals)} "
        else:
            text += f"Qualifications: {quals} "
    
    # Handle skills (can be List[str] or List[Dict])
    if job_data.get('skills'):
        skills = job_data['skills']
        if skills and isinstance(skills[0], dict):
            # Extract skill names from structured skills
            skill_names = [s.get('name', '') for s in skills if s.get('name')]
            text += f"Skills: {', '.join(skill_names)} "
        elif isinstance(skills, list):
            text += f"Skills: {', '.join(skills)} "
    
    # Handle location (can be str or Dict)
    location = job_data.get('location')
    if location:
        if isinstance(location, dict):
            # Structured location
            city = location.get('city', '')
            country = location.get('countryCode', '')
            if city:
                text += f"Location: {city}"
                if country:
                    text += f", {country} "
        else:
            # Simple string location
            text += f"Location: {location}"
            if job_data.get('country'):
                text += f", {job_data['country']} "
    
    # Additional details
    work_type = job_data.get('type') or job_data.get('work_type')
    if work_type:
        text += f"Work Type: {work_type} "
    
    salary = job_data.get('salary') or job_data.get('salary_range')
    if salary:
        text += f"Salary: {salary} "
    
    if job_data.get('responsibilities'):
        text += f"Responsibilities: {', '.join(job_data['responsibilities'])} "
    
    if job_data.get('benefits'):
        text += f"Benefits: {', '.join(job_data['benefits'])} "
    
    if job_data.get('remote'):
        text += f"Remote: {job_data['remote']} "
    
    return text.strip()
