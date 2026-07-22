import os
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql+psycopg://Admin:admin1234@localhost:5432/postgres"

def main():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        print("[Fix DDL] Reinforcing all potential missing columns in decision_histories...")
        conn.execute(text("ALTER TABLE decision_histories ADD COLUMN IF NOT EXISTS region VARCHAR(250);"))
        conn.execute(text("ALTER TABLE decision_histories ADD COLUMN IF NOT EXISTS facility_type VARCHAR(50);"))
        conn.execute(text("ALTER TABLE decision_histories ADD COLUMN IF NOT EXISTS infra VARCHAR(100);"))
        conn.execute(text("ALTER TABLE decision_histories ADD COLUMN IF NOT EXISTS pnu_count INTEGER DEFAULT 1;"))
        conn.execute(text("ALTER TABLE decision_histories ADD COLUMN IF NOT EXISTS status VARCHAR(50);"))
        conn.execute(text("ALTER TABLE decision_histories ADD COLUMN IF NOT EXISTS audit_state VARCHAR(50);"))
        conn.execute(text("ALTER TABLE decision_histories ADD COLUMN IF NOT EXISTS audit_opinion TEXT;"))
        conn.execute(text("ALTER TABLE decision_histories ADD COLUMN IF NOT EXISTS inferred_purpose VARCHAR(250);"))
        conn.execute(text("ALTER TABLE decision_histories ADD COLUMN IF NOT EXISTS ahp_weights JSONB;"))
        conn.execute(text("ALTER TABLE decision_histories ADD COLUMN IF NOT EXISTS selected_parcel_jibun VARCHAR(250);"))
        conn.execute(text("ALTER TABLE decision_histories ADD COLUMN IF NOT EXISTS selected_parcel_pnu VARCHAR(50);"))
        conn.execute(text("ALTER TABLE decision_histories ADD COLUMN IF NOT EXISTS selected_parcel_price BIGINT;"))
        conn.execute(text("ALTER TABLE decision_histories ADD COLUMN IF NOT EXISTS selected_parcel_area NUMERIC;"))
        conn.execute(text("ALTER TABLE decision_histories ADD COLUMN IF NOT EXISTS selected_parcel_css INTEGER;"))
        conn.execute(text("ALTER TABLE decision_histories ADD COLUMN IF NOT EXISTS debate_logs JSONB;"))
        
        # verified_precedents 테이블의 외래키 제약조건을 완전히 제거하여 가상 모의 데이터와 실 데이터 간 참조 무결성 충돌 차단
        print("[Fix DDL] Decoupling verified_precedents foreign key constraint...")
        conn.execute(text("ALTER TABLE verified_precedents DROP CONSTRAINT IF EXISTS verified_precedents_conflict_simulation_id_fkey;"))
        conn.execute(text("ALTER TABLE verified_precedents ALTER COLUMN conflict_simulation_id DROP NOT NULL;"))
        conn.execute(text("ALTER TABLE verified_precedents ADD COLUMN IF NOT EXISTS selected_parcel_pnu VARCHAR(50);"))
        conn.execute(text("ALTER TABLE verified_precedents ADD COLUMN IF NOT EXISTS match_score INTEGER DEFAULT 100;"))
        conn.execute(text("ALTER TABLE verified_precedents ADD COLUMN IF NOT EXISTS audit_opinion TEXT;"))
        
        # pgvector district_regulations 테이블의 잘못된 btree INCLUDE 인덱스 수정 (로우 크기 초과 방지)
        print("[Fix DDL] Repairing district_regulations btree index to exclude vector column...")
        conn.execute(text("DROP INDEX IF EXISTS idx_regulations_district_category_vector;"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_regulations_district_category_vector ON district_regulations (district_id, category);"))
        conn.commit()
        print("[Fix DDL] Column and foreign keys repaired successfully!")

if __name__ == "__main__":
    main()
