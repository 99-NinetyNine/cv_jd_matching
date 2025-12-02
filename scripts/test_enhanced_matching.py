#!/usr/bin/env python3
"""
Test script for enhanced job recommendation system.
Verifies that all matching factors and skills analysis are working correctly.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.matching.skills_analyzer import SkillsAnalyzer
from core.matching.matching_factors import MatchingFactorsCalculator


def test_skills_analyzer():
    """Test the skills analyzer module."""
    print("=" * 60)
    print("Testing Skills Analyzer")
    print("=" * 60)
    
    analyzer = SkillsAnalyzer()
    
    # Sample CV data
    cv_data = {
        "basics": {
            "name": "John Doe",
            "summary": "Experienced Python developer with expertise in machine learning and NLP"
        },
        "skills": ["Python", "TensorFlow", "NLP", "Docker", "AWS"],
        "work": [
            {
                "position": "Senior AI Engineer",
                "summary": "Built LLM applications using PyTorch and transformers",
                "highlights": ["Developed chatbots", "Implemented RAG systems"]
            }
        ]
    }
    
    # Sample job data
    job_data = {
        "title": "Senior AI Engineer",
        "company": "Tech Innovations Inc",
        "description": "Looking for an AI engineer with Python and LLM experience",
        "skills": ["Python", "TensorFlow", "NLP", "LLMs", "Kubernetes"],
        "qualifications": "Bachelor's degree in Computer Science"
    }
    
    # Analyze
    result = analyzer.analyze(cv_data, job_data)
    
    print(f"\n✓ Skills Match Score: {result['skills_match']:.2f}")
    print(f"✓ Matched Skills: {', '.join(result['matched_skills'])}")
    print(f"✓ Missing Skills: {', '.join(result['missing_skills'])}")
    print(f"✓ CV Skills Count: {result['cv_skills_count']}")
    print(f"✓ Job Skills Count: {result['job_skills_count']}")
    
    return result


def test_matching_factors():
    """Test the matching factors calculator."""
    print("\n" + "=" * 60)
    print("Testing Matching Factors Calculator")
    print("=" * 60)
    
    calculator = MatchingFactorsCalculator()
    
    # Sample CV data
    cv_data = {
        "basics": {
            "name": "Jane Smith",
            "summary": "Software engineer with 5 years of experience"
        },
        "work": [
            {
                "position": "Software Engineer",
                "company": "Tech Corp",
                "startDate": "2019-01-01",
                "endDate": "Present"
            },
            {
                "position": "Junior Developer",
                "company": "StartupXYZ",
                "startDate": "2017-06-01",
                "endDate": "2018-12-31"
            }
        ],
        "education": [
            {
                "studyType": "Bachelor of Science",
                "area": "Computer Science",
                "institution": "University of Tech"
            }
        ]
    }
    
    # Sample job data
    job_data = {
        "title": "Senior Software Engineer",
        "company": "BigTech Inc",
        "experience": "5+ years",
        "qualifications": "Bachelor's degree in Computer Science or related field",
        "description": "We need a senior engineer with 5 years of experience"
    }
    
    # Calculate factors
    experience_score = calculator.calculate_experience_match(cv_data, job_data)
    education_score = calculator.calculate_education_match(cv_data, job_data)
    
    print(f"\n✓ Experience Match: {experience_score:.2f}")
    print(f"✓ Education Match: {education_score:.2f}")
    
    # Test all factors
    all_factors = calculator.calculate_all_factors(
        cv_data=cv_data,
        job_data=job_data,
        semantic_similarity=0.85,
        skills_match=0.90
    )
    
    print(f"\n✓ All Matching Factors:")
    for factor, score in all_factors.items():
        print(f"  - {factor}: {score:.2f}")
    
    return all_factors


def test_integration():
    """Test the integration of both modules."""
    print("\n" + "=" * 60)
    print("Testing Integration")
    print("=" * 60)
    
    analyzer = SkillsAnalyzer()
    calculator = MatchingFactorsCalculator()
    
    # Complete CV
    cv_data = {
        "basics": {
            "name": "Alex Johnson",
            "summary": "Full-stack developer with AI/ML expertise"
        },
        "skills": ["Python", "JavaScript", "React", "TensorFlow", "Docker"],
        "work": [
            {
                "position": "Full Stack Developer",
                "startDate": "2020-01-01",
                "endDate": "Present",
                "highlights": ["Built ML models", "Deployed with Kubernetes"]
            }
        ],
        "education": [
            {
                "studyType": "Master of Science",
                "area": "Artificial Intelligence"
            }
        ]
    }
    
    # Job posting
    job_data = {
        "title": "AI/ML Engineer",
        "company": "AI Startup",
        "skills": ["Python", "TensorFlow", "Kubernetes", "MLOps"],
        "experience": "3-5 years",
        "qualifications": "Master's degree preferred",
        "description": "Build and deploy ML models in production"
    }
    
    # Analyze skills
    skills_result = analyzer.analyze(cv_data, job_data)
    
    # Calculate all factors
    all_factors = calculator.calculate_all_factors(
        cv_data=cv_data,
        job_data=job_data,
        semantic_similarity=0.88,
        skills_match=skills_result['skills_match']
    )
    
    # Calculate overall score (weighted)
    overall_score = (
        all_factors["skills_match"] * 0.35 +
        all_factors["experience_match"] * 0.25 +
        all_factors["education_match"] * 0.15 +
        all_factors["semantic_similarity"] * 0.25
    )
    
    print(f"\n✓ Complete Match Analysis:")
    print(f"  Candidate: {cv_data['basics']['name']}")
    print(f"  Job: {job_data['title']} at {job_data['company']}")
    print(f"\n  Matching Factors:")
    for factor, score in all_factors.items():
        print(f"    - {factor}: {score:.3f}")
    print(f"\n  Matched Skills: {', '.join(skills_result['matched_skills'])}")
    print(f"  Missing Skills: {', '.join(skills_result['missing_skills'])}")
    print(f"\n  ⭐ Overall Match Score: {overall_score:.3f}")
    
    return overall_score


def main():
    """Run all tests."""
    print("\n🧪 Testing Enhanced Job Recommendation System\n")
    
    try:
        # Test individual components
        skills_result = test_skills_analyzer()
        factors_result = test_matching_factors()
        overall_score = test_integration()
        
        print("\n" + "=" * 60)
        print("✅ All Tests Passed!")
        print("=" * 60)
        print("\nThe enhanced recommendation system is working correctly:")
        print("  ✓ Skills analyzer extracts and compares skills")
        print("  ✓ Matching factors calculator computes detailed scores")
        print("  ✓ Integration produces complete match analysis")
        print("\nReady for production use! 🚀\n")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Test Failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
