import os, sys
sys.path.append("backend")

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

response = client.get("/api/v1/spatial/recommend", params={"district_id": 1, "ref_lat": 37.5302, "ref_lng": 126.9724, "limit": 5})
print("Direct FastAPI Status Code:", response.status_code)
data = response.json()
cands = data.get("candidates", {})
print("Direct FastAPI Candidates Keys:", list(cands.keys()))
for k, v in cands.items():
    print(f"  {k}: {v.get('jibun')} | Ownership: {v.get('ownership_type')} | CSS: {v.get('css_score')} | Lat: {v.get('lat')}, Lng: {v.get('lng')}")
