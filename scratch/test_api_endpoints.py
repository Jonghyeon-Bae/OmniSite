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
            geom = data.get('geometry', {})
            print(f"Geometry Type: {geom.get('type')}, Coord length: {len(geom.get('coordinates', [[]])[0]) if geom.get('coordinates') else 0}")
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
            print(f"Is cached response fast? (Time should be < 0.010s): {elapsed < 0.010}")
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
            if features:
                print(f"Sample Feature Properties: {features[0].get('properties')}")
    except Exception as e:
        print(f"[Error] National properties call failed: {e}")

if __name__ == "__main__":
    test_api()
