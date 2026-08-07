import os
import sys
import time
from sqlalchemy import create_engine, text

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

def test_queries():
    env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))
    db_url = "postgresql+psycopg://Admin:admin1234@localhost:5432/postgres"
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("DATABASE_URL="):
                    db_url = line.split("DATABASE_URL=")[1].strip()
                    break

    print(f"Connecting to: {db_url}")
    engine = create_engine(db_url)
    with engine.connect() as conn:
        # 1. Check ownership distribution
        print("\n--- 1. Ownership Type Distribution ---")
        try:
            res = conn.execute(text("SELECT ownership_type, COUNT(*) FROM cadastral_lands GROUP BY ownership_type;")).fetchall()
            for r in res:
                print(f"ownership_type: {r[0]}, count: {r[1]}")
        except Exception as e:
            print(f"Failed to query ownership distribution: {e}")

        # 2. Check national properties count
        print("\n--- 2. National Properties (ownership_type = '국유지') Count ---")
        try:
            cnt = conn.execute(text("SELECT COUNT(*) FROM cadastral_lands WHERE district_id = 1 AND ownership_type = '국유지';")).scalar()
            print(f"Count: {cnt}")
        except Exception as e:
            print(f"Failed to query national properties count: {e}")

        # 3. Test Concave Hull query performance and validity
        print("\n--- 3. Testing District Boundary ST_ConcaveHull Query ---")
        start = time.time()
        try:
            query = text("SELECT ST_AsGeoJSON(ST_ConcaveHull(ST_Collect(ST_MakeValid(geom)), 0.65)) FROM cadastral_lands")
            res_str = conn.execute(query).scalar()
            end = time.time()
            elapsed = end - start
            print(f"ConcaveHull Query Succeeded. Elapsed time: {elapsed:.3f}s")
            print(f"Result length: {len(res_str) if res_str else 0}")
            if res_str:
                print(f"Result preview: {res_str[:200]}...")
            else:
                print("Result is NULL!")
        except Exception as e:
            end = time.time()
            elapsed = end - start
            print(f"ConcaveHull Query Failed in {elapsed:.3f}s. Error: {e}")

        # 4. Test Convex Hull fallback query
        print("\n--- 4. Testing Fallback ST_ConvexHull Query ---")
        start = time.time()
        try:
            query = text("SELECT ST_AsGeoJSON(ST_ConvexHull(ST_Collect(geom))) FROM cadastral_lands")
            res_str = conn.execute(query).scalar()
            end = time.time()
            elapsed = end - start
            print(f"ConvexHull Query Succeeded. Elapsed time: {elapsed:.3f}s")
            print(f"Result length: {len(res_str) if res_str else 0}")
        except Exception as e:
            end = time.time()
            elapsed = end - start
            print(f"ConvexHull Query Failed in {elapsed:.3f}s. Error: {e}")

if __name__ == "__main__":
    test_queries()
