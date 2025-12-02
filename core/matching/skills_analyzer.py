"""
Skills Analyzer Module - Domain Agnostic

Extracts and compares skills between CVs and job descriptions using structured schemas.
Works for ALL domains (tech, healthcare, finance, education, etc.) by leveraging
the JSON Resume and Job Description schemas instead of hardcoded regex patterns.
"""

from typing import List, Dict, Set, Any, Optional
from difflib import SequenceMatcher
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import logging

logger = logging.getLogger(__name__)


class SkillsAnalyzer:
    """
    Domain-agnostic skills analyzer that uses structured schema fields.
    Works for any industry by extracting skills from schema-defined fields.
    """

    def __init__(self, similarity_threshold: float = 0.75):
        """
        Initialize the skills analyzer.

        Args:
            similarity_threshold: Threshold for fuzzy matching (0.0-1.0)
        """
        self.similarity_threshold = similarity_threshold

    def extract_skills_from_cv(self, cv_data: Dict[str, Any]) -> Set[str]:
        """
        Extract skills from CV data using JSON Resume schema.

        Schema-based extraction from:
        - skills[].name
        - skills[].keywords[]
        - work[].highlights[]
        - projects[].keywords[]
        - certificates[].name

        Args:
            cv_data: Parsed CV data (JSON Resume format)

        Returns:
            Set of normalized skill names
        """
        skills = set()

        # 1. Extract from structured skills section (PRIMARY SOURCE)
        if "skills" in cv_data and isinstance(cv_data["skills"], list):
            for skill in cv_data["skills"]:
                if isinstance(skill, dict):
                    # Skill name
                    if skill.get("name"):
                        skills.add(skill["name"].lower().strip())

                    # Skill keywords
                    if "keywords" in skill and isinstance(skill["keywords"], list):
                        for keyword in skill["keywords"]:
                            if keyword:
                                skills.add(str(keyword).lower().strip())
                elif isinstance(skill, str):
                    # Handle simple string skills
                    skills.add(skill.lower().strip())

        # 2. Extract from work experience highlights
        if "work" in cv_data and isinstance(cv_data["work"], list):
            for work_item in cv_data["work"]:
                if isinstance(work_item, dict):
                    highlights = work_item.get("highlights", [])
                    if isinstance(highlights, list):
                        # Extract skills mentioned in highlights
                        for highlight in highlights:
                            if highlight:
                                # Simple extraction: words that look like skills (capitalized, 2+ chars)
                                skills.update(self._extract_skill_terms(str(highlight)))

        # 3. Extract from projects
        if "projects" in cv_data and isinstance(cv_data["projects"], list):
            for project in cv_data["projects"]:
                if isinstance(project, dict):
                    # Project keywords
                    if "keywords" in project and isinstance(project["keywords"], list):
                        for keyword in project["keywords"]:
                            if keyword:
                                skills.add(str(keyword).lower().strip())

        # 4. Extract from certificates
        if "certificates" in cv_data and isinstance(cv_data["certificates"], list):
            for cert in cv_data["certificates"]:
                if isinstance(cert, dict) and cert.get("name"):
                    # Certificate names often indicate skills
                    skills.add(cert["name"].lower().strip())

        # Clean up: remove very short or very long strings
        skills = {s for s in skills if 2 <= len(s) <= 100}

        return skills

    def extract_skills_from_job(self, job_data: Dict[str, Any]) -> Set[str]:
        """
        Extract required skills from job description using Job schema.

        Schema-based extraction from:
        - skills[].name
        - skills[].keywords[]
        - qualifications[]
        - responsibilities[]

        Args:
            job_data: Job data (Job Description Schema format)

        Returns:
            Set of normalized skill names
        """
        skills = set()

        # 1. Extract from structured skills field (PRIMARY SOURCE)
        if "skills" in job_data:
            job_skills = job_data["skills"]

            if isinstance(job_skills, list):
                for skill in job_skills:
                    if isinstance(skill, dict):
                        # Skill name
                        if skill.get("name"):
                            skills.add(skill["name"].lower().strip())

                        # Skill keywords
                        if "keywords" in skill and isinstance(skill["keywords"], list):
                            for keyword in skill["keywords"]:
                                if keyword:
                                    skills.add(str(keyword).lower().strip())
                    elif isinstance(skill, str):
                        # Handle simple string skills (backward compatibility)
                        skills.add(skill.lower().strip())

        # 2. Extract from qualifications (structured list)
        if "qualifications" in job_data:
            qualifications = job_data["qualifications"]

            if isinstance(qualifications, list):
                for qual in qualifications:
                    if qual:
                        # Qualifications often mention required skills
                        skills.update(self._extract_skill_terms(str(qual)))
            elif isinstance(qualifications, str):
                # Handle legacy string format
                skills.update(self._extract_skill_terms(qualifications))

        # 3. Extract from responsibilities
        if "responsibilities" in job_data and isinstance(job_data["responsibilities"], list):
            for resp in job_data["responsibilities"]:
                if resp:
                    # Responsibilities often mention required skills
                    skills.update(self._extract_skill_terms(str(resp)))

        # 4. Extract from description (fallback)
        if "description" in job_data and job_data["description"]:
            description = job_data["description"]
            # Extract skill-like terms from description
            skills.update(self._extract_skill_terms(description))

        # Clean up
        skills = {s for s in skills if 2 <= len(s) <= 100}

        return skills

    def _extract_skill_terms(self, text: str) -> Set[str]:
        """
        Extract skill-like terms from free-form text.
        Domain-agnostic approach: looks for capitalized terms, acronyms, and technical phrases.

        Args:
            text: Text to extract skills from

        Returns:
            Set of extracted skill terms
        """
        if not text:
            return set()

        skills = set()
        words = text.split()

        for i, word in enumerate(words):
            cleaned = word.strip('.,;:()[]{}"\'-')

            # Pattern 1: Capitalized words (e.g., Python, JavaScript, Nursing, AutoCAD)
            if len(cleaned) >= 3 and cleaned[0].isupper():
                skills.add(cleaned.lower())

            # Pattern 2: Acronyms (e.g., SQL, API, CPR, MBA)
            if len(cleaned) >= 2 and cleaned.isupper():
                skills.add(cleaned.lower())

            # Pattern 3: Two-word technical phrases (e.g., "machine learning", "patient care")
            if i < len(words) - 1:
                next_word = words[i + 1].strip('.,;:()[]{}"\'-')
                two_word = f"{cleaned} {next_word}"
                # Both words should be reasonably long
                if len(cleaned) >= 3 and len(next_word) >= 3:
                    if cleaned[0].isupper() or next_word[0].isupper():
                        skills.add(two_word.lower())

        return skills

    def calculate_matched_skills(
        self,
        cv_skills: Set[str],
        job_skills: Set[str],
        use_semantic: bool = True
    ) -> List[str]:
        """
        Calculate skills that match between CV and job.
        Uses exact matching, fuzzy matching, and optional semantic similarity.

        Args:
            cv_skills: Skills from CV
            job_skills: Required skills from job
            use_semantic: Whether to use semantic similarity (TF-IDF cosine)

        Returns:
            List of matched skills
        """
        matched = set()

        # Exact matches (case-insensitive)
        cv_skills_lower = {s.lower() for s in cv_skills}
        job_skills_lower = {s.lower() for s in job_skills}
        exact_matches = cv_skills_lower.intersection(job_skills_lower)
        matched.update(exact_matches)

        # Remaining skills for fuzzy/semantic matching
        remaining_cv = cv_skills_lower - exact_matches
        remaining_job = job_skills_lower - exact_matches

        if not remaining_cv or not remaining_job:
            return sorted(list(matched))

        # Fuzzy string matching
        for cv_skill in list(remaining_cv):
            for job_skill in list(remaining_job):
                similarity = self._similarity(cv_skill, job_skill)
                if similarity >= self.similarity_threshold:
                    matched.add(job_skill)  # Use job skill name as canonical
                    remaining_cv.discard(cv_skill)
                    remaining_job.discard(job_skill)
                    break

        # Semantic similarity using TF-IDF (optional, for multi-word skills)
        if use_semantic and remaining_cv and remaining_job:
            try:
                all_skills = list(remaining_cv) + list(remaining_job)
                if len(all_skills) >= 2:  # Need at least 2 items for vectorization
                    vectorizer = TfidfVectorizer(ngram_range=(1, 3), min_df=1)
                    vectors = vectorizer.fit_transform(all_skills)

                    cv_vectors = vectors[:len(remaining_cv)]
                    job_vectors = vectors[len(remaining_cv):]

                    # Calculate cosine similarity
                    if cv_vectors.shape[0] > 0 and job_vectors.shape[0] > 0:
                        similarity_matrix = cosine_similarity(cv_vectors, job_vectors)

                        # Find best matches above threshold
                        for i, cv_skill in enumerate(remaining_cv):
                            best_match_idx = similarity_matrix[i].argmax()
                            best_score = similarity_matrix[i, best_match_idx]

                            if best_score >= self.similarity_threshold:
                                job_skill = list(remaining_job)[best_match_idx]
                                matched.add(job_skill)

            except Exception as e:
                logger.warning(f"Semantic matching failed: {e}")

        return sorted(list(matched))

    def calculate_missing_skills(
        self,
        cv_skills: Set[str],
        job_skills: Set[str],
        matched_skills: List[str]
    ) -> List[str]:
        """
        Calculate skills required by job but missing from CV.

        Args:
            cv_skills: Skills from CV
            job_skills: Required skills from job
            matched_skills: Already matched skills

        Returns:
            List of missing skills
        """
        matched_set = {s.lower() for s in matched_skills}
        job_skills_lower = {s.lower() for s in job_skills}
        missing = job_skills_lower - matched_set

        return sorted(list(missing))

    def calculate_skills_match_score(
        self,
        matched_skills: List[str],
        job_skills: Set[str]
    ) -> float:
        """
        Calculate skills match score (0.0 to 1.0).

        Args:
            matched_skills: List of matched skills
            job_skills: All required job skills

        Returns:
            Score from 0.0 (no match) to 1.0 (perfect match)
        """
        if not job_skills:
            return 1.0  # No requirements means perfect match

        match_ratio = len(matched_skills) / len(job_skills)
        return min(1.0, match_ratio)  # Cap at 1.0

    def _similarity(self, a: str, b: str) -> float:
        """
        Calculate similarity between two strings.

        Args:
            a: First string
            b: Second string

        Returns:
            Similarity score (0.0 to 1.0)
        """
        return SequenceMatcher(None, a, b).ratio()

    def analyze(
        self,
        cv_data: Dict[str, Any],
        job_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Perform complete skills analysis.

        Args:
            cv_data: Parsed CV data (JSON Resume format)
            job_data: Job data (Job Description Schema format)

        Returns:
            Dictionary with matched_skills, missing_skills, and skills_match_score
        """
        cv_skills = self.extract_skills_from_cv(cv_data)
        job_skills = self.extract_skills_from_job(job_data)

        matched_skills = self.calculate_matched_skills(cv_skills, job_skills)
        missing_skills = self.calculate_missing_skills(cv_skills, job_skills, matched_skills)
        skills_match_score = self.calculate_skills_match_score(matched_skills, job_skills)

        return {
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
            "skills_match": skills_match_score,
            "cv_skills_count": len(cv_skills),
            "job_skills_count": len(job_skills)
        }
