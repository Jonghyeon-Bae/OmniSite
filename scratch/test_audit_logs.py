import requests
import json

url = "http://127.0.0.1:8000/api/v1/spatial/logs"
try:
    res = requests.get(url)
    print("Status:", res.status_code)
    print("Response JSON:", json.dumps(res.json(), indent=2, ensure_ascii=False))
except Exception as e:
    print("Error:", e)
