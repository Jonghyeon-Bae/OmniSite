import sys
import os

sys.path.insert(0, os.path.abspath("."))
from sqlalchemy import text
from app.database import engine

def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        
    print("=== SEED_DB.PY VS LIVE POSTGRESQL DATABASE COMPARISON REPORT ===")
    
    # seed_db.py가 적재하는 핵심 시드 마스터 테이블 및 정량 기대치
    expected_seed_counts = {
        "districts": 1,
        "dong_boundaries": 37,
        "dongs": 15,
        "cadastral_lands": 6524,
        "cadastral_parcels": 6524,
        "commercial_shops": 6509,
        "restricted_zones": 268,
        "transit_stations": 414,
        "transit_passengers": 314,
        "illegal_dumping_zones": 7,
        "population_stats": 38,
        "civil_complaints": 38,
        "district_regulations": 72,
        "domain_regulation_rules": 3,
        "registered_domain_tags": 3,
        "system_notices": 5,
        "community_posts": 6,
        "system_faqs": 20,
        "users": 4,
        "system_settings": 1
    }

    with engine.connect() as conn:
        print(f"\n{'[TABLE NAME]':<25} | {'[SEED EXPECTED]':<15} | {'[LIVE DB COUNT]':<15} | {'[MATCH STATUS]'}")
        print("-" * 75)
        
        all_matched = True
        for tbl, exp_cnt in expected_seed_counts.items():
            try:
                cnt = conn.execute(text(f"SELECT COUNT(*) FROM {tbl}")).scalar()
                status = "MATCH (100% 일치)" if cnt == exp_cnt else f"MISMATCH (차이: {cnt - exp_cnt})"
                if cnt != exp_cnt:
                    all_matched = False
                print(f"{tbl:<25} | {exp_cnt:<15,} | {cnt:<15,} | {status}")
            except Exception as e:
                print(f"{tbl:<25} | {exp_cnt:<15,} | {'ERROR':<15} | {e}")
                all_matched = False

        print("\n--- 런타임 유저 데이터 이력 테이블 (사용자 조작 누적 데이터) ---")
        runtime_tables = ["decision_histories", "pipeline_execution_logs", "user_exclusion_zones", "verified_precedents"]
        for r_tbl in runtime_tables:
            try:
                cnt = conn.execute(text(f"SELECT COUNT(*) FROM {r_tbl}")).scalar()
                print(f"{r_tbl:<25} | 런타임 누적 데이터 | {cnt:<15,} | 정상 보존 중")
            except Exception as e:
                print(f"{r_tbl:<25} | ERROR: {e}")

    print("\n" + "="*75)
    if all_matched:
        print("VERDICT: seed_db.py 시딩 파이프라인 정량 수치와 현재 라이브 DB 데이터가 100% 완벽히 일치합니다!")
    else:
        print("VERDICT: 라이브 DB 수치와 시드 수치 간 일부 미세 차이가 존재합니다.")

if __name__ == "__main__":
    main()
