import urllib.request
import json
import time

def test_api():
    base_url = "http://localhost:8000/api/v1/spatial"
    
    # 1. Test district-boundary API (First Call)
    print("\n--- 1. Testing district-boundary (First Call) ---")
    start = time.time()
    try:
        url = f"{base_url}/district-boundary/1"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            elapsed = time.time() - start
            print(f"[Success] Status: {response.status}, Time: {elapsed:.3f}s")
            print(f"GeoJSON Type: {data.get('type')}")
    except Exception as e:
        print(f"[Error] First call failed: {e}")

    # 2. Test district-boundary API (Second Call - Cache Hit Test)
    print("\n--- 2. Testing district-boundary (Second Call - Cache Hit) ---")
    start = time.time()
    try:
        url = f"{base_url}/district-boundary/1"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            elapsed = time.time() - start
            print(f"[Success] Cache Hit Status: {response.status}, Time: {elapsed:.4f}s")
    except Exception as e:
        print(f"[Error] Second call failed: {e}")

    # 3. Test national-properties API
    print("\n--- 3. Testing national-properties ---")
    start = time.time()
    try:
        url = f"{base_url}/national-properties"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            elapsed = time.time() - start
            features = data.get('features', [])
            print(f"[Success] Status: {response.status}, Time: {elapsed:.3f}s")
            print(f"Features returned: {len(features)}")
    except Exception as e:
        print(f"[Error] National properties call failed: {e}")

    # 4. Test user-exclusions API (Database Auto-Healing Verification)
    print("\n--- 4. Testing user-exclusions (Auto-Healing check) ---")
    start = time.time()
    try:
        url = f"{base_url}/user-exclusions"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            elapsed = time.time() - start
            features = data.get('features', [])
            print(f"[Success] Status: {response.status}, Time: {elapsed:.3f}s")
            print(f"User exclusions count: {len(features)}")
    except Exception as e:
        print(f"[Error] User exclusions call failed: {e}")

    # 5. Test recommend optimal sites API (Database query check with user_exclusion_zones table)
    print("\n--- 5. Testing recommend optimal sites (Blind Land / Exclusion checks) ---")
    start = time.time()
    try:
        # 1차 추천 쿼리 (Step 4 가중치를 이용해 ref_lat/ref_lng 부근 추천)
        url = f"{base_url}/recommend?district_id=1&ref_lat=37.5302&ref_lng=126.9724&limit=3"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            elapsed = time.time() - start
            candidates = data.get('candidates', [])
            print(f"[Success] Status: {response.status}, Time: {elapsed:.3f}s")
            print(f"Candidates count returned: {len(candidates)}")
            if candidates:
                # 첫 번째 후보지 정보 출력
                first_cand = candidates[0]
                print(f"First Candidate - Jibun: {first_cand.get('jibun')}, Ownership: {first_cand.get('ownership_type')}, ISI Score: {first_cand.get('isi_score')}")
    except Exception as e:
        print(f"[Error] Recommend call failed: {e}")

if __name__ == "__main__":
    test_api()
