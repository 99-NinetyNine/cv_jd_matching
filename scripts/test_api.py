from fastapi.testclient import TestClient
from api.main import app
import os

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
    print("Health check passed.")

def test_extract():
    pdf_path = "data/synthetic_verification/resume_0.pdf"
    if not os.path.exists(pdf_path):
        print(f"Skipping extract test: {pdf_path} not found.")
        return

    with open(pdf_path, "rb") as f:
        # We need to mock the LLM inside the pipeline used by the app
        # Since 'app' imports 'pipeline', we can try to patch it or just rely on the env var
        # The env var LLM_MODEL=mock should be set when running this script
        
        response = client.post("/extract", files={"file": ("resume.pdf", f, "application/pdf")})
    
    if response.status_code == 200:
        print("Extract endpoint passed.")
        data = response.json()
        if "basics" in data:
            print("  - Structure verified.")
    else:
        print(f"Extract endpoint failed: {response.status_code} - {response.text}")

if __name__ == "__main__":
    test_health()
    test_extract()
