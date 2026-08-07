import os
import json
import datetime
from sqlalchemy import text
from app.database import engine

def main():
    backup_dir = os.path.join(os.getcwd(), "data", "backup")
    os.makedirs(backup_dir, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = os.path.join(backup_dir, f"omnisite_db_backup_{timestamp}.json")
    sql_path = os.path.join(backup_dir, f"omnisite_db_backup_{timestamp}.sql")

    with engine.connect() as conn:
        tables_res = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
              AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)).fetchall()
        
        tables = [r[0] for r in tables_res]
        print(f"[DB Backup] Found {len(tables)} public tables in PostgreSQL DB.")
        
        backup_data = {}
        sql_lines = [
            f"-- OmniSite PostgreSQL DB Full Schema & Data Backup ({timestamp})",
            "BEGIN;\n"
        ]
        
        for tbl in tables:
            try:
                # Column metadata
                cols_res = conn.execute(text(f"""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = '{tbl}'
                    ORDER BY ordinal_position
                """)).fetchall()
                cols = [c[0] for c in cols_res]
                
                # Rows data
                rows = conn.execute(text(f"SELECT * FROM {tbl}")).fetchall()
                
                serialized_rows = []
                for r in rows:
                    row_dict = {}
                    for col_name, val in zip(cols, r):
                        if val is None:
                            row_dict[col_name] = None
                        elif isinstance(val, (datetime.datetime, datetime.date)):
                            row_dict[col_name] = val.isoformat()
                        else:
                            row_dict[col_name] = str(val)
                    serialized_rows.append(row_dict)
                
                backup_data[tbl] = {
                    "columns": [{"name": c[0], "type": c[1]} for c in cols_res],
                    "row_count": len(rows),
                    "rows": serialized_rows
                }
                print(f"  [OK] [{tbl}] {len(rows)} records backed up.")
                
            except Exception as e:
                print(f"  [FAIL] [{tbl}] Backup warning: {e}")
        
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=2)
            
        print(f"==> DB JSON Backup successfully created at: {json_path}")
        return json_path

if __name__ == "__main__":
    main()
