#!/usr/bin/env python3
"""
Script to register a random candidate and upload CVs with job matching.
This mimics the API workflow: register -> get token -> upload CVs"""

import requests
import json
import os
import sys
import random
import string
from pathlib import Path
from typing import Dict, Any, List


# Configuration
BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
RESUMES_DIR = Path(__file__).parent.parent / "tests" / "test_resumes"


def generate_random_email() -> str:
    """Generate a random email for testing."""
    random_str = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"candidate_{random_str}@test.com"


def generate_random_password() -> str:
    """Generate a random password for testing."""
    return "".join(random.choices(string.ascii_letters + string.digits, k=12))


def register_candidate(email: str, password: str) -> Dict[str, Any]:
    """
    Register a new candidate via /auth/register endpoint.

    Returns:
        Dict with access_token, token_type, and role
    """
    url = f"{BASE_URL}/auth/register"
    payload = {"email": email, "password": password, "role": "candidate"}

    print(f"🔐 Registering candidate: {email}")
    response = requests.post(url, json=payload)

    if response.status_code == 200:
        token_data = response.json()
        print(
            f"✅ Registration successful! Token: {token_data['access_token'][:20]}..."
        )
        return token_data
    else:
        print(f"❌ Registration failed: {response.status_code}")
        print(f"Response: {response.text}")
        sys.exit(1)


def upload_cv_and_match(cv_path: Path, token: str) -> Dict[str, Any]:
    """
    Upload a CV and get job matching results via /upload endpoint.

    Args:
        cv_path: Path to the CV file (PDF)
        token: Bearer token from registration

    Returns:
        Response with predictions and candidate info
    """
    url = f"{BASE_URL}/upload"
    headers = {"Authorization": f"Bearer {token}"}
    # IMPORTANT: specify action upload
    params = {"action": "upload"}

    print(f"📄 Uploading CV: {cv_path.name}")

    # Read the PDF file
    with open(cv_path, "rb") as f:
        files = {"file": (cv_path.name, f, "application/pdf")}

        response = requests.post(url, files=files, headers=headers, params=params)

    if response.status_code == 200:
        result = response.json()
        print(f"✅ CV uploaded and matched successfully!")
        print(f"   Candidate: {result.get('candidate_name', 'Unknown')}")
        print(f"   Recommendations: {len(result.get('recommendations', []))}")
        print(f"   Prediction ID: {result.get('prediction_id', 'N/A')}")
        return result
    else:
        print(f"❌ CV upload failed: {response.status_code}")
        print(f"Response: {response.text}")
        return None

def load_cv_files(resumes_dir: Path, limit: int = None) -> List[Path]:
    """
    Load all PDF files from the resumes directory.

    Args:
        resumes_dir: Directory containing CV PDFs
        limit: Optional limit on number of files to process

    Returns:
        List of CV file paths
    """
    pdf_files = sorted(resumes_dir.glob("*.pdf"))

    if not pdf_files:
        print(f"⚠️  No PDF files found in {resumes_dir}")
        return []

    if limit:
        pdf_files = pdf_files[:limit]

    print(f"📂 Found {len(pdf_files)} CV(s) to process")
    for pdf_file in pdf_files:
        print(f"   - {pdf_file.name}")

    return pdf_files


def main():
    """Main execution flow."""
    print("=" * 60)
    print("CV Upload & Matching Script - Register Candidate & Match CVs")
    print("=" * 60)
    print()

    # Step 1: Generate random credentials
    email = generate_random_email()
    password = generate_random_password()

    print(f"Generated credentials:")
    print(f"  Email: {email}")
    print(f"  Password: {password}")
    print()

    # Step 2: Register candidate and get token
    token_data = register_candidate(email, password)
    access_token = token_data["access_token"]
    print()

    # Step 3: Load CV files
    print(f"📂 Loading CVs from: {RESUMES_DIR}")

    # Check if we should limit the number of CVs (yield if too many)
    limit = None
    cv_files = load_cv_files(RESUMES_DIR)

    if len(cv_files) > 10:
        print(f"\n⚠️  Found {len(cv_files)} CVs. Processing in batches...")
        user_input = input(
            f"Process all {len(cv_files)} CVs? (y/n, or enter number to limit): "
        )

        if user_input.lower() == "n":
            print("Exiting...")
            sys.exit(0)
        elif user_input.isdigit():
            limit = int(user_input)
            cv_files = cv_files[:limit]
            print(f"Processing first {limit} CVs")

    if not cv_files:
        print("No CVs to process. Exiting.")
        sys.exit(0)

    print(f"Processing {len(cv_files)} CV(s).")
    print()

    # Step 4: Upload CVs and save predictions iteratively
    successful = 0
    failed = 0
    # be careful this is real files, sending too much would occupy space in uploads dir

    for idx, cv_path in enumerate(cv_files, 1):
        print(f"\n[{idx}/{len(cv_files)}] Processing {cv_path.name}")
        print("-" * 60)
        if upload_cv_and_match(cv_path, access_token):
           successful += 1
        else:
            failed += 1

        print("-" * 60)

    # Summary
    print()
    print("=" * 60)
    print("Summary:")
    print(f"  ✅ Successful: {successful}")
    print(f"  ❌ Failed: {failed}")
    print(f"  📊 Total: {len(cv_files)}")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Script interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
