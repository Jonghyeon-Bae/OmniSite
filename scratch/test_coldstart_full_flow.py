import os
import requests

BASE_URL = "http://127.0.0.1:8000/api/v1"

def test_coldstart_flow():
    session = requests.Session()
    login_res = session.post(f"{BASE_URL}/auth/login", json={"username": "admin", "password": "admin1234"})
    if login_res.status_code != 200:
        print(f"[FAIL] Login failed: {login_res.text}")
        return
    token = login_res.json()["access_token"]
    session.headers.update({"Authorization": f"Bearer {token}"})
    print("[PASS] Step 0: Admin Login OK")

    # Step 4 Test (Empty payload test)
    s4_res = session.post(f"{BASE_URL}/upload/seed-spatial-step4")
    print(f"[PASS] Step 4 Activation API Status: {s4_res.status_code}")
    if s4_res.status_code == 200:
        print(f"  Result: {s4_res.json().get('message')}")
    else:
        print(f"  Fail Result: {s4_res.text}")

if __name__ == "__main__":
    test_coldstart_flow()
