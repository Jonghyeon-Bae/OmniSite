from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql+psycopg://Admin:admin1234@localhost:5432/postgres"

def main():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        print("[DB Direct Insert] Trying to insert into verified_precedents...")
        try:
            conn.execute(
                text("""
                    INSERT INTO verified_precedents (conflict_simulation_id, document_title, document_ocr_text, actual_scenario)
                    VALUES (NULL, 'direct_test_precedent.pdf', 'Direct insert test text content.', '시나리오 A (정당 규정 완전 부합 준공)');
                """)
            )
            conn.commit()
            print("[DB Direct Insert] Insert completed and committed successfully!")
        except Exception as e:
            conn.rollback()
            print(f"[DB Direct Insert] Insert FAILED: {e}")

if __name__ == "__main__":
    main()
