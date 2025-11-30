import requests
import sys

BASE_URL = "http://localhost:8000"

def test_signup(email, password, role):
    print(f"Testing signup for {role}...")
    response = requests.post(f"{BASE_URL}/auth/register", json={
        "email": email,
        "password": password,
        "role": role
    })
    if response.status_code == 200:
        data = response.json()
        print(f"Success! Token: {data['access_token'][:10]}... Role: {data['role']}")
        return True
    elif response.status_code == 400 and "already registered" in response.text:
        print("User already registered.")
        return True
    else:
        print(f"Failed: {response.status_code} - {response.text}")
        return False

def test_login(email, password, expected_role):
    print(f"Testing login for {email}...")
    response = requests.post(f"{BASE_URL}/token", data={
        "username": email,
        "password": password
    })
    if response.status_code == 200:
        data = response.json()
        print(f"Success! Token: {data['access_token'][:10]}... Role: {data['role']}")
        if data['role'] == expected_role:
            print("Role match!")
            return True
        else:
            print(f"Role mismatch: expected {expected_role}, got {data['role']}")
            return False
    else:
        print(f"Failed: {response.status_code} - {response.text}")
        return False

if __name__ == "__main__":
    # Test Candidate
    test_signup("candidate@example.com", "pass123", "candidate")
    test_login("candidate@example.com", "pass123", "candidate")
    
    # Test Hirer
    test_signup("hirer@example.com", "pass123", "hirer")
    test_login("hirer@example.com", "pass123", "hirer")
    
    # Test Admin (created via script)
    test_login("admin@example.com", "admin123", "admin")
