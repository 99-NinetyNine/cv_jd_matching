"""
Matching Factors Calculator - Domain Agnostic

Calculates detailed matching scores between CV and job across multiple dimensions using
structured JSON schemas. Works for ALL domains by leveraging schema-defined fields.

Matching dimensions:
- Skills match (from SkillsAnalyzer)
- Experience match (years, roles, relevance)
- Education match (degrees, fields, certifications)
- Semantic similarity (from embeddings)
"""

from typing import Dict, Any, Optional, List, Set
import re
from datetime import datetime


class MatchingFactorsCalculator:
    """Domain-agnostic matching factors calculator using structured schemas."""

    def __init__(self):
        """Initialize the matching factors calculator."""
        pass

    def calculate_experience_match(
        self,
        cv_data: Dict[str, Any],
        job_data: Dict[str, Any]
    ) -> float:
        """
        Calculate experience match score (0.0 to 1.0) using schema fields.

        Uses:
        - CV: work[] array (startDate, endDate, position, name)
        - Job: experience field (e.g., "Senior", "5+ years")

        Args:
            cv_data: Parsed CV data (JSON Resume format)
            job_data: Job data (Job Description Schema format)

        Returns:
            Experience match score (0.0 to 1.0)
        """
        score = 0.0
        factors = []

        # 1. Calculate total years of experience from CV work[] array
        cv_years = self._calculate_years_of_experience(cv_data)

        # 2. Extract required experience from job.experience field
        job_years = self._extract_required_experience(job_data)

        # 3. Compare years of experience
        if job_years is not None and cv_years is not None:
            if cv_years >= job_years:
                # Has required experience or more
                years_score = 1.0
            elif cv_years >= job_years * 0.7:
                # Close to required (70%+)
                years_score = 0.8
            elif cv_years >= job_years * 0.5:
                # Moderate experience (50%+)
                years_score = 0.6
            else:
                # Less than half required
                years_score = 0.3
            factors.append(years_score)

        # 4. Check for relevant role/position experience
        job_title = job_data.get("title", "").lower()
        job_role = job_data.get("role", "").lower()

        has_relevant_role = False
        if "work" in cv_data and isinstance(cv_data["work"], list):
            for work_item in cv_data["work"]:
                if isinstance(work_item, dict):
                    cv_position = work_item.get("position", "").lower()
                    # Keyword matching for role relevance
                    if any(keyword in cv_position for keyword in [job_title, job_role] if keyword):
                        has_relevant_role = True
                        break

        if has_relevant_role:
            factors.append(1.0)
        else:
            factors.append(0.5)  # Neutral if no exact role match

        # Calculate average
        if factors:
            score = sum(factors) / len(factors)
        else:
            score = 0.5  # Neutral if no data

        return min(1.0, max(0.0, score))

    def calculate_education_match(
        self,
        cv_data: Dict[str, Any],
        job_data: Dict[str, Any]
    ) -> float:
        """
        Calculate education match score (0.0 to 1.0) using schema fields.

        Uses:
        - CV: education[] array (studyType, area, institution)
        - CV: certificates[] array (name, issuer)
        - Job: qualifications[] array or qualifications string

        Args:
            cv_data: Parsed CV data (JSON Resume format)
            job_data: Job data (Job Description Schema format)

        Returns:
            Education match score (0.0 to 1.0)
        """
        score = 0.0
        factors = []

        # Extract education from CV
        cv_education = cv_data.get("education", [])
        if not isinstance(cv_education, list):
            cv_education = []

        # Extract certificates from CV (important for all domains)
        cv_certificates = cv_data.get("certificates", [])
        if not isinstance(cv_certificates, list):
            cv_certificates = []

        # Extract required qualifications from job
        job_qualifications = self._extract_qualifications_list(job_data)

        # 1. Check degree level match
        degree_levels = {
            "phd": 5, "doctorate": 5, "doctoral": 5,
            "master": 4, "masters": 4, "mba": 4, "msc": 4, "ma": 4,
            "bachelor": 3, "bachelors": 3, "undergraduate": 3, "bsc": 3, "ba": 3, "bba": 3,
            "associate": 2, "associates": 2,
            "diploma": 1, "certificate": 1, "certification": 1
        }

        cv_max_level = 0
        for edu in cv_education:
            if isinstance(edu, dict):
                degree = edu.get("studyType", "").lower()
                area = edu.get("area", "").lower()

                for level_name, level_value in degree_levels.items():
                    if level_name in degree or level_name in area:
                        cv_max_level = max(cv_max_level, level_value)

        # Also check certificates for degree-equivalent certifications
        for cert in cv_certificates:
            if isinstance(cert, dict):
                cert_name = cert.get("name", "").lower()
                for level_name, level_value in degree_levels.items():
                    if level_name in cert_name:
                        cv_max_level = max(cv_max_level, level_value)

        # Check if job requires specific degree level
        required_level = 0
        for qual in job_qualifications:
            qual_lower = qual.lower()
            for level_name, level_value in degree_levels.items():
                if level_name in qual_lower:
                    required_level = max(required_level, level_value)

        if required_level > 0:
            if cv_max_level >= required_level:
                factors.append(1.0)
            elif cv_max_level >= required_level - 1:
                factors.append(0.8)
            else:
                factors.append(0.5)
        else:
            # No specific requirement, give credit for having education
            if cv_max_level > 0:
                factors.append(0.8)
            else:
                factors.append(0.5)

        # 2. Check field of study/certification relevance
        # Extract keywords from job requirements
        job_keywords = self._extract_education_keywords(job_data)

        has_relevant_field = False

        # Check education areas
        for edu in cv_education:
            if isinstance(edu, dict):
                area = edu.get("area", "").lower()
                if any(keyword in area for keyword in job_keywords if len(keyword) > 3):
                    has_relevant_field = True
                    break

        # Check certificate names (very important for professional fields)
        if not has_relevant_field:
            for cert in cv_certificates:
                if isinstance(cert, dict):
                    cert_name = cert.get("name", "").lower()
                    if any(keyword in cert_name for keyword in job_keywords if len(keyword) > 3):
                        has_relevant_field = True
                        break

        if has_relevant_field:
            factors.append(1.0)
        else:
            factors.append(0.6)  # Slightly lower if no direct field match

        # Calculate average
        if factors:
            score = sum(factors) / len(factors)
        else:
            score = 0.5

        return min(1.0, max(0.0, score))

    def _calculate_years_of_experience(self, cv_data: Dict[str, Any]) -> Optional[float]:
        """
        Calculate total years of work experience from CV work[] array.

        Args:
            cv_data: Parsed CV data (JSON Resume format)

        Returns:
            Years of experience or None if cannot determine
        """
        if "work" not in cv_data or not cv_data["work"]:
            return None

        work_items = cv_data["work"]
        if not isinstance(work_items, list):
            return None

        total_months = 0

        for work_item in work_items:
            if not isinstance(work_item, dict):
                continue

            start_date = work_item.get("startDate")
            end_date = work_item.get("endDate", "Present")

            if not start_date:
                continue

            # Parse dates (ISO 8601: YYYY-MM-DD or YYYY-MM or YYYY)
            try:
                start_year = self._extract_year(start_date)
                if end_date and end_date.lower() not in ["present", "current", "now"]:
                    end_year = self._extract_year(end_date)
                else:
                    end_year = datetime.now().year

                if start_year and end_year:
                    years = end_year - start_year
                    total_months += years * 12
            except:
                continue

        return total_months / 12.0 if total_months > 0 else None

    def _extract_year(self, date_str: str) -> Optional[int]:
        """Extract year from ISO 8601 date string or year string."""
        if not date_str:
            return None

        # Try to find 4-digit year
        match = re.search(r'\b(19|20)\d{2}\b', str(date_str))
        if match:
            return int(match.group())
        return None

    def _extract_required_experience(self, job_data: Dict[str, Any]) -> Optional[float]:
        """
        Extract required years of experience from job.experience field.

        Args:
            job_data: Job data (Job Description Schema format)

        Returns:
            Required years or None if not specified
        """
        # Check experience field (PRIMARY SOURCE in schema)
        if "experience" in job_data and job_data["experience"]:
            exp_str = str(job_data["experience"]).lower()

            # Look for patterns like "5 years", "3-5 years", "5+ years"
            patterns = [
                r'(\d+)\s*(?:\+|plus)?\s*(?:to|-)?\s*(\d+)?\s*years?',
                r'(\d+)\s*years?'
            ]

            for pattern in patterns:
                match = re.search(pattern, exp_str)
                if match:
                    # Take the minimum if range given
                    years = int(match.group(1))
                    return float(years)

        # Fallback: check description for experience requirements
        description = job_data.get("description", "")
        if description:
            desc_lower = description.lower()
            patterns = [
                r'(\d+)\s*(?:\+|plus)?\s*years?\s+(?:of\s+)?experience',
                r'experience.*?(\d+)\s*(?:\+|plus)?\s*years?'
            ]

            for pattern in patterns:
                match = re.search(pattern, desc_lower)
                if match:
                    return float(match.group(1))

        return None

    def _extract_qualifications_list(self, job_data: Dict[str, Any]) -> List[str]:
        """
        Extract qualifications as a list from job data.

        Args:
            job_data: Job data (Job Description Schema format)

        Returns:
            List of qualification strings
        """
        qualifications = job_data.get("qualifications", [])

        if isinstance(qualifications, list):
            return [str(q) for q in qualifications if q]
        elif isinstance(qualifications, str):
            # Handle legacy string format - split by common delimiters
            return [q.strip() for q in re.split(r'[,;/]', qualifications) if q.strip()]
        else:
            return []

    def _extract_education_keywords(self, job_data: Dict[str, Any]) -> Set[str]:
        """
        Extract education-related keywords from job data.

        Args:
            job_data: Job data

        Returns:
            Set of keywords related to education/certifications
        """
        keywords = set()

        # Extract from title
        if "title" in job_data:
            keywords.update(job_data["title"].lower().split())

        # Extract from qualifications
        for qual in self._extract_qualifications_list(job_data):
            keywords.update(qual.lower().split())

        # Extract from description (first 100 words)
        if "description" in job_data:
            desc_words = job_data["description"].lower().split()[:100]
            keywords.update(desc_words)

        # Filter out very short keywords
        return {k for k in keywords if len(k) > 3}

    def calculate_all_factors(
        self,
        cv_data: Dict[str, Any],
        job_data: Dict[str, Any],
        semantic_similarity: float,
        skills_match: float
    ) -> Dict[str, float]:
        """
        Calculate all matching factors.

        Args:
            cv_data: Parsed CV data (JSON Resume format)
            job_data: Job data (Job Description Schema format)
            semantic_similarity: Pre-calculated semantic similarity from embeddings
            skills_match: Pre-calculated skills match score

        Returns:
            Dictionary with all matching factor scores
        """
        experience_match = self.calculate_experience_match(cv_data, job_data)
        education_match = self.calculate_education_match(cv_data, job_data)

        return {
            "skills_match": skills_match,
            "experience_match": experience_match,
            "education_match": education_match,
            "semantic_similarity": semantic_similarity
        }
