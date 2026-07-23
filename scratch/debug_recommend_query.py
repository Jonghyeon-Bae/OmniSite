import os
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql+psycopg://Admin:admin1234@localhost:5432/postgres"
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    # 1. Total cadastral_lands count
    total_parcels = conn.execute(text("SELECT count(*) FROM cadastral_lands")).scalar()
    print("Total cadastral_lands in DB:", total_parcels)
    
    # 2. Count by ownership_type
    owners = conn.execute(text("SELECT ownership_type, count(*) FROM cadastral_lands GROUP BY ownership_type")).fetchall()
    print("Ownership types:", owners)
    
    # 3. Check sample cadastral_lands coordinates vs ref_lat/ref_lng
    sample_parcels = conn.execute(text("""
        SELECT id, pnu, jibun, ownership_type, ST_X(ST_Centroid(geom)) as lng, ST_Y(ST_Centroid(geom)) as lat 
        FROM cadastral_lands LIMIT 5
    """)).fetchall()
    print("Sample parcels:", sample_parcels)
    
    # 4. Check restricted_zones count
    rest_cnt = conn.execute(text("SELECT count(*) FROM restricted_zones")).scalar()
    print("Total restricted_zones in DB:", rest_cnt)
