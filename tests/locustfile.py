"""
Locust load testing for CV-Job matching system with realistic flow.

REALISTIC FLOW:
1. Hirer creates job (synchronous)
2. Candidate uploads CV and gets parse (synchronous)
3. Candidate gets recommendations (depends on matching - may wait)
4. Candidate interacts: view → save/apply
5. Hirer reviews applications: shortlist → interview → hire/reject
6. Admin monitors logs anytime

Run with:
    # Web UI
    locust -f scripts/locust_load_test_new.py --host=http://localhost:8000

    # Headless (100 users, 10/sec spawn, 5 min duration)
    locust -f scripts/locust_load_test_new.py --host=http://localhost:8000 --headless -u 100 -r 10 -t 300s

    # Specific user class
    locust -f scripts/locust_load_test_new.py --host=http://localhost:8000 CandidateUser
    locust -f scripts/locust_load_test_new.py --host=http://localhost:8000 HirerUser
"""

from locust import HttpUser, task, between, events, SequentialTaskSet
import json
import random
import logging
from io import BytesIO

logger = logging.getLogger(__name__)

# ============= SAMPLE DATA FOR REALISTIC MOCKING =============

SAMPLE_JOBS = [
    {"title": "Senior Python Engineer", "company": "TechCorp", "description": "Build scalable backend systems with Python, FastAPI, and PostgreSQL. 5+ years exp.", "experience": "5 years", "skills": [{"name": "Python", "level": "expert"}, {"name": "FastAPI", "level": "advanced"}]},
    {"title": "Machine Learning Engineer", "company": "AI Startup", "description": "Develop ML models for NLP and CV tasks. PyTorch, transformers.", "experience": "3 years", "skills": [{"name": "Python", "level": "expert"}, {"name": "PyTorch", "level": "advanced"}]},
    {"title": "DevOps Engineer", "company": "Cloud Co", "description": "Manage K8s clusters, CI/CD pipelines. AWS, Docker, Terraform.", "experience": "4 years", "skills": [{"name": "Kubernetes", "level": "advanced"}, {"name": "AWS", "level": "expert"}]},
    {"title": "Full Stack Developer", "company": "Startup Inc", "description": "React + Node.js + MongoDB. Build products from scratch.", "experience": "2 years", "skills": [{"name": "React", "level": "advanced"}, {"name": "Node.js", "level": "intermediate"}]},
]

# Simple PDF header for valid file upload
DUMMY_PDF = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n%%EOF"


# ============= HELPER MIXIN FOR AUTH =============

class AuthMixin:
    """Mixin to handle authentication."""

    def register_and_login(self, role="candidate"):
        """Register or login user and store token."""
        email = f"load_test_{role}_{random.randint(1, 10000)}@example.com"
        password = "testpassword123"

        # Try to register
        response = self.client.post("/auth/register", json={
            "email": email,
            "password": password,
            "role": role
        }, name=f"[{role}] Auth: Register")

        if response.status_code == 200:
            data = response.json()
            self.token = data["access_token"]
            logger.info(f"✓ Registered {role}: {email}")
        else:
            # If already exists, login
            response = self.client.post("/token", data={
                "username": email,
                "password": password
            }, name=f"[{role}] Auth: Login")

            if response.status_code == 200:
                data = response.json()
                self.token = data["access_token"]
                logger.info(f"✓ Logged in {role}: {email}")
            else:
                # Fallback: create new user
                email = f"load_test_{role}_{random.randint(10001, 99999)}@example.com"
                response = self.client.post("/auth/register", json={
                    "email": email,
                    "password": password,
                    "role": role
                }, name=f"[{role}] Auth: Register (fallback)")
                data = response.json()
                self.token = data["access_token"]

        self.headers = {"Authorization": f"Bearer {self.token}"}
        self.email = email

    def auth_get(self, url, **kwargs):
        """Authenticated GET request."""
        kwargs.setdefault("headers", {}).update(self.headers)
        return self.client.get(url, **kwargs)

    def auth_post(self, url, **kwargs):
        """Authenticated POST request."""
        kwargs.setdefault("headers", {}).update(self.headers)
        return self.client.post(url, **kwargs)


# ============= REALISTIC CANDIDATE FLOW =============

class CandidateFlow(SequentialTaskSet, AuthMixin):
    """Realistic candidate journey: Upload CV → Get Recs → Interact"""

    def on_start(self):
        """Setup candidate user."""
        self.register_and_login(role="candidate")
        self.cv_id = None
        self.prediction_id = None
        self.recommendations = []
        # first time analyze CV
        self.is_first_time = True
        

    @task
    def step1_upload_cv(self):
        """Upload CV (synchronous parsing)."""
        files = {"file": ("candidate_cv.pdf", BytesIO(DUMMY_PDF), "application/pdf")}

        action = "match" if self.is_first_time else "upload"
        self.is_first_time = False

        with self.auth_post(
            f"/upload?action={action}",  # Full flow: upload + parse + match
            files=files,
            catch_response=True,
            name="[Candidate] 1. Upload CV (full)"
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    self.cv_id = data.get("cv_id") or data.get("candidate_id")
                    self.prediction_id = data.get("prediction_id")
                    self.recommendations = data.get("recommendations", [])
                    response.success()
                    logger.info(f"✓ CV uploaded: {self.cv_id}, got {len(self.recommendations)} recs")
                except Exception as e:
                    response.failure(f"Parse error: {e}")
            else:
                response.failure(f"Upload failed: {response.status_code}")

    @task
    def step2_get_recommendations(self):
        """Get job recommendations (may use cache or compute)."""
        with self.auth_get(
            "/recommendations",
            catch_response=True,
            name="[Candidate] 2. Get Recommendations"
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    self.recommendations = data.get("recommendations", [])
                    self.prediction_id = data.get("prediction_id")
                    response.success()
                    logger.info(f"✓ Got {len(self.recommendations)} recommendations")
                except Exception as e:
                    response.failure(f"Parse error: {e}")
            elif response.status_code == 404:
                # No CV yet - expected for new users
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")

    @task
    def step3_view_jobs(self):
        """View recommended jobs."""
        if not self.recommendations:
            logger.warning("No recommendations to view, skipping")
            return

        # View top 3 recommendations
        for rec in self.recommendations[:3]:
            job_id = rec.get("job_id")
            if not job_id:
                continue

            # Log "viewed" interaction
            with self.auth_post(
                "/interactions/log",
                json={
                    "job_id": job_id,
                    "action": "viewed",
                    "cv_id": self.cv_id,
                    "prediction_id": self.prediction_id,
                    "metadata": {"match_score": rec.get("score")}
                },
                catch_response=True,
                name="[Candidate] 3. View Job"
            ) as response:
                if response.status_code == 200:
                    response.success()
                elif response.status_code == 400 and "already" in response.text:
                    response.success()  # Duplicate view is OK
                else:
                    response.failure(f"Failed to log view: {response.status_code}")

    @task
    def step4_save_or_apply(self):
        """Save or apply to jobs."""
        if not self.recommendations:
            return

        # Save 2 jobs
        for rec in self.recommendations[:2]:
            job_id = rec.get("job_id")
            if not job_id:
                continue

            action = random.choice(["saved", "saved", "applied"])  # 66% save, 33% apply

            with self.auth_post(
                "/interactions/log",
                json={
                    "job_id": job_id,
                    "action": action,
                    "cv_id": self.cv_id,
                    "prediction_id": self.prediction_id
                },
                catch_response=True,
                name=f"[Candidate] 4. {action.capitalize()}"
            ) as response:
                if response.status_code in [200, 400]:  # 400 = already exists
                    response.success()
                else:
                    response.failure(f"Failed: {response.status_code}")


# ============= REALISTIC HIRER FLOW =============

class HirerFlow(SequentialTaskSet, AuthMixin):
    """Realistic hirer journey: Create Job → View Apps → Take Action"""

    def on_start(self):
        """Setup hirer user."""
        self.register_and_login(role="hirer")
        self.job_ids = []
        self.applications = []
        # first time let's create job embeddings
        self.is_first_time = True
        
    @task
    def step1_create_job(self):
        """Create job posting (synchronous)."""
        job_data = random.choice(SAMPLE_JOBS).copy()

        is_test = "true" if self.is_first_time else "false"
        self.is_first_time = False
        with self.auth_post(
            f"/jobs?is_test={is_test}",  # Immediate embedding computation
            json=job_data,
            catch_response=True,
            name="[Hirer] 1. Create Job"
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    job_id = data.get("job_id")
                    self.job_ids.append(job_id)
                    response.success()
                    logger.info(f"✓ Created job: {job_id}")
                except Exception as e:
                    response.failure(f"Parse error: {e}")
            else:
                response.failure(f"Failed: {response.status_code}")

    @task
    def step2_list_jobs(self):
        """List own jobs."""
        with self.auth_get(
            "/jobs",
            catch_response=True,
            name="[Hirer] 2. List Jobs"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed: {response.status_code}")

    @task
    def step3_view_applications(self):
        """View applications for jobs."""
        if not self.job_ids:
            return

        job_id = random.choice(self.job_ids)

        with self.auth_get(
            f"/jobs/{job_id}/applications",
            catch_response=True,
            name="[Hirer] 3. View Applications"
        ) as response:
            if response.status_code in [200, 404]:  # 404 = no apps yet
                try:
                    if response.status_code == 200:
                        data = response.json()
                        self.applications = data.get("applications", [])
                except:
                    pass
                response.success()
            else:
                response.failure(f"Failed: {response.status_code}")

    @task
    def step4_take_action(self):
        """Take action on applications (shortlist/interview/hire/reject)."""
        if not self.applications:
            return

        app = random.choice(self.applications)
        action = random.choice(["shortlisted", "interviewed", "hired", "rejected"])

        with self.auth_post(
            "/interactions/log",
            json={
                "job_id": app["job_id"],
                "action": action,
                "application_id": app["id"]
            },
            catch_response=True,
            name=f"[Hirer] 4. {action.capitalize()}"
        ) as response:
            if response.status_code in [200, 400]:
                response.success()
            else:
                response.failure(f"Failed: {response.status_code}")


# ============= ADMIN MONITORING =============

class AdminUser(HttpUser, AuthMixin):
    """Admin monitoring dashboard (no auth needed for metrics)."""

    wait_time = between(5, 15)

    def on_start(self):
        """No auth needed for metrics endpoints."""
        pass

    @task(2)
    def get_evaluation_metrics(self):
        """Check recommendation quality metrics."""
        with self.client.get(
            "/admin/evaluation_metrics",
            catch_response=True,
            name="[Admin] Evaluation Metrics"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed: {response.status_code}")

    @task(2)
    def get_performance_dashboard(self):
        """Check performance dashboard."""
        with self.client.get(
            "/admin/performance_dashboard",
            catch_response=True,
            name="[Admin] Performance Dashboard"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed: {response.status_code}")

    @task(1)
    def get_system_health(self):
        """Check system health."""
        with self.client.get(
            "/admin/system_health",
            catch_response=True,
            name="[Admin] System Health"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed: {response.status_code}")


# ============= USER TYPES FOR LOCUST UI =============

class CandidateUser(HttpUser):
    """Candidate user type (for Locust UI)."""
    wait_time = between(2, 8)
    tasks = [CandidateFlow]


class HirerUser(HttpUser):
    """Hirer user type (for Locust UI)."""
    wait_time = between(3, 10)
    tasks = [HirerFlow]


# ============= MIXED REALISTIC TRAFFIC =============

class MixedTraffic(HttpUser):
    """Realistic traffic mix: 70% candidates, 25% hirers, 5% admin."""

    wait_time = between(1, 5)
    tasks = {
        CandidateFlow: 70,
        HirerFlow: 25,
        AdminUser: 5
    }


# ============= LOAD SCENARIOS =============

class BurstTraffic(HttpUser):
    """Burst scenario: Sudden spike in candidates."""
    wait_time = between(0.1, 1)
    tasks = [CandidateFlow]


class HeavyLoad(HttpUser):
    """Heavy sustained load."""
    wait_time = between(0.5, 2)
    tasks = {CandidateFlow: 70, HirerFlow: 25, AdminUser: 5}


# ============= EVENTS FOR REPORTING =============

@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Log failures."""
    if exception:
        logger.error(f"❌ {name} failed: {exception}")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Test start."""
    print("\n" + "="*60)
    print("🚀 CV-Job Matching Load Test Starting")
    print(f"   Host: {environment.host}")
    print(f"   Realistic flow: Job Creation → CV Upload → Matching → Interactions")
    print("="*60 + "\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Test completion summary."""
    stats = environment.stats
    print("\n" + "="*60)
    print("✅ Load Test Completed!")
    print("="*60)
    print(f"Total requests:        {stats.total.num_requests}")
    print(f"Total failures:        {stats.total.num_failures}")
    print(f"Success rate:          {(1 - stats.total.fail_ratio) * 100:.2f}%")
    print(f"Avg response time:     {stats.total.avg_response_time:.2f}ms")
    print(f"Median response time:  {stats.total.median_response_time:.2f}ms")
    print(f"95th percentile:       {stats.total.get_response_time_percentile(0.95):.2f}ms")
    print(f"99th percentile:       {stats.total.get_response_time_percentile(0.99):.2f}ms")
    print(f"Requests per second:   {stats.total.total_rps:.2f}")
    print("="*60 + "\n")
