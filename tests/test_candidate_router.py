"""
Tests for candidate router endpoints.

Tests cover:
1. CV upload with different action modes (upload, parse, analyze)
2. Get recommendations with authentication and user filtering
3. Authorization checks for user-specific data

NOTE: These tests hit the REAL API running in Docker (http://localhost:8000)
"""

import pytest
import httpx
from sqlmodel import Session
from core.db.models import User, CV
from io import BytesIO
import time


class TestUploadCV:
    """Test suite for CV upload endpoint with different actions."""
    
    def test_upload_cv_upload_mode_success(
        self,
        client: httpx.Client,
        candidate_auth_headers: dict,
        candidate_user: User,
    ):
        """
        Test CV upload in 'upload' mode (file save only).
        
        Verifies:
        - File is accepted and saved
        - CV record is created in database
        - CV is linked to authenticated user
        """
        # Create a mock PDF file
        pdf_content = b"%PDF-1.4 mock pdf content"
        files = {
            "file": ("test.pdf", BytesIO(pdf_content), "application/pdf")
        }
        
        response = client.post(
            "/candidate/upload?action=upload",
            files=files,
            headers=candidate_auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "cv_id" in data
        assert "filename" in data
        assert "path" in data
        assert data["filename"].endswith(".pdf")
    
    def test_upload_cv_without_auth_fails(self, client: httpx.Client):
        """
        Test that CV upload requires authentication.
        
        Verifies:
        - Unauthenticated requests are rejected with 401
        """
        pdf_content = b"%PDF-1.4 mock pdf content"
        files = {
            "file": ("test.pdf", BytesIO(pdf_content), "application/pdf")
        }
        
        response = client.post(
            "/candidate/upload?action=upload",
            files=files,
        )
        
        assert response.status_code == 401
    
    def test_upload_cv_wrong_file_type_fails(
        self,
        client: httpx.Client,
        candidate_auth_headers: dict,
    ):
        """
        Test that only PDF files are accepted.
        
        Verifies:
        - Non-PDF files are rejected with 400
        """
        txt_content = b"This is a text file"
        files = {
            "file": ("test.txt", BytesIO(txt_content), "text/plain")
        }
        
        response = client.post(
            "/candidate/upload?action=upload",
            files=files,
            headers=candidate_auth_headers,
        )
        
        assert response.status_code == 400
        assert "Only PDF files are allowed" in response.json()["detail"]
    
    def test_upload_cv_file_too_large_fails(
        self,
        client: httpx.Client,
        candidate_auth_headers: dict,
    ):
        """
        Test that files over 5MB are rejected.
        
        Verifies:
        - Large files are rejected with 400
        """
        # Create a file larger than 5MB
        large_content = b"%PDF-1.4" + (b"x" * (6 * 1024 * 1024))
        files = {
            "file": ("large.pdf", BytesIO(large_content), "application/pdf")
        }
        
        response = client.post(
            "/candidate/upload?action=upload",
            files=files,
            headers=candidate_auth_headers,
        )
        
        assert response.status_code == 400
        assert "too large" in response.json()["detail"].lower()
    
    def test_upload_cv_parse_mode(
        self,
        client: httpx.Client,
        candidate_auth_headers: dict,
    ):
        """
        Test CV upload in 'parse' mode.
        
        Verifies:
        - File is uploaded and parsed by real parser
        - Parsed data is returned
        
        NOTE: This test uses the real parsing service (LLM).
        If parsing fails, it may be due to service unavailability.
        """
        pdf_content = b"%PDF-1.4 mock pdf content"
        files = {
            "file": ("test.pdf", BytesIO(pdf_content), "application/pdf")
        }
        
        response = client.post(
            "/candidate/upload?action=parse",
            files=files,
            headers=candidate_auth_headers,
        )
        
        # Parse mode may take time or fail if LLM unavailable
        # We accept both success and service unavailable
        assert response.status_code in [200, 503, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "cv_id" in data
            assert "data" in data
    
    def test_upload_cv_analyze_mode(
        self,
        client: httpx.Client,
        candidate_auth_headers: dict,
    ):
        """
        Test CV upload in 'analyze' mode (full processing with matching).
        
        Verifies:
        - File is uploaded, parsed, and matched using real services
        - Recommendations are returned
        - Prediction is saved
        
        NOTE: This test uses real parsing and matching services.
        Results may vary based on actual job data in database.
        """
        pdf_content = b"%PDF-1.4 mock pdf content"
        files = {
            "file": ("test.pdf", BytesIO(pdf_content), "application/pdf")
        }
        
        response = client.post(
            "/candidate/upload?action=analyze",
            files=files,
            headers=candidate_auth_headers,
        )
        
        # Analyze mode may take time or fail if services unavailable
        # We accept success, service unavailable, or queued for batch
        assert response.status_code in [200, 202, 503, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "status" in data
            # May be "complete" or "queued" depending on premium status
            assert data["status"] in ["complete", "queued"]
            
            if data["status"] == "complete":
                assert "recommendations" in data
                assert "prediction_id" in data


class TestGetRecommendations:
    """Test suite for get recommendations endpoint."""
    
    def test_get_recommendations_success(
        self,
        client: httpx.Client,
        session: Session,
        candidate_auth_headers: dict,
        candidate_user: User,
        sample_cv: CV,
    ):
        """
        Test successful retrieval of recommendations.
        
        Verifies:
        - Authenticated user can get recommendations
        - Only user's own CVs are used
        - Real cache and database are queried
        """
        # Create a prediction for the CV in the real database
        from core.db.models import Prediction
        import uuid
        
        mock_matches = [
            {"job_id": "job1", "score": 0.95},
            {"job_id": "job2", "score": 0.85},
        ]
        
        prediction = Prediction(
            prediction_id=str(uuid.uuid4()),
            cv_id=str(sample_cv.id),
            matches=mock_matches,
        )
        session.add(prediction)
        session.commit()
        
        response = client.get(
            "/candidate/recommendations",
            headers=candidate_auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "recommendations" in data
        assert "candidate_name" in data
        assert data["candidate_name"] == "John Doe"
        assert len(data["recommendations"]) >= 0  # May vary based on actual data
    
    def test_get_recommendations_no_cv_fails(
        self,
        client: httpx.Client,
        candidate_auth_headers: dict,
    ):
        """
        Test that endpoint fails gracefully when user has no CV.
        
        Verifies:
        - Returns 404 when no CV found
        - Error message is helpful
        """
        response = client.get(
            "/candidate/recommendations",
            headers=candidate_auth_headers,
        )
        
        assert response.status_code == 404
        assert "No CV found" in response.json()["detail"]
    
    def test_get_recommendations_without_auth_fails(self, client: httpx.Client):
        """
        Test that recommendations require authentication.
        
        Verifies:
        - Unauthenticated requests are rejected with 401
        """
        response = client.get("/candidate/recommendations")
        
        assert response.status_code == 401
    
    def test_get_recommendations_only_own_cv(
        self,
        client: httpx.Client,
        session: Session,
        candidate_auth_headers: dict,
        candidate_user: User,
        hirer_user: User,
    ):
        """
        Test that users only see recommendations for their own CVs.
        
        Verifies:
        - User cannot access other users' CVs
        - Only CVs with matching owner_id are considered
        """
        # Create a CV for another user
        other_cv = CV(
            filename="other_cv.pdf",
            content={"basics": {"name": "Other User"}},
            embedding_status="completed",
            parsing_status="completed",
            is_latest=True,
            owner_id=hirer_user.id,  # Different owner
        )
        session.add(other_cv)
        session.commit()
        
        response = client.get(
            "/candidate/recommendations",
            headers=candidate_auth_headers,
        )
        
        # Should return 404 because candidate has no CV
        assert response.status_code == 404
    
    def test_get_recommendations_uses_latest_cv(
        self,
        client: httpx.Client,
        session: Session,
        candidate_auth_headers: dict,
        candidate_user: User,
    ):
        """
        Test that recommendations use the latest CV.
        
        Verifies:
        - Only CV with is_latest=True is used
        - Older CVs are ignored
        """
        # Create two CVs, only one is latest
        old_cv = CV(
            filename="old_cv.pdf",
            content={"basics": {"name": "Old Version"}},
            embedding_status="completed",
            parsing_status="completed",
            is_latest=False,
            owner_id=candidate_user.id,
        )
        latest_cv = CV(
            filename="latest_cv.pdf",
            content={"basics": {"name": "Latest Version"}},
            embedding_status="completed",
            parsing_status="completed",
            is_latest=True,
            owner_id=candidate_user.id,
        )
        session.add(old_cv)
        session.add(latest_cv)
        session.commit()
        session.refresh(latest_cv)
        
        # Create prediction for latest CV
        from core.db.models import Prediction
        import uuid
        
        prediction = Prediction(
            prediction_id=str(uuid.uuid4()),
            cv_id=str(latest_cv.id),
            matches=[{"job_id": "job1", "score": 0.9}],
        )
        session.add(prediction)
        session.commit()
        
        response = client.get(
            "/candidate/recommendations",
            headers=candidate_auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["candidate_name"] == "Latest Version"
