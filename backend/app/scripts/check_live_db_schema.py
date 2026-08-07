import sys
import os

sys.path.insert(0, os.path.abspath("."))
from sqlalchemy import text
from app.database import engine

def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        
    with engine.connect() as conn:
        tables = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name")).fetchall()
        print("=== LIVE POSTGRESQL DATABASE INSPECTION SUMMARY ===")
        for t_row in tables:
            t_name = t_row[0]
            cnt = conn.execute(text(f"SELECT COUNT(*) FROM {t_name}")).scalar()
            cols = conn.execute(text(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{t_name}' ORDER BY ordinal_position")).fetchall()
            col_info = [f"{c[0]} ({c[1]})" for c in cols]
            print(f"\n[TABLE] {t_name} -> Total Rows: {cnt:,}")
            print(f"        Columns ({len(col_info)}): {', '.join(col_info)}")

if __name__ == "__main__":
    main()
