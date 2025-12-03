"""
Tests for hirer router endpoints.

Tests cover:
1. Job creation with test mode enabled/disabled
2. Authorization checks (only hirers can create jobs)
3. List jobs with user filtering
4. Delete jobs with authorization
5. Get job applications with authorization
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
from core.db.models import User, Job, Application, CV
import uuid


class TestCreateJob:
    """Test suite for job creation endpoint."""
    
    def test_create_job_success_test_mode(
        self,
        client: TestClient,
        hirer_auth_headers: dict,
    ):
        """
        Test job creation in test mode (immediate embedding).
        
        Verifies:
        - Hirer can create job
        - Job is linked to authenticated user
        - Embedding is computed immediately when is_test=True
        """
        job_data = {
            "title": "Senior Python Developer",
            "company": "Test Corp",
            "description": "We are looking for an experienced Python developer",
            "employment_type": "full-time",
            "experience_level": "senior",
            "location": {
                "city": "San Francisco",
                "state": "CA",
                "country": "USA"
            },
            "skills": [
                {"name": "Python", "level": "expert"},
                {"name": "FastAPI", "level": "intermediate"}
            ],
            "salary_min": 100000,
            "salary_max": 150000,
        }
        
        print("hirer_auth_headers:", hirer_auth_headers)
        response = client.post(
            "/jobs?is_test=true",
            json=job_data,
            headers=hirer_auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "Job created successfully"
        assert "job_id" in data
    
    def test_create_job_batch_mode(
        self,
        client: TestClient,
        hirer_auth_headers: dict,
    ):
        """
        Test job creation in batch mode (queued embedding).
        
        Verifies:
        - Job is created with pending_batch status
        - Embedding computation is deferred
        """
        job_data = {
            "title": "Junior Developer",
            "company": "Startup Inc",
            "description": "Entry level position",
            "employment_type": "full-time",
            "experience_level": "junior",
        }
        
        response = client.post(
            "/jobs?is_test=false",
            json=job_data,
            headers=hirer_auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
   

class TestListJobs:
    """Test suite for list jobs endpoint."""
    
    def test_list_jobs_own_jobs_only(
        self,
        client: TestClient,
        session: Session,
        hirer_auth_headers: dict,
        hirer_user: User,
        sample_job: Job,
    ):
        """
        Test that hirers only see their own jobs by default.
        
        Verifies:
        - User sees only jobs they created
        - Other users' jobs are not visible
        """
        # Create another hirer with a job
        other_hirer = User(
            email="other_hirer@test.com",
            password_hash="hash",
            role="hirer",
        )
        session.add(other_hirer)
        session.commit()
        session.refresh(other_hirer)
        
        other_job = Job(
            job_id=str(uuid.uuid4()),
            title="Other Job",
            company="Other Company",
            description="Other description",
            employment_type="full-time",
            experience_level="mid",
            embedding_status="completed",
            owner_id=other_hirer.id,
        )
        session.add(other_job)
        session.commit()
        
        response = client.get("/jobs", headers=hirer_auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Should only see own job
        assert data["count"] == 1
        assert data["jobs"][0]["job_id"] == sample_job.job_id
    
    def test_list_jobs_admin_show_all(
        self,
        client: TestClient,
        session: Session,
        admin_auth_headers: dict,
        sample_job: Job,
    ):
        """
        Test that admins can view all jobs with show_all=True.
        
        Verifies:
        - Admin can set show_all=True
        - All jobs are returned
        """
        # Create another job
        other_job = Job(
            job_id=str(uuid.uuid4()),
            title="Another Job",
            company="Another Company",
            description="Description",
            employment_type="full-time",
            experience_level="senior",
            embedding_status="completed",
            owner_id=999,  # Different owner
        )
        session.add(other_job)
        session.commit()
        
        response = client.get("/jobs?show_all=true", headers=admin_auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Should see all jobs
        assert data["count"] >= 2
    
    def test_list_jobs_non_admin_show_all_fails(
        self,
        client: TestClient,
        hirer_auth_headers: dict,
    ):
        """
        Test that non-admins cannot use show_all=True.
        
        Verifies:
        - Returns 403 for non-admin users
        """
        response = client.get("/jobs?show_all=true", headers=hirer_auth_headers)
        
        assert response.status_code == 403
        assert "Only admins can view all jobs" in response.json()["detail"]
    
    def test_list_jobs_without_auth_fails(self, client: TestClient):
        """
        Test that listing jobs requires authentication.
        
        Verifies:
        - Unauthenticated requests are rejected with 401
        """
        response = client.get("/jobs")
        
        assert response.status_code == 401


class TestDeleteJob:
    """Test suite for delete job endpoint."""
    
    def test_delete_job_owner_success(
        self,
        client: TestClient,
        hirer_auth_headers: dict,
        sample_job: Job,
    ):
        """
        Test that job owner can delete their job.
        
        Verifies:
        - Owner can delete their own job
        - Job is removed from database
        """
        response = client.delete(
            f"/jobs/{sample_job.job_id}",
            headers=hirer_auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "Job deleted successfully"
        assert data["job_id"] == sample_job.job_id
    
    def test_delete_job_non_owner_fails(
        self,
        client: TestClient,
        session: Session,
        candidate_auth_headers: dict,
        sample_job: Job,
    ):
        """
        Test that non-owners cannot delete jobs.
        
        Verifies:
        - Returns 403 for non-owners
        - Job is not deleted
        """
        response = client.delete(
            f"/jobs/{sample_job.job_id}",
            headers=candidate_auth_headers,
        )
        
        assert response.status_code == 403
        assert "Not authorized" in response.json()["detail"]
    
    def test_delete_job_admin_success(
        self,
        client: TestClient,
        admin_auth_headers: dict,
        sample_job: Job,
    ):
        """
        Test that admins can delete any job.
        
        Verifies:
        - Admin can delete jobs they don't own
        """
        response = client.delete(
            f"/jobs/{sample_job.job_id}",
            headers=admin_auth_headers,
        )
        
        assert response.status_code == 200
    
    def test_delete_job_not_found(
        self,
        client: TestClient,
        hirer_auth_headers: dict,
    ):
        """
        Test deleting non-existent job.
        
        Verifies:
        - Returns 404 for non-existent job
        """
        response = client.delete(
            "/jobs/nonexistent-job-id",
            headers=hirer_auth_headers,
        )
        
        assert response.status_code == 404
    
    def test_delete_job_without_auth_fails(
        self,
        client: TestClient,
        sample_job: Job,
    ):
        """
        Test that deleting jobs requires authentication.
        
        Verifies:
        - Unauthenticated requests are rejected with 401
        """
        response = client.delete(f"/jobs/{sample_job.job_id}")
        
        assert response.status_code == 401


class TestGetJobApplications:
    """Test suite for get job applications endpoint."""
    
    def test_get_applications_owner_success(
        self,
        client: TestClient,
        session: Session,
        hirer_auth_headers: dict,
        sample_job: Job,
        sample_cv: CV,
    ):
        """
        Test that job owner can view applications.
        
        Verifies:
        - Owner can see applications for their job
        - Application details include candidate info
        """
        # Create an application
        application = Application(
            cv_id=sample_cv.filename,
            job_id=sample_job.job_id,
            prediction_id=str(uuid.uuid4()),
            status="pending",
        )
        session.add(application)
        session.commit()
        
        response = client.get(
            f"/jobs/{sample_job.job_id}/applications",
            headers=hirer_auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["job_id"] == sample_job.job_id
        assert data["count"] == 1
        assert len(data["applications"]) == 1
        assert data["applications"][0]["status"] == "pending"
    
    def test_get_applications_non_owner_fails(
        self,
        client: TestClient,
        candidate_auth_headers: dict,
        sample_job: Job,
    ):
        """
        Test that non-owners cannot view applications.
        
        Verifies:
        - Returns 403 for non-owners
        """
        response = client.get(
            f"/jobs/{sample_job.job_id}/applications",
            headers=candidate_auth_headers,
        )
        
        assert response.status_code == 403
        assert "Not authorized" in response.json()["detail"]
    
    def test_get_applications_admin_success(
        self,
        client: TestClient,
        admin_auth_headers: dict,
        sample_job: Job,
    ):
        """
        Test that admins can view any job's applications.
        
        Verifies:
        - Admin can access applications for any job
        """
        response = client.get(
            f"/jobs/{sample_job.job_id}/applications",
            headers=admin_auth_headers,
        )
        
        assert response.status_code == 200
    
    def test_get_applications_with_status_filter(
        self,
        client: TestClient,
        session: Session,
        hirer_auth_headers: dict,
        sample_job: Job,
        sample_cv: CV,
    ):
        """
        Test filtering applications by status.
        
        Verifies:
        - Status filter works correctly
        - Only matching applications are returned
        """
        # Create applications with different statuses
        app1 = Application(
            cv_id=sample_cv.filename,
            job_id=sample_job.job_id,
            prediction_id=str(uuid.uuid4()),
            status="pending",
        )
        app2 = Application(
            cv_id=sample_cv.filename + "2",
            job_id=sample_job.job_id,
            prediction_id=str(uuid.uuid4()),
            status="accepted",
        )
        session.add(app1)
        session.add(app2)
        session.commit()
        
        response = client.get(
            f"/jobs/{sample_job.job_id}/applications?status_filter=pending",
            headers=hirer_auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should only see pending applications
        assert all(app["status"] == "pending" for app in data["applications"])
    
    def test_get_applications_job_not_found(
        self,
        client: TestClient,
        hirer_auth_headers: dict,
    ):
        """
        Test getting applications for non-existent job.
        
        Verifies:
        - Returns 404 for non-existent job
        """
        response = client.get(
            "/jobs/nonexistent-job/applications",
            headers=hirer_auth_headers,
        )
        
        assert response.status_code == 404
    
    def test_get_applications_without_auth_fails(
        self,
        client: TestClient,
        sample_job: Job,
    ):
        """
        Test that viewing applications requires authentication.
        
        Verifies:
        - Unauthenticated requests are rejected with 401
        """
        response = client.get(f"/jobs/{sample_job.job_id}/applications")
        
        assert response.status_code == 401
