"""
Tests for interactions router endpoints.

Tests cover:
1. Log interaction for candidates (viewed, saved, applied)
2. Log interaction for hirers (shortlisted, interviewed, hired, rejected)
3. Get user interaction stats with authorization
4. Get job interaction stats with authorization
5. Application creation and status updates
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
from core.db.models import User, Job, CV, Application, UserInteraction
import uuid


class TestLogInteraction:
    """Test suite for log interaction endpoint."""
    
    def test_log_candidate_viewed_interaction(
        self,
        client: TestClient,
        session: Session,
        candidate_auth_headers: dict,
        sample_job: Job,
    ):
        """
        Test logging a 'viewed' interaction from candidate.
        
        Verifies:
        - Candidate can log view action
        - Interaction is saved to database
        """
        interaction_data = {
            "user_id": "candidate_123",
            "user_type": "candidate",
            "job_id": sample_job.job_id,
            "action": "viewed",
            "prediction_id": str(uuid.uuid4()),
        }
        
        response = client.post(
            "/interactions/log",
            json=interaction_data,
            headers=candidate_auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert "viewed" in data["message"]
    
    def test_log_candidate_saved_interaction(
        self,
        client: TestClient,
        candidate_auth_headers: dict,
        sample_job: Job,
    ):
        """
        Test logging a 'saved' interaction from candidate.
        
        Verifies:
        - Candidate can save/bookmark jobs
        """
        interaction_data = {
            "user_id": "candidate_123",
            "user_type": "candidate",
            "job_id": sample_job.job_id,
            "action": "saved",
        }
        
        response = client.post(
            "/interactions/log",
            json=interaction_data,
            headers=candidate_auth_headers,
        )
        
        assert response.status_code == 200
        assert response.json()["status"] == "success"
    
    def test_log_candidate_applied_creates_application(
        self,
        client: TestClient,
        session: Session,
        candidate_auth_headers: dict,
        sample_job: Job,
        sample_cv: CV,
    ):
        """
        Test that 'applied' action creates an Application record.
        
        Verifies:
        - Application record is created
        - Application ID is returned
        - Status is set to 'pending'
        """
        interaction_data = {
            "user_id": "candidate_123",
            "user_type": "candidate",
            "job_id": sample_job.job_id,
            "action": "applied",
            "cv_id": sample_cv.filename,
            "prediction_id": str(uuid.uuid4()),
        }
        
        response = client.post(
            "/interactions/log",
            json=interaction_data,
            headers=candidate_auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert "application_id" in data
        assert data["application_id"] is not None
        
        # Verify application was created
        application = session.query(Application).filter(
            Application.id == data["application_id"]
        ).first()
        assert application is not None
        assert application.status == "pending"
    
    def test_log_candidate_applied_duplicate_no_error(
        self,
        client: TestClient,
        session: Session,
        candidate_auth_headers: dict,
        sample_job: Job,
        sample_cv: CV,
    ):
        """
        Test that applying twice to same job doesn't create duplicate.
        
        Verifies:
        - Duplicate applications are handled gracefully
        - Existing application ID is returned
        """
        # Create existing application
        existing_app = Application(
            cv_id=sample_cv.filename,
            job_id=sample_job.job_id,
            prediction_id=str(uuid.uuid4()),
            status="pending",
        )
        session.add(existing_app)
        session.commit()
        session.refresh(existing_app)
        
        interaction_data = {
            "user_id": "candidate_123",
            "user_type": "candidate",
            "job_id": sample_job.job_id,
            "action": "applied",
            "cv_id": sample_cv.filename,
            "prediction_id": str(uuid.uuid4()),
        }
        
        response = client.post(
            "/interactions/log",
            json=interaction_data,
            headers=candidate_auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["application_id"] == existing_app.id
    
    def test_log_hirer_shortlisted_interaction(
        self,
        client: TestClient,
        session: Session,
        hirer_auth_headers: dict,
        sample_job: Job,
        sample_cv: CV,
    ):
        """
        Test logging a 'shortlisted' interaction from hirer.
        
        Verifies:
        - Hirer can shortlist candidates
        - Application status is updated
        """
        # Create application first
        application = Application(
            cv_id=sample_cv.filename,
            job_id=sample_job.job_id,
            prediction_id=str(uuid.uuid4()),
            status="pending",
        )
        session.add(application)
        session.commit()
        session.refresh(application)
        
        interaction_data = {
            "user_id": "hirer_123",
            "user_type": "hirer",
            "job_id": sample_job.job_id,
            "action": "shortlisted",
            "application_id": application.id,
        }
        
        response = client.post(
            "/interactions/log",
            json=interaction_data,
            headers=hirer_auth_headers,
        )
        
        assert response.status_code == 200
        assert response.json()["status"] == "success"
    
    def test_log_hirer_hired_updates_application(
        self,
        client: TestClient,
        session: Session,
        hirer_auth_headers: dict,
        sample_job: Job,
        sample_cv: CV,
    ):
        """
        Test that 'hired' action updates application to 'accepted'.
        
        Verifies:
        - Application status changes to 'accepted'
        - Decision timestamp is set
        """
        # Create application
        application = Application(
            cv_id=sample_cv.filename,
            job_id=sample_job.job_id,
            prediction_id=str(uuid.uuid4()),
            status="pending",
        )
        session.add(application)
        session.commit()
        session.refresh(application)
        
        interaction_data = {
            "user_id": "hirer_123",
            "user_type": "hirer",
            "job_id": sample_job.job_id,
            "action": "hired",
            "application_id": application.id,
        }
        
        response = client.post(
            "/interactions/log",
            json=interaction_data,
            headers=hirer_auth_headers,
        )
        
        assert response.status_code == 200
        
        # Verify application status updated
        session.refresh(application)
        assert application.status == "accepted"
        assert application.decision_at is not None
    
    def test_log_hirer_rejected_updates_application(
        self,
        client: TestClient,
        session: Session,
        hirer_auth_headers: dict,
        sample_job: Job,
        sample_cv: CV,
    ):
        """
        Test that 'rejected' action updates application to 'rejected'.
        
        Verifies:
        - Application status changes to 'rejected'
        - Decision timestamp is set
        """
        # Create application
        application = Application(
            cv_id=sample_cv.filename,
            job_id=sample_job.job_id,
            prediction_id=str(uuid.uuid4()),
            status="pending",
        )
        session.add(application)
        session.commit()
        session.refresh(application)
        
        interaction_data = {
            "user_id": "hirer_123",
            "user_type": "hirer",
            "job_id": sample_job.job_id,
            "action": "rejected",
            "application_id": application.id,
        }
        
        response = client.post(
            "/interactions/log",
            json=interaction_data,
            headers=hirer_auth_headers,
        )
        
        assert response.status_code == 200
        
        # Verify application status updated
        session.refresh(application)
        assert application.status == "rejected"
        assert application.decision_at is not None
    
    def test_log_invalid_candidate_action_fails(
        self,
        client: TestClient,
        candidate_auth_headers: dict,
        sample_job: Job,
    ):
        """
        Test that invalid actions for candidates are rejected.
        
        Verifies:
        - Candidates cannot use hirer actions
        - Returns 400 with helpful error
        """
        interaction_data = {
            "user_id": "candidate_123",
            "user_type": "candidate",
            "job_id": sample_job.job_id,
            "action": "hired",  # Invalid for candidate
        }
        
        response = client.post(
            "/interactions/log",
            json=interaction_data,
            headers=candidate_auth_headers,
        )
        
        assert response.status_code == 400
        assert "Invalid candidate action" in response.json()["detail"]
    
    def test_log_invalid_hirer_action_fails(
        self,
        client: TestClient,
        hirer_auth_headers: dict,
        sample_job: Job,
    ):
        """
        Test that invalid actions for hirers are rejected.
        
        Verifies:
        - Hirers cannot use candidate actions
        - Returns 400 with helpful error
        """
        interaction_data = {
            "user_id": "hirer_123",
            "user_type": "hirer",
            "job_id": sample_job.job_id,
            "action": "applied",  # Invalid for hirer
        }
        
        response = client.post(
            "/interactions/log",
            json=interaction_data,
            headers=hirer_auth_headers,
        )
        
        assert response.status_code == 400
        assert "Invalid hirer action" in response.json()["detail"]
    
    def test_log_interaction_without_auth_fails(
        self,
        client: TestClient,
        sample_job: Job,
    ):
        """
        Test that logging interactions requires authentication.
        
        Verifies:
        - Unauthenticated requests are rejected with 401
        """
        interaction_data = {
            "user_id": "test_123",
            "user_type": "candidate",
            "job_id": sample_job.job_id,
            "action": "viewed",
        }
        
        response = client.post("/interactions/log", json=interaction_data)
        
        assert response.status_code == 401


class TestGetUserInteractionStats:
    """Test suite for get user interaction stats endpoint."""
    
    def test_get_own_stats_success(
        self,
        client: TestClient,
        session: Session,
        candidate_auth_headers: dict,
        candidate_user: User,
        sample_job: Job,
    ):
        """
        Test that users can view their own interaction stats.
        
        Verifies:
        - User can access their own stats
        - Stats include action counts and recent interactions
        """
        # Create some interactions
        for action in ["viewed", "saved", "applied"]:
            interaction = UserInteraction(
                user_id=candidate_user.id,
                job_id=sample_job.job_id,
                action=action,
                strategy="pgvector",
            )
            session.add(interaction)
        session.commit()
        
        response = client.get(
            f"/interactions/stats/{candidate_user.id}",
            headers=candidate_auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_interactions"] == 3
        assert "viewed" in data["actions"]
        assert "saved" in data["actions"]
        assert "applied" in data["actions"]
        assert len(data["recent_interactions"]) == 3
    
    def test_get_other_user_stats_fails(
        self,
        client: TestClient,
        session: Session,
        candidate_auth_headers: dict,
        hirer_user: User,
    ):
        """
        Test that users cannot view other users' stats.
        
        Verifies:
        - Returns 403 when accessing other users' stats
        """
        response = client.get(
            f"/interactions/stats/{hirer_user.id}",
            headers=candidate_auth_headers,
        )
        
        assert response.status_code == 403
        assert "Not authorized" in response.json()["detail"]
    
    def test_get_other_user_stats_admin_success(
        self,
        client: TestClient,
        session: Session,
        admin_auth_headers: dict,
        candidate_user: User,
    ):
        """
        Test that admins can view any user's stats.
        
        Verifies:
        - Admin can access other users' stats
        """
        response = client.get(
            f"/interactions/stats/{candidate_user.id}",
            headers=admin_auth_headers,
        )
        
        assert response.status_code == 200
    
    def test_get_stats_no_interactions(
        self,
        client: TestClient,
        candidate_auth_headers: dict,
        candidate_user: User,
    ):
        """
        Test getting stats for user with no interactions.
        
        Verifies:
        - Returns empty stats gracefully
        """
        response = client.get(
            f"/interactions/stats/{candidate_user.id}",
            headers=candidate_auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_interactions"] == 0
        assert data["actions"] == {}
    
    def test_get_stats_without_auth_fails(
        self,
        client: TestClient,
        candidate_user: User,
    ):
        """
        Test that viewing stats requires authentication.
        
        Verifies:
        - Unauthenticated requests are rejected with 401
        """
        response = client.get(f"/interactions/stats/{candidate_user.id}")
        
        assert response.status_code == 401


class TestGetJobInteractionStats:
    """Test suite for get job interaction stats endpoint."""
    
    def test_get_job_stats_owner_success(
        self,
        client: TestClient,
        session: Session,
        hirer_auth_headers: dict,
        sample_job: Job,
        candidate_user: User,
    ):
        """
        Test that job owner can view job interaction stats.
        
        Verifies:
        - Owner can access job stats
        - Stats include engagement metrics
        """
        # Create interactions
        for action in ["viewed", "viewed", "applied"]:
            interaction = UserInteraction(
                user_id=candidate_user.id,
                job_id=sample_job.job_id,
                action=action,
                strategy="pgvector",
            )
            session.add(interaction)
        session.commit()
        
        response = client.get(
            f"/interactions/job/{sample_job.job_id}/stats",
            headers=hirer_auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["job_id"] == sample_job.job_id
        assert data["total_interactions"] == 3
        assert data["actions"]["viewed"] == 2
        assert data["actions"]["applied"] == 1
        assert data["engagement_rate"] == 50.0  # 1 applied / 2 viewed * 100
    
    def test_get_job_stats_non_owner_fails(
        self,
        client: TestClient,
        candidate_auth_headers: dict,
        sample_job: Job,
    ):
        """
        Test that non-owners cannot view job stats.
        
        Verifies:
        - Returns 403 for non-owners
        """
        response = client.get(
            f"/interactions/job/{sample_job.job_id}/stats",
            headers=candidate_auth_headers,
        )
        
        assert response.status_code == 403
        assert "Not authorized" in response.json()["detail"]
    
    def test_get_job_stats_admin_success(
        self,
        client: TestClient,
        admin_auth_headers: dict,
        sample_job: Job,
    ):
        """
        Test that admins can view any job's stats.
        
        Verifies:
        - Admin can access stats for any job
        """
        response = client.get(
            f"/interactions/job/{sample_job.job_id}/stats",
            headers=admin_auth_headers,
        )
        
        assert response.status_code == 200
    
    def test_get_job_stats_not_found(
        self,
        client: TestClient,
        hirer_auth_headers: dict,
    ):
        """
        Test getting stats for non-existent job.
        
        Verifies:
        - Returns 404 for non-existent job
        """
        response = client.get(
            "/interactions/job/nonexistent-job/stats",
            headers=hirer_auth_headers,
        )
        
        assert response.status_code == 404
    
    def test_get_job_stats_no_interactions(
        self,
        client: TestClient,
        hirer_auth_headers: dict,
        sample_job: Job,
    ):
        """
        Test getting stats for job with no interactions.
        
        Verifies:
        - Returns empty stats gracefully
        """
        response = client.get(
            f"/interactions/job/{sample_job.job_id}/stats",
            headers=hirer_auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_interactions"] == 0
        assert data["engagement_rate"] == 0
    
    def test_get_job_stats_without_auth_fails(
        self,
        client: TestClient,
        sample_job: Job,
    ):
        """
        Test that viewing job stats requires authentication.
        
        Verifies:
        - Unauthenticated requests are rejected with 401
        """
        response = client.get(f"/interactions/job/{sample_job.job_id}/stats")
        
        assert response.status_code == 401
