import urllib.request
import urllib.error
import json
import time

def test_api():
    base_url = "http://localhost:8000/api/v1/spatial"
    
    def safe_request(name, url):
        print(f"\n--- Testing {name} ---")
        start = time.time()
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode('utf-8'))
                elapsed = time.time() - start
                print(f"[Success] Status: {response.status}, Time: {elapsed:.4f}s")
                return data
        except urllib.error.HTTPError as e:
            elapsed = time.time() - start
            print(f"[HTTP Error {e.code}] {e.reason} (Time: {elapsed:.4f}s)")
            try:
                error_body = e.read().decode('utf-8')
                print(f"Error Body: {error_body}")
            except Exception:
                pass
        except Exception as e:
            elapsed = time.time() - start
            print(f"[System Error] {e} (Time: {elapsed:.4f}s)")
        return None

    # 1. Test district-boundary (First Call)
    safe_request("district-boundary (First Call)", f"{base_url}/district-boundary/1")

    # 2. Test district-boundary (Second Call - Cache Hit)
    safe_request("district-boundary (Second Call - Cache Hit)", f"{base_url}/district-boundary/1")

    # 3. Test national-properties
    safe_request("national-properties", f"{base_url}/national-properties")

    # 4. Test user-exclusions
    safe_request("user-exclusions (Auto-Healing)", f"{base_url}/user-exclusions")

    # 5. Test recommend optimal sites
    safe_request("recommend optimal sites", f"{base_url}/recommend?district_id=1&ref_lat=37.5302&ref_lng=126.9724&limit=3")

if __name__ == "__main__":
    test_api()
