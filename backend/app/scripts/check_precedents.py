from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql+psycopg://Admin:admin1234@localhost:5432/postgres"

def main():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        print("[DB Verify] Peeking verified_precedents...")
        res = conn.execute(text("SELECT id, document_title, actual_scenario, verified_at, LEFT(document_ocr_text, 100) FROM verified_precedents;")).fetchall()
        print(f"[DB Verify] Total precedents found: {len(res)}")
        for r in res:
            print(r)
            
        print("[DB Verify] Peeking decision_histories...")
        res2 = conn.execute(text("SELECT id, region, facility_type, infra, status FROM decision_histories;")).fetchall()
        print(f"[DB Verify] Total decision histories found: {len(res2)}")
        for r2 in res2[:5]:
            print(r2)

if __name__ == "__main__":
    main()
