"""
Locust load testing for CV-Job matching system.
Tests various endpoints under different load scenarios.

Run with:
    locust -f scripts/locust_load_test.py --host=http://localhost:8000
"""

from locust import HttpUser, task, between, events
import json
import random
import logging
from io import BytesIO

logger = logging.getLogger(__name__)


class CandidateUser(HttpUser):
    """Simulates candidate users uploading CVs and checking recommendations."""

    wait_time = between(1, 5)  # Wait 1-5 seconds between tasks

    def on_start(self):
        """Called when a user starts."""
        self.cv_id = None
        self.prediction_id = None

    @task(3)
    def get_recommendations(self):
        """Get job recommendations (most common action)."""
        with self.client.get(
            "/api/candidate/recommendations",
            catch_response=True,
            name="/api/candidate/recommendations"
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "recommendations" in data:
                        response.success()
                        self.prediction_id = data.get("prediction_id")
                    else:
                        response.failure("No recommendations in response")
                except Exception as e:
                    response.failure(f"Failed to parse response: {e}")
            elif response.status_code == 404:
                # No CV found - expected for new users
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")

    @task(1)
    def upload_cv(self):
        """Upload a CV (less common action)."""
        # Create a dummy PDF-like file
        pdf_content = b"%PDF-1.4\n%..." + b"x" * 1024  # Dummy PDF content

        files = {"file": ("test_cv.pdf", BytesIO(pdf_content), "application/pdf")}

        with self.client.post(
            "/api/candidate/upload_and_parse",
            files=files,
            catch_response=True,
            name="/api/candidate/upload_and_parse"
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    self.cv_id = data.get("cv_id")
                    response.success()
                except Exception as e:
                    response.failure(f"Failed to parse response: {e}")
            else:
                response.failure(f"Got status code {response.status_code}")

    @task(2)
    def log_interaction(self):
        """Log a user interaction with a job posting."""
        if not self.cv_id:
            # Use a dummy CV ID for testing
            self.cv_id = f"dummy_cv_{random.randint(1, 100)}"

        if not self.prediction_id:
            self.prediction_id = f"dummy_pred_{random.randint(1, 100)}"

        interaction_data = {
            "user_id": self.cv_id,
            "job_id": f"job_{random.randint(1, 50)}",
            "action": random.choice(["viewed", "applied", "saved"]),
            "strategy": "pgvector",
            "prediction_id": self.prediction_id,
            "cv_id": self.cv_id
        }

        with self.client.post(
            "/api/candidate/interact",
            json=interaction_data,
            catch_response=True,
            name="/api/candidate/interact"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")


class HirerUser(HttpUser):
    """Simulates hirer users creating jobs and reviewing applications."""

    wait_time = between(2, 6)

    def on_start(self):
        """Called when a user starts."""
        self.job_ids = []

    @task(1)
    def create_job(self):
        """Create a new job posting."""
        job_data = {
            "title": random.choice(["Software Engineer", "Data Scientist", "DevOps Engineer"]),
            "company": f"Company {random.randint(1, 100)}",
            "description": "We are looking for talented engineers to join our team.",
            "experience": f"{random.randint(2, 10)} years",
            "skills": random.sample(["Python", "Java", "Docker", "AWS", "React"], 3),
            "location": random.choice(["San Francisco", "New York", "Remote"])
        }

        with self.client.post(
            "/api/jobs",
            json=job_data,
            catch_response=True,
            name="/api/jobs (create)"
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    job_id = data.get("job_id")
                    if job_id:
                        self.job_ids.append(job_id)
                    response.success()
                except Exception as e:
                    response.failure(f"Failed to parse response: {e}")
            else:
                response.failure(f"Got status code {response.status_code}")

    @task(3)
    def list_jobs(self):
        """List all jobs (most common action for hirers)."""
        with self.client.get(
            "/api/jobs",
            catch_response=True,
            name="/api/jobs (list)"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")

    @task(2)
    def get_applications(self):
        """Get applications for a job."""
        if not self.job_ids:
            # Use a dummy job ID
            job_id = f"job_{random.randint(1, 50)}"
        else:
            job_id = random.choice(self.job_ids)

        with self.client.get(
            f"/api/jobs/{job_id}/applications",
            catch_response=True,
            name="/api/jobs/{job_id}/applications"
        ) as response:
            if response.status_code in [200, 404]:  # 404 is acceptable (no applications)
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")


class AdminUser(HttpUser):
    """Simulates admin users checking metrics and system health."""

    wait_time = between(5, 10)

    @task(1)
    def get_system_metrics(self):
        """Get system performance metrics."""
        with self.client.get(
            "/api/admin/metrics",
            catch_response=True,
            name="/api/admin/metrics"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")

    @task(1)
    def get_evaluation_metrics(self):
        """Get recommendation evaluation metrics."""
        with self.client.get(
            "/api/admin/evaluation_metrics",
            catch_response=True,
            name="/api/admin/evaluation_metrics"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")


class MixedUser(HttpUser):
    """Mixed user behavior - simulates real-world traffic mix."""

    wait_time = between(1, 5)
    tasks = {
        CandidateUser: 70,  # 70% candidate traffic
        HirerUser: 25,      # 25% hirer traffic
        AdminUser: 5        # 5% admin traffic
    }


# Custom events for detailed reporting
@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Log detailed request information."""
    if exception:
        logger.error(f"Request failed: {name} - {exception}")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when the test starts."""
    print("🚀 Load test starting...")
    print(f"Host: {environment.host}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when the test stops."""
    print("\n✅ Load test completed!")
    print(f"Total requests: {environment.stats.total.num_requests}")
    print(f"Total failures: {environment.stats.total.num_failures}")
    print(f"Average response time: {environment.stats.total.avg_response_time:.2f}ms")
    print(f"Requests per second: {environment.stats.total.total_rps:.2f}")


# Scenarios for different load profiles
class BurstTraffic(HttpUser):
    """Simulates burst traffic - sudden spike in users."""
    wait_time = between(0.1, 0.5)  # Very short wait time
    tasks = {CandidateUser: 1}


class SteadyTraffic(HttpUser):
    """Simulates steady, normal traffic."""
    wait_time = between(2, 5)
    tasks = {MixedUser: 1}


class HeavyLoad(HttpUser):
    """Simulates heavy sustained load."""
    wait_time = between(0.5, 2)
    tasks = {MixedUser: 1}
