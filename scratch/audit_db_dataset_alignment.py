import os
import sys
from sqlalchemy import create_engine, text

sys.stdout.reconfigure(encoding='utf-8')

sys.path.append("backend")
from app.database import engine

print("========================================================")
print(" [DB vs Essential Dataset Audit Engine]")
print("========================================================")

essential_dir = r"C:\Users\Admin\Desktop\빅프로젝트 관련자료\최종1차\데이터\최초 ColdStart를 위한 데이터셋\필수데이터"

with engine.connect() as conn:
    tables = [
        "districts",
        "dong_boundaries",
        "cadastral_lands",
        "building_ledgers",
        "restricted_zones",
        "transit_stations",
        "transit_passengers",
        "population_stats",
        "commercial_shops",
        "civil_complaints"
    ]
    
    print("\n[1] Current PostgreSQL Table Counts:")
    for t in tables:
        try:
            cnt = conn.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
            print(f"  - Table '{t}': {cnt:,} rows")
        except Exception as e:
            print(f"  - Table '{t}': ERROR ({e})")
            
    print("\n[2] Checking Specific Essential File Load Status:")
    
    # Check 11. 국유부동산정보.csv
    national_prop_csv = os.path.join(essential_dir, "cadastral_lands", "11. 국유부동산정보.csv")
    print(f"\n  - File: 'cadastral_lands/11. 국유부동산정보.csv'")
    if os.path.exists(national_prop_csv):
        print(f"    Exist: YES ({os.path.getsize(national_prop_csv):,} bytes)")
    else:
        print(f"    Exist: NO")
        
    # Check 용산구 건축물대장 표제부.csv
    bldg_csv = os.path.join(essential_dir, "cadastral_lands", "용산구 건축물대장 표제부.csv")
    print(f"\n  - File: 'cadastral_lands/용산구 건축물대장 표제부.csv'")
    if os.path.exists(bldg_csv):
        print(f"    Exist: YES ({os.path.getsize(bldg_csv):,} bytes)")
    else:
        print(f"    Exist: NO")
        
    # Check restricted_zones files
    rz_dir = os.path.join(essential_dir, "restricted_zones")
    print(f"\n  - Directory: 'restricted_zones/' ({len(os.listdir(rz_dir))} files)")
    for f in os.listdir(rz_dir):
        print(f"    - {f}")

