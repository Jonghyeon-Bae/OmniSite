import requests

url = "http://127.0.0.1:8000/api/v1/spatial/recommend"
params = {
    "district_id": 1,
    "ref_lat": 37.5302,
    "ref_lng": 126.9724,
    "limit": 5
}

resp = requests.get(url, params=params, timeout=10)
data = resp.json()
cands_dict = data.get("candidates", {})
print(f"Candidates Dict Keys: {list(cands_dict.keys())}")

for rank_key, c in cands_dict.items():
    print(f"[{rank_key.upper()}] {c.get('jibun')} ({c.get('ownership_type')}) - CSS Score: {c.get('css_score')}, Lat: {c.get('lat')}, Lng: {c.get('lng')}")
