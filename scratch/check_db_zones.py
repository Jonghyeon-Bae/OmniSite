import os
import psycopg
from dotenv import load_dotenv

load_dotenv('backend/.env')
db_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/omnisite_db')
db_url = db_url.replace('postgresql+psycopg://', 'postgresql://')

with psycopg.connect(db_url) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM cadastral_lands;")
        total_parcels = cur.fetchone()[0]
        
        cur.execute("SELECT ownership_type, COUNT(*) FROM cadastral_lands GROUP BY ownership_type;")
        ownership_stats = cur.fetchall()
        
        cur.execute("SELECT dong_name, COUNT(*) FROM dong_boundaries GROUP BY dong_name;")
        dongs = cur.fetchall()
        
        print(f"Total Parcels: {total_parcels}")
        print(f"Ownership Breakdown: {ownership_stats}")
        print(f"Total Dongs Count: {len(dongs)}")
        print(f"Sample Dongs: {dongs[:10]}")
