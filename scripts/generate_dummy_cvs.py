"""
Generate dummy CVs and jobs with mock embeddings for performance testing.
Bypasses LLM calls to test system performance without API costs.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import Session, select
from core.db.engine import engine
from core.db.models import CV, Job
import numpy as np
import json
from datetime import datetime, timedelta
import random
import uuid


class DummyDataGenerator:
    """Generates realistic dummy CVs and jobs with mock embeddings."""

    def __init__(self, embedding_dim: int = 768):
        self.embedding_dim = embedding_dim

        self.first_names = ["John", "Jane", "Michael", "Sarah", "David", "Emily", "James", "Lisa", "Robert", "Maria"]
        self.last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"]

        self.titles = [
            "Software Engineer", "Senior Software Engineer", "Data Scientist", "Machine Learning Engineer",
            "DevOps Engineer", "Frontend Developer", "Backend Developer", "Full Stack Developer",
            "AI Engineer", "Data Analyst", "System Architect", "Cloud Engineer"
        ]

        self.companies = [
            "Tech Corp", "Innovation Labs", "DataTech Solutions", "Cloud Systems Inc",
            "AI Ventures", "Software Dynamics", "Digital Innovations", "Tech Giants LLC",
            "StartUp Labs", "Enterprise Solutions"
        ]

        self.skills_pool = [
            "Python", "Java", "JavaScript", "TypeScript", "React", "Angular", "Vue.js",
            "Node.js", "Django", "Flask", "FastAPI", "Spring Boot", "Docker", "Kubernetes",
            "AWS", "Azure", "GCP", "PostgreSQL", "MongoDB", "Redis", "Machine Learning",
            "Deep Learning", "NLP", "Computer Vision", "TensorFlow", "PyTorch", "Git",
            "CI/CD", "Microservices", "REST API", "GraphQL", "Agile", "Scrum"
        ]

        self.education_institutions = [
            "MIT", "Stanford University", "UC Berkeley", "Carnegie Mellon",
            "Harvard University", "Georgia Tech", "University of Washington",
            "Cornell University", "Columbia University", "Princeton University"
        ]

        self.degrees = ["Bachelor", "Master", "PhD"]
        self.fields = [
            "Computer Science", "Software Engineering", "Data Science",
            "Electrical Engineering", "Information Technology", "Mathematics"
        ]

    def generate_mock_embedding(self, seed: Optional[int] = None) -> list:
        """
        Generate a mock embedding vector.

        Args:
            seed: Optional seed for reproducibility

        Returns:
            List of floats representing embedding
        """
        if seed is not None:
            np.random.seed(seed)

        # Generate random normalized vector
        embedding = np.random.randn(self.embedding_dim)
        # Normalize to unit length (like real embeddings)
        embedding = embedding / np.linalg.norm(embedding)

        return embedding.tolist()

    def generate_cv_data(self, index: int) -> dict:
        """Generate realistic CV data."""
        first_name = random.choice(self.first_names)
        last_name = random.choice(self.last_names)
        email = f"{first_name.lower()}.{last_name.lower()}@email.com"

        # Random work history (1-4 jobs)
        num_jobs = random.randint(1, 4)
        work_history = []

        for i in range(num_jobs):
            start_year = 2024 - random.randint(0, 10)
            end_year = start_year + random.randint(1, 4)
            if i == 0:  # Current job
                end_date = "Present"
            else:
                end_date = f"{end_year}-{random.randint(1,12):02d}"

            work_history.append({
                "name": random.choice(self.companies),
                "position": random.choice(self.titles),
                "startDate": f"{start_year}-{random.randint(1,12):02d}",
                "endDate": end_date,
                "summary": f"Worked on various projects involving {', '.join(random.sample(self.skills_pool, 3))}",
                "highlights": [
                    f"Developed applications using {random.choice(self.skills_pool)}",
                    f"Led team of {random.randint(2,8)} developers",
                    "Improved system performance by 40%"
                ]
            })

        # Random skills (5-15)
        num_skills = random.randint(5, 15)
        skills = [
            {"name": skill, "level": random.choice(["Beginner", "Intermediate", "Advanced", "Expert"])}
            for skill in random.sample(self.skills_pool, num_skills)
        ]

        # Education
        education = [{
            "institution": random.choice(self.education_institutions),
            "studyType": random.choice(self.degrees),
            "area": random.choice(self.fields),
            "startDate": "2015",
            "endDate": "2019",
            "score": f"{random.uniform(3.0, 4.0):.2f}"
        }]

        cv_data = {
            "basics": {
                "name": f"{first_name} {last_name}",
                "label": random.choice(self.titles),
                "email": email,
                "phone": f"+1-{random.randint(200,999)}-{random.randint(100,999)}-{random.randint(1000,9999)}",
                "summary": f"Experienced {random.choice(self.titles)} with {random.randint(2,10)} years of experience in {random.choice(self.fields)}",
                "location": {
                    "city": random.choice(["San Francisco", "New York", "Seattle", "Boston", "Austin"]),
                    "countryCode": "US"
                }
            },
            "work": work_history,
            "education": education,
            "skills": skills
        }

        return cv_data

    def generate_job_data(self, index: int) -> dict:
        """Generate realistic job posting data."""
        title = random.choice(self.titles)
        company = random.choice(self.companies)

        # Random required skills (3-8)
        required_skills = random.sample(self.skills_pool, random.randint(3, 8))

        job_data = {
            "job_id": f"job_{uuid.uuid4().hex[:8]}",
            "title": title,
            "role": title,
            "company": company,
            "description": f"We are looking for a {title} to join our team. "
                          f"The ideal candidate will have experience with {', '.join(required_skills[:3])}. "
                          f"You will work on exciting projects and collaborate with talented engineers.",
            "experience": f"{random.randint(2,10)} years",
            "qualifications": f"{random.choice(self.degrees)} in {random.choice(self.fields)}",
            "skills": required_skills,
            "salary_range": f"${random.randint(60,150)}K-${random.randint(80,200)}K",
            "location": random.choice(["San Francisco", "New York", "Seattle", "Remote"]),
            "country": "USA",
            "work_type": random.choice(["Full-Time", "Contract", "Part-Time"]),
            "company_size": random.randint(10, 1000),
            "job_posting_date": (datetime.utcnow() - timedelta(days=random.randint(1, 30))).isoformat()
        }

        return job_data

    def create_dummy_cvs(self, count: int, session: Session):
        """Create dummy CVs in database with mock embeddings."""
        print(f"Creating {count} dummy CVs...")

        created = 0
        for i in range(count):
            try:
                cv_data = self.generate_cv_data(i)
                filename = f"dummy_cv_{uuid.uuid4().hex[:8]}.pdf"

                cv = CV(
                    filename=filename,
                    content=cv_data,
                    embedding=self.generate_mock_embedding(seed=i),
                    parsing_status="completed",
                    embedding_status="completed",
                    is_latest=True,
                    last_analyzed=datetime.utcnow(),
                    created_at=datetime.utcnow() - timedelta(days=random.randint(0, 30))
                )

                session.add(cv)
                created += 1

                if (i + 1) % 100 == 0:
                    session.commit()
                    print(f"Created {i + 1}/{count} CVs...")

            except Exception as e:
                print(f"Failed to create CV {i}: {e}")

        session.commit()
        print(f"Successfully created {created} dummy CVs")

    def create_dummy_jobs(self, count: int, session: Session):
        """Create dummy job postings in database with mock embeddings."""
        print(f"Creating {count} dummy jobs...")

        created = 0
        for i in range(count):
            try:
                job_data = self.generate_job_data(i)

                job = Job(
                    job_id=job_data["job_id"],
                    title=job_data["title"],
                    role=job_data.get("role"),
                    company=job_data["company"],
                    description=job_data["description"],
                    experience=job_data.get("experience"),
                    qualifications=job_data.get("qualifications"),
                    skills=job_data.get("skills"),
                    salary_range=job_data.get("salary_range"),
                    location=job_data.get("location"),
                    country=job_data.get("country"),
                    work_type=job_data.get("work_type"),
                    company_size=job_data.get("company_size"),
                    embedding=self.generate_mock_embedding(seed=i + 10000),
                    embedding_status="completed",
                    created_at=datetime.utcnow() - timedelta(days=random.randint(0, 60))
                )

                session.add(job)
                created += 1

                if (i + 1) % 100 == 0:
                    session.commit()
                    print(f"Created {i + 1}/{count} jobs...")

            except Exception as e:
                print(f"Failed to create job {i}: {e}")

        session.commit()
        print(f"Successfully created {created} dummy jobs")


def main():
    """Main function to generate dummy data."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate dummy CVs and jobs for testing")
    parser.add_argument("--cvs", type=int, default=100, help="Number of CVs to generate")
    parser.add_argument("--jobs", type=int, default=50, help="Number of jobs to generate")
    parser.add_argument("--clear", action="store_true", help="Clear existing data first")

    args = parser.parse_args()

    generator = DummyDataGenerator()

    with Session(engine) as session:
        if args.clear:
            print("Clearing existing dummy data...")
            # Delete CVs with dummy filenames
            dummy_cvs = session.exec(select(CV).where(CV.filename.like("dummy_cv_%"))).all()
            for cv in dummy_cvs:
                session.delete(cv)

            # Delete jobs with dummy IDs
            dummy_jobs = session.exec(select(Job).where(Job.job_id.like("job_%"))).all()
            for job in dummy_jobs:
                session.delete(job)

            session.commit()
            print("Cleared existing dummy data")

        # Generate new data
        if args.cvs > 0:
            generator.create_dummy_cvs(args.cvs, session)

        if args.jobs > 0:
            generator.create_dummy_jobs(args.jobs, session)

    print("\n✅ Dummy data generation complete!")
    print(f"Generated {args.cvs} CVs and {args.jobs} jobs with mock embeddings")


if __name__ == "__main__":
    main()
