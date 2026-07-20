import os
import json
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql+psycopg://Admin:admin1234@localhost:5432/postgres"

def main():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        print("[Migration] Dropping decision_histories if exists...")
        conn.execute(text("DROP TABLE IF EXISTS decision_histories CASCADE;"))
        
        print("[Migration] Creating table decision_histories...")
        conn.execute(text("""
            CREATE TABLE decision_histories (
                id SERIAL PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                region VARCHAR(250) NOT NULL,
                facility_type VARCHAR(50) NOT NULL,
                infra VARCHAR(100) NOT NULL,
                pnu_count INTEGER NOT NULL DEFAULT 1,
                status VARCHAR(50) NOT NULL,
                audit_state VARCHAR(50) NOT NULL,
                audit_opinion TEXT,
                inferred_purpose VARCHAR(250),
                ahp_weights JSONB,
                selected_parcel_jibun VARCHAR(250),
                selected_parcel_price BIGINT,
                selected_parcel_area NUMERIC,
                selected_parcel_css INTEGER,
                debate_logs JSONB
            );
        """))
        
        print("[Migration] Table creation completed successfully without dummy seed data!")

if __name__ == "__main__":
    main()
