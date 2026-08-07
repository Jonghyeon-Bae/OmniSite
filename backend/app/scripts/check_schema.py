import os
import re
from sqlalchemy import text
from app.database import engine

def main():
    schema_file = os.path.abspath(os.path.join(os.getcwd(), "..", "DB", "init", "01_schema.sql"))
    if not os.path.exists(schema_file):
        print(f"[Schema Check Error] Schema file not found at: {schema_file}")
        return

    with open(schema_file, "r", encoding="utf-8") as f:
        sql_content = f.read()

    # Extract table names from CREATE TABLE statements in sql
    schema_tables = set(re.findall(r"CREATE\ TABLE\ (?:IF\ NOT\ EXISTS\ )?([a-zA-Z0-9_]+)", sql_content, re.IGNORECASE))
    
    with engine.connect() as conn:
        db_tables_res = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE'")).fetchall()
        db_tables = set([r[0] for r in db_tables_res if r[0] != 'spatial_ref_sys'])

    print(f"==> Schema File Defined Tables ({len(schema_tables)}): {sorted(list(schema_tables))}")
    print(f"==> Actual DB Live Tables ({len(db_tables)}): {sorted(list(db_tables))}")

    missing_in_schema = db_tables - schema_tables
    missing_in_db = schema_tables - db_tables

    if missing_in_schema:
        print(f"[MISSING IN SCHEMA] Tables in Live DB but missing in 01_schema.sql: {sorted(list(missing_in_schema))}")
        with engine.connect() as conn:
            for tbl in missing_in_schema:
                cols = conn.execute(text(f"SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name = '{tbl}' ORDER BY ordinal_position")).fetchall()
                print(f"\n--- Definition for table '{tbl}' ---")
                for c in cols:
                    print(f"  {c[0]} {c[1]} (Nullable: {c[2]})")
    else:
        print("[OK] All Live DB tables are represented in 01_schema.sql!")

    if missing_in_db:
        print(f"[MISSING IN DB] Tables in 01_schema.sql but missing in Live DB: {sorted(list(missing_in_db))}")
    else:
        print("[OK] All 01_schema.sql tables exist in Live DB!")

if __name__ == "__main__":
    main()
