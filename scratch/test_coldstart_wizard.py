import requests
import json

BASE_URL = "http://127.0.0.1:8000/api/v1"

print("========================================================")
print(" [ColdStart Wizard 1~4 Steps API Test]")
print("========================================================")

session = requests.Session()

# 1. Login
login_res = session.post(f"{BASE_URL}/auth/login", json={"username": "admin", "password": "admin1234"})
print(f"[Step 0 Login] Status: {login_res.status_code}")
if login_res.status_code == 200:
    token = login_res.json()["access_token"]
    session.headers.update({"Authorization": f"Bearer {token}"})
    print("  ✓ Login Token Obtained!")
else:
    print("  ❌ Login Failed!")
    exit(1)

# 2. Test Step 4 (Empty upload test)
s4_res = session.post(f"{BASE_URL}/upload/seed-spatial-step4")
print(f"[Step 4 Complete API] Status: {s4_res.status_code}")
print(f"  Response: {s4_res.text[:200]}")

print("========================================================")
