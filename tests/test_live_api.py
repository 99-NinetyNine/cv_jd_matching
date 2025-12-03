import pytest
from fastapi import status
import os
import uuid
import time

# Skip these tests if TEST_LIVE_API is not set to true
pytestmark = pytest.mark.skipif(
    os.getenv("TEST_LIVE_API") != "true",
    reason="Skipping live API tests. Set TEST_LIVE_API=true to run."
)

@pytest.fixture
def live_auth_token(live_api_client):
    """
    Register a new user on the live API and return the access token.
    """
    email = f"live_test_{uuid.uuid4()}@example.com"
    password = "testpass123"
    
    response = live_api_client.post(
        "/auth/register",
        json={"email": email, "password": password, "role": "candidate"}
    )
    
    if response.status_code != 200:
        pytest.fail(f"Failed to register live user: {response.text}")
        
    return response.json()["access_token"]

def test_api_health(live_api_client):
    """Test that the API is up and running."""
    try:
        response = live_api_client.get("/health")
    except Exception as e:
        pytest.fail(f"Could not connect to live API: {e}")
        
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "healthy"}

def test_upload_cv_live(live_api_client, live_auth_token):
    """Test uploading a CV to the live API."""
    headers = {"Authorization": f"Bearer {live_auth_token}"}
    
    # Create a dummy PDF content
    # Minimal PDF header/trailer
    pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/Resources <<\n/Font <<\n/F1 4 0 R\n>>\n>>\n/MediaBox [0 0 612 792]\n/Contents 5 0 R\n>>\nendobj\n4 0 obj\n<<\n/Type /Font\n/Subtype /Type1\n/BaseFont /Helvetica\n>>\nendobj\n5 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n/F1 24 Tf\n100 100 Td\n(Hello World) Tj\nET\nendstream\nendobj\nxref\n0 6\n0000000000 65535 f\n0000000010 00000 n\n0000000060 00000 n\n0000000117 00000 n\n0000000256 00000 n\n0000000343 00000 n\ntrailer\n<<\n/Size 6\n/Root 1 0 R\n>>\nstartxref\n437\n%%EOF"
    
    files = {'file': ('test_live.pdf', pdf_content, 'application/pdf')}
    
    # Upload only
    response = live_api_client.post(
        "/candidate/upload?action=upload",
        headers=headers,
        files=files
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "cv_id" in data
    cv_id = data["cv_id"]
    
    # Now try to get recommendations (should fail or return empty/error because not parsed)
    # Actually, recommendations endpoint checks if CV is parsed/embedded.
    
    # Let's try to parse it (action=parse)
    # We need to re-upload or just call parse? The endpoint is upload based.
    # But we can upload the same file again with action=parse.
    
    files = {'file': ('test_live.pdf', pdf_content, 'application/pdf')}
    response = live_api_client.post(
        "/candidate/upload?action=parse",
        headers=headers,
        files=files
    )
    
    # This might fail if the parser (LLM) is not available or mocked in Docker.
    # If using Ollama in Docker, it might work if Ollama is up.
    # If it fails, we just warn.
    if response.status_code != 200:
        print(f"Parse failed (expected if LLM not ready): {response.text}")
    else:
        data = response.json()
        assert "data" in data
        
def test_get_recommendations_live(live_api_client, live_auth_token):
    """Test getting recommendations."""
    headers = {"Authorization": f"Bearer {live_auth_token}"}
    
    response = live_api_client.get("/candidate/recommendations", headers=headers)
    
    # Expect 404 because we haven't uploaded a CV for this user yet (in this test function's scope, if we didn't reuse user)
    # Wait, live_auth_token creates a NEW user each time.
    assert response.status_code == 404
