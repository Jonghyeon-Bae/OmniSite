import requests

url = "http://127.0.0.1:8000/api/v1/spatial/report/download"
payload = {
    "district_id": 1,
    "facility_type": "smoking_zone",
    "inferred_purpose": "스마트 흡연구역",
    "candidate_jibun": "서울특별시 용산구 한강로2가 72",
    "candidate_css": 95,
    "candidate_lat": 37.5303,
    "candidate_lng": 126.9716,
    "candidate_reason": "안전 이격거리 준수",
    "ahp_weights": {"traffic": 0.4, "complaint": 0.6},
    "debate_logs": [
        {"sender": "상인대표", "text": "상권 활성화를 위해 꼭 필요합니다."},
        {"sender": "주민대표", "text": "주거 정주권 훼손이 우려됩니다."},
        {"sender": "갈등조정관", "text": "이격거리 후퇴 조건으로 상생 합의합니다."}
    ]
}

resp = requests.post(url, json=payload)
print("Status Code:", resp.status_code)
if resp.status_code == 200:
    print("PDF Content-Length:", len(resp.content))
    with open("scratch/test_report.pdf", "wb") as f:
        f.write(resp.content)
    print("Saved test_report.pdf successfully.")
else:
    print("Error Detail:", resp.text)
