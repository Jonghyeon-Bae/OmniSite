import os
import sys
from sqlalchemy import create_engine, text

# Add backend directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

def test_db():
    # Read backend/.env manually if needed
    env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))
    db_url = "postgresql+psycopg://Admin:admin1234@localhost:5432/postgres"
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("DATABASE_URL="):
                    db_url = line.split("DATABASE_URL=")[1].strip()
                    break

    print(f"Connecting to database with URL: {db_url}")
    try:
        engine = create_engine(db_url)
        with engine.connect() as conn:
            # 1. PostGIS Version
            try:
                postgis_ver = conn.execute(text("SELECT PostGIS_Full_Version();")).scalar()
                print(f"[Success] PostGIS Version: {postgis_ver}")
            except Exception as e:
                print(f"[Error] Failed to select PostGIS version: {e}")

            # 2. Check major spatial tables
            tables = ["cadastral_lands", "user_exclusion_zones", "restricted_zones", "districts"]
            for table in tables:
                try:
                    cnt = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                    print(f"[Success] Table '{table}' exists. Count = {cnt}")
                except Exception as e:
                    print(f"[Error] Table '{table}' check failed: {e}")

            # 3. Check spatial column type & index of cadastral_lands
            try:
                res = conn.execute(text("""
                    SELECT column_name, data_type, udt_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'cadastral_lands' AND column_name = 'geom';
                """)).fetchone()
                print(f"[Success] cadastral_lands.geom column: {res}")
            except Exception as e:
                print(f"[Error] cadastral_lands geom column check failed: {e}")

    except Exception as e:
        print(f"[Critical Error] Database connection failed: {e}")

if __name__ == "__main__":
    test_db()
