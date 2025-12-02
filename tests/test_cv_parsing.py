import requests
from pathlib import Path

BASE_URL = "http://localhost:8000"

def test_upload_cv(file_path: str, token: str):
    print(f"Testing CV upload for file: {file_path}")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    with open(file_path, "rb") as f:
        files = {"file": (Path(file_path).name, f, "application/pdf")}
        response = requests.post(f"{BASE_URL}/upload_and_parse", files=files, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print("Upload Success!")
        print(f"CV ID: {data['cv_id']}, Filename: {data['filename']}")
        print(f"Parsed data keys: {list(data['data'].keys())}")
        return data
    else:
        print(f"Upload Failed: {response.status_code} - {response.text}")
        return None

if __name__ == "__main__":
    # First, login as candidate to get token
    login_resp = requests.post(f"{BASE_URL}/token", data={
        "username": "candidate@example.com",
        "password": "pass123"
    })
    
    token = login_resp.json().get("access_token")
    if not token:
        print("Login failed, cannot test CV upload.")
    else:
        # Test uploading a PDF CV
        test_upload_cv("test_resumes/ADVOCATE_14445309.pdf", token)

"""
case a.
candidate is not premium user
case a.1 canddiate has uploaded cv for the first time
    expected=> run the parsing, compute its embedding, compute similiarity scores and return rag result. but if so many others users want this
    and they are new then this is gonna create more problems.
case a.2 candidate has uploadeed cv before
    expected => saved result is r etuned, cv will be handled in batched mode
case b: candidate is premium user 
though this will still gonna cost if all users are premium users, but anyways let's say that these are batched.

=> this i can do 

case c. jobs are batched always 
case d. jobs are not batched but computed asap.

case e. when case b or a.1 occurs, we need to measure siiliarty search performance, here measureing latency of rag would be better
case f. when case a.2 occurs, we need to measure siimliarty performance on batch level, and also rag is batched here too

case g. measuring evaluation such as ctr etc so that admin keeps track of these.




"""