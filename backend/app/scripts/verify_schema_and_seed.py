import sys
import os

sys.path.insert(0, os.path.abspath("."))
from sqlalchemy import text
from app.database import engine

def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        
    sql_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "DB", "init", "01_schema.sql")
    sql_path = os.path.abspath(sql_path)
    
    print(f"=== CHECKING DDL SCHEMA FILE: {sql_path} ===")
    if not os.path.exists(sql_path):
        print(f"[ERROR] 01_schema.sql not found at {sql_path}")
        return

    with open(sql_path, "r", encoding="utf-8") as f:
        sql_content = f.read()

    # 테이블 목록 추출
    ddl_tables = []
    for line in sql_content.splitlines():
        line_str = line.strip()
        if line_str.upper().startswith("CREATE TABLE"):
            parts = line_str.split()
            if len(parts) >= 3:
                tbl = parts[2] if parts[2].upper() != "IF" else parts[5]
                tbl = tbl.replace("(", "").strip()
                ddl_tables.append(tbl)

    print(f"Found {len(ddl_tables)} tables defined in 01_schema.sql:")
    print(", ".join(sorted(ddl_tables)))

    # DB 테이블과 비교
    with engine.connect() as conn:
        db_tables = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")).fetchall()
        db_table_names = set(t[0] for t in db_tables)

    missing_in_db = set(ddl_tables) - db_table_names
    missing_in_sql = db_table_names - set(ddl_tables) - {"spatial_ref_sys", "geometry_columns", "geography_columns"}

    print("\n--- SCHEMA SYNC CHECK RESULTS ---")
    if missing_in_db:
        print(f"[WARN] Tables defined in 01_schema.sql but missing in DB: {missing_in_db}")
    else:
        print("[SUCCESS] All tables in 01_schema.sql exist in live DB!")

    if missing_in_sql:
        print(f"[WARN] Tables present in live DB but missing in 01_schema.sql: {missing_in_sql}")
    else:
        print("[SUCCESS] All live DB tables are fully documented in 01_schema.sql!")

if __name__ == "__main__":
    main()
