"""
Test configuration and fixtures for API tests.

This module provides common fixtures and configuration for all API tests.
By default, tests now hit the REAL API running in Docker and use the REAL database.

Default fixtures:
- client: httpx.Client hitting http://localhost:8000 (real API)
- session: Real PostgreSQL database session with cleanup

Legacy fixtures (for unit tests):
- unit_test_client: In-process TestClient (old behavior)
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from typing import Generator
import sys
import os
import httpx
from pathlib import Path
import uuid

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.db.engine import get_session
from core.db.models import User, CV, Job, Application
from core.auth.security import get_password_hash, create_access_token

# Import app after adding to path
from api.main import app


# ============================================================================
# PRIMARY FIXTURES - Real API + Real Database (DEFAULT)
# ============================================================================

@pytest.fixture(name="session", scope="function")
def session_fixture() -> Generator[Session, None, None]:
    """
    Connect to real PostgreSQL database running in Docker.
    
    This is the DEFAULT database fixture. Tests use the real database.
    Data is cleaned up after each test to ensure isolation.
    
    Environment variables:
        DATABASE_URL: Connection string (default: postgresql://postgres:postgres@localhost:5432/cv_matching)
    
    Yields:
        Session: Database session connected to real PostgreSQL
    """
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/cv_matching"
    )

    engine = create_engine(database_url, echo=False)
    
    # Ensure tables exist
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        yield session
        
      


@pytest.fixture(name="client", scope="function")
def client_fixture() -> Generator[httpx.Client, None, None]:
    """
    Create HTTP client to test against the REAL API running in Docker.
    
    This is the DEFAULT client fixture. Tests hit http://localhost:8000.
    
    Environment variables:
        API_BASE_URL: Base URL for API (default: http://localhost:8000)
    
    Yields:
        httpx.Client: HTTP client connected to the live API
    """
    base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    
    with httpx.Client(base_url=base_url, timeout=30.0, follow_redirects=True) as client:
        yield client


# ============================================================================
# LEGACY FIXTURES - In-Process TestClient (for unit tests)
# ============================================================================

@pytest.fixture(name="unit_test_client")
def unit_test_client_fixture(session: Session) -> Generator[TestClient, None, None]:
    """
    Create an in-process FastAPI test client (legacy behavior).
    
    Use this ONLY for unit tests that need to mock dependencies.
    For integration tests, use the default 'client' fixture.
    
    Args:
        session: Database session to override
    
    Returns:
        TestClient: In-process FastAPI test client
    """
    def get_session_override():
        return session
    
    app.dependency_overrides[get_session] = get_session_override
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


# ============================================================================
# USER FIXTURES - Create test users in real database
# ============================================================================

@pytest.fixture(name="candidate_user")
def candidate_user_fixture(session: Session) -> User:
    """
    Create a test candidate user in the real database.
    
    Args:
        session: Database session
    
    Returns:
        User: Test candidate user
    """
    # Use unique email to avoid conflicts
    email = f"candidate_{uuid.uuid4().hex[:8]}@test.com"
    
    user = User(
        email=email,
        password_hash=get_password_hash("testpass123"),
        role="candidate",
        is_premium=False,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="premium_candidate_user")
def premium_candidate_user_fixture(session: Session) -> User:
    """
    Create a test premium candidate user in the real database.
    
    Args:
        session: Database session
    
    Returns:
        User: Test premium candidate user
    """
    email = f"premium_{uuid.uuid4().hex[:8]}@test.com"
    
    user = User(
        email=email,
        password_hash=get_password_hash("testpass123"),
        role="candidate",
        is_premium=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="hirer_user")
def hirer_user_fixture(session: Session) -> User:
    """
    Create a test hirer user in the real database.
    
    Args:
        session: Database session
    
    Returns:
        User: Test hirer user
    """
    email = f"hirer_{uuid.uuid4().hex[:8]}@test.com"
    
    user = User(
        email=email,
        password_hash=get_password_hash("testpass123"),
        role="hirer",
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="admin_user")
def admin_user_fixture(session: Session) -> User:
    """
    Create a test admin user in the real database.
    
    Args:
        session: Database session
    
    Returns:
        User: Test admin user
    """
    email = f"admin_{uuid.uuid4().hex[:8]}@test.com"
    
    user = User(
        email=email,
        password_hash=get_password_hash("testpass123"),
        role="admin",
        is_admin=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


# ============================================================================
# AUTHENTICATION HELPERS
# ============================================================================
def login_and_get_headers(client: TestClient, email: str, password: str = "testpass123") -> dict:
    response = client.post(
        "/token",
        data={
            "username": email,
            "password": password,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
@pytest.fixture
def auth_headers(client: TestClient):
    def _get_headers(user: User):
        return login_and_get_headers(client, user.email)
    return _get_headers

@pytest.fixture
def candidate_auth_headers(auth_headers, candidate_user):
    return auth_headers(candidate_user)

@pytest.fixture
def premium_candidate_auth_headers(auth_headers, premium_candidate_user):
    return auth_headers(premium_candidate_user)

@pytest.fixture
def hirer_auth_headers(auth_headers, hirer_user):
    return auth_headers(hirer_user)

@pytest.fixture
def admin_auth_headers(auth_headers, admin_user):
    return auth_headers(admin_user)

# ============================================================================
# TEST DATA FACTORIES
# ============================================================================

@pytest.fixture(name="sample_cv")
def sample_cv_fixture(session: Session, candidate_user: User) -> CV:
    """
    Create a sample CV for testing in the real database.
    
    Args:
        session: Database session
        candidate_user: Owner of the CV
    
    Returns:
        CV: Test CV record
    """
    cv = CV(
        filename="test_cv.pdf",
        content={
            "basics": {
                "name": "John Doe",
                "email": "john@example.com",
                "summary": "Experienced software engineer"
            },
            "skills": ["Python", "FastAPI", "PostgreSQL"],
            "work": [
                {
                    "company": "Tech Corp",
                    "position": "Senior Developer",
                    "years": 3
                }
            ]
        },
        embedding_status="completed",
        parsing_status="completed",
        is_latest=True,
        owner_id=candidate_user.id,
    )
    session.add(cv)
    session.commit()
    session.refresh(cv)
    return cv


@pytest.fixture(name="sample_job")
def sample_job_fixture(session: Session, hirer_user: User) -> Job:
    """
    Create a sample job for testing in the real database.

    Args:
        session: Database session
        hirer_user: Owner of the job

    Returns:
        Job: Test job record
    """
    job = Job(
        job_id=str(uuid.uuid4()),
        title="Senior Python Developer",
        company="Test Company",
        description="Looking for an experienced Python developer",
        location={"city": "San Francisco", "country": "USA"},
        skills=[{"name": "Python", "level": "expert"}],
        employment_type="full-time",
        experience_level="senior",
        salary_min=100000,
        salary_max=150000,
        embedding_status="completed",
        owner_id=hirer_user.id,
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


# ============================================================================
# ADDITIONAL FIXTURES
# ============================================================================

@pytest.fixture(name="test_db_engine")
def test_db_engine_fixture():
    """
    Create a test database engine.
    
    Returns:
        Engine: SQLModel engine for testing
    """
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/cv_matching"
    )
    
    engine = create_engine(database_url, echo=False)
    SQLModel.metadata.create_all(engine)
    return engine

