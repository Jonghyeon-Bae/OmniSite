import requests

url = "http://127.0.0.1:8000/api/v1/spatial/history/audit-register-precedent"
payload = {
    "pnu": "1117012500102350001",
    "jibun": "용산구 서빙고동 235-1",
    "filename": "yongsan_smart_infra_completion_notice_sample.pdf",
    "textContent": "Yongsan-gu Seobinggo-dong 235-1, parcel PNU 1117012500102350001 smart booth completion notice. Distance to Seobinggo Kindergarten is 15.2 meters, which satisfies the regulation. Completed successfully."
}

try:
    print("[Test Insert] Calling API...")
    res = requests.post(url, json=payload)
    print(f"[Test Insert] Status Code: {res.status_code}")
    print(f"[Test Insert] Response JSON: {res.json()}")
except Exception as e:
    print(f"[Test Insert] Request Failed: {e}")
