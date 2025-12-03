import time
import logging
import uuid
import random
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from core.matching.semantic_matcher import GraphMatcher
from core.matching.evaluation.metrics import Evaluator, PerformanceMonitor

logger = logging.getLogger(__name__)

class EvaluationPipeline:
    """
    Scalable evaluation pipeline for job recommendation system.
    Handles data generation, batch processing, and performance measurement.
    """
    
    def __init__(self, db_session=None):
        self.matcher = GraphMatcher()
        self.evaluator = Evaluator()
        self.monitor = PerformanceMonitor(db_session)
        self.session = db_session
        
    def generate_synthetic_data(self, num_cvs: int = 100, num_jobs: int = 50) -> Dict[str, Any]:
        """
        Generate synthetic CVs and Jobs for load testing.
        """
        logger.info(f"Generating {num_cvs} CVs and {num_jobs} Jobs...")
        
        skills_pool = ["Python", "Java", "React", "AWS", "Docker", "Kubernetes", "Machine Learning", "NLP", "SQL", "NoSQL"]
        roles_pool = ["Software Engineer", "Data Scientist", "DevOps Engineer", "Frontend Developer", "Backend Developer"]
        
        cvs = []
        for i in range(num_cvs):
            role = random.choice(roles_pool)
            skills = random.sample(skills_pool, k=random.randint(3, 8))
            cvs.append({
                "id": f"cv_{i}",
                "basics": {
                    "name": f"Candidate {i}",
                    "summary": f"Experienced {role} with skills in {', '.join(skills)}"
                },
                "skills": skills,
                "work": [{"position": role, "summary": "Worked on various projects"}]
            })
            
        jobs = []
        for i in range(num_jobs):
            role = random.choice(roles_pool)
            skills = random.sample(skills_pool, k=random.randint(3, 8))
            jobs.append({
                "id": f"job_{i}",
                "title": role,
                "company": f"Company {i}",
                "description": f"We are looking for a {role} with experience in {', '.join(skills)}",
                "skills": skills
            })
            
        return {"cvs": cvs, "jobs": jobs}

    def run_load_test(self, cvs: List[Dict], concurrency: int = 5) -> Dict[str, Any]:
        """
        Run load test by processing CVs concurrently.
        Measures latency and throughput.
        """
        logger.info(f"Starting load test with {len(cvs)} CVs (Concurrency: {concurrency})...")
        
        start_time = time.time()
        latencies = []
        
        # Helper for parallel execution
        def process_cv(cv):
            t0 = time.time()
            try:
                # Run matching
                matches = self.matcher.match(cv, cv_id=cv.get("id"))
                duration = time.time() - t0
                return duration, True
            except Exception as e:
                logger.error(f"Error processing CV {cv.get('id')}: {e}")
                return time.time() - t0, False

        success_count = 0
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [executor.submit(process_cv, cv) for cv in cvs]
            
            for future in as_completed(futures):
                duration, success = future.result()
                latencies.append(duration)
                if success:
                    success_count += 1
                    
                # Log metric to DB if session available
                if self.session and success:
                    self.monitor.log_latency("match_latency", duration, {"type": "load_test"})

        total_time = time.time() - start_time
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        throughput = (success_count / total_time) * 60  # Requests per minute
        
        results = {
            "total_processed": len(cvs),
            "success_count": success_count,
            "total_time_seconds": round(total_time, 2),
            "avg_latency_seconds": round(avg_latency, 4),
            "throughput_rpm": round(throughput, 2),
            "p95_latency": round(sorted(latencies)[int(len(latencies) * 0.95)], 4) if latencies else 0,
            "p99_latency": round(sorted(latencies)[int(len(latencies) * 0.99)], 4) if latencies else 0
        }
        
        logger.info(f"Load Test Results: {results}")
        return results

    def evaluate_quality(self, ground_truth: Dict[str, List[str]], predictions: Dict[str, List[str]]) -> Dict[str, float]:
        """
        Evaluate recommendation quality using precision, recall, etc.
        """
        return self.evaluator.evaluate(ground_truth, predictions)
