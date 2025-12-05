#!/usr/bin/env python3
"""
Script to register a random hirer and post job descriptions from JSON files.
This mimics the API workflow: register -> get token -> create jobs one by one.
"""

import requests
import json
import os
import sys
import random
import string
from pathlib import Path
from typing import Dict, Any


# Configuration
BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
JOBS_DIR = Path(__file__).parent.parent / "tests" / "test_job_desc"


def generate_random_email() -> str:
    """Generate a random email for testing."""
    random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"hirer_{random_str}@test.com"


def generate_random_password() -> str:
    """Generate a random password for testing."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=12))


def register_hirer(email: str, password: str) -> Dict[str, Any]:
    """
    Register a new hirer via /auth/register endpoint.

    Returns:
        Dict with access_token, token_type, and role
    """
    url = f"{BASE_URL}/auth/register"
    payload = {
        "email": email,
        "password": password,
        "role": "hirer"
    }

    print(f"🔐 Registering hirer: {email}")
    response = requests.post(url, json=payload)

    if response.status_code == 200:
        token_data = response.json()
        print(f"✅ Registration successful! Token: {token_data['access_token'][:20]}...")
        return token_data
    else:
        print(f"❌ Registration failed: {response.status_code}")
        print(f"Response: {response.text}")
        sys.exit(1)


def create_job(job_data: Dict[str, Any], token: str, is_test: bool = False) -> Dict[str, Any]:
    """
    Create a job posting via /jobs endpoint.

    Args:
        job_data: Job description JSON
        token: Bearer token from registration
        is_test: If True, compute embedding synchronously

    Returns:
        Response with status and job_id
    """
    url = f"{BASE_URL}/jobs"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    params = {"is_test": str(is_test).lower()}

    # Remove job_id if present (will be auto-generated)
    job_data_copy = job_data.copy()
    job_data_copy.pop("job_id", None)

    print(f"📝 Creating job: {job_data.get('title', 'Unknown')} at {job_data.get('company', 'Unknown')}")

    response = requests.post(url, json=job_data_copy, headers=headers, params=params)

    if response.status_code == 200:
        result = response.json()
        print(f"✅ Job created successfully! ID: {result['job_id']}")
        return result
    else:
        print(f"❌ Job creation failed: {response.status_code}")
        print(f"Response: {response.text}")
        return None


def load_json_files(jobs_dir: Path) -> list:
    """Load all JSON files from the jobs directory."""
    json_files = list(jobs_dir.glob("*.json"))

    if not json_files:
        print(f"⚠️  No JSON files found in {jobs_dir}")
        return []

    jobs = []
    for json_file in json_files:
        try:
            with open(json_file, 'r') as f:
                job_data = json.load(f)
                jobs.append((json_file.name, job_data))
                print(f"📄 Loaded: {json_file.name}")
        except Exception as e:
            print(f"⚠️  Failed to load {json_file.name}: {e}")

    return jobs


def main():
    """Main execution flow."""
    print("=" * 60)
    print("Job Posting Script - Register Hirer & Post Jobs")
    print("=" * 60)
    print()

    # Step 1: Generate random credentials
    email = generate_random_email()
    password = generate_random_password()

    print(f"Generated credentials:")
    print(f"  Email: {email}")
    print(f"  Password: {password}")
    print()

    # Step 2: Register hirer and get token
    token_data = register_hirer(email, password)
    access_token = token_data["access_token"]
    print()

    # Step 3: Load job JSON files
    print(f"📂 Loading jobs from: {JOBS_DIR}")
    jobs = load_json_files(JOBS_DIR)

    if not jobs:
        print("No jobs to post. Exiting.")
        sys.exit(0)

    print(f"Found {len(jobs)} job(s) to post.")
    print()

    # Step 4: Post jobs one by one
    is_test = os.getenv("IS_TEST", "true").lower() == "true"
    successful = 0
    failed = 0

    for idx, (filename, job_data) in enumerate(jobs, 1):
        print(f"\n[{idx}/{len(jobs)}] Processing {filename}")
        print("-" * 60)

        result = create_job(job_data, access_token, is_test=is_test)

        if result:
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
    print(f"  📊 Total: {len(jobs)}")
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
