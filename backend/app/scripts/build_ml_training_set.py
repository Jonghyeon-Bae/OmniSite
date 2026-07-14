# -*- coding: utf-8 -*-
import os
import csv
from sqlalchemy import create_engine, text

print("=== [PHASE 1: STARTING PURE-PYTHON CSS ML DATASET BUILDER V4] ===")

DATABASE_URL = "postgresql+psycopg://Admin:admin1234@localhost:5432/postgres"
engine = create_engine(DATABASE_URL)

output_dir = "backend/data/processed"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)
    print(f"Created processed data folder: {output_dir}")

output_file = os.path.join(output_dir, "css_train_dataset.csv")

# Balanced labeling thresholds based on empirical percentile stats:
# complaint_count >= 120 -> Y=1 (Conflict / Top 45% percentile)
# complaint_count <= 95 -> Y=0 (Peace / Bottom 30% percentile)
query = text("""
    WITH nearest_school AS (
        SELECT DISTINCT ON (c.id)
            c.id AS parcel_id,
            ST_Distance(ST_Centroid(c.geom)::geography, rz.geom::geography) AS dist_to_school
        FROM cadastral_lands c
        CROSS JOIN LATERAL (
            SELECT geom FROM restricted_zones 
            WHERE zone_type = 'school' 
            ORDER BY ST_Centroid(c.geom) <-> geom 
            LIMIT 1
        ) rz
        WHERE c.district_id = 1
    ),
    nearest_childcare AS (
        SELECT DISTINCT ON (c.id)
            c.id AS parcel_id,
            ST_Distance(ST_Centroid(c.geom)::geography, rz.geom::geography) AS dist_to_childcare
        FROM cadastral_lands c
        CROSS JOIN LATERAL (
            SELECT geom FROM restricted_zones 
            WHERE zone_type = 'childcare_center' 
            ORDER BY ST_Centroid(c.geom) <-> geom 
            LIMIT 1
        ) rz
        WHERE c.district_id = 1
    )
    SELECT 
        c.id AS parcel_id,
        c.pnu,
        c.jibun,
        c.land_use_code,
        c.ownership_type,
        ST_Area(c.geom::geography) AS area,
        ST_X(ST_Centroid(c.geom)) AS lng,
        ST_Y(ST_Centroid(c.geom)) AS lat,
        COALESCE(ns.dist_to_school, 9999.0) AS dist_to_school,
        COALESCE(nc.dist_to_childcare, 9999.0) AS dist_to_childcare,
        COALESCE(cc.complaint_count, 0) AS complaint_count,
        -- Balanced split
        CASE 
            WHEN COALESCE(cc.complaint_count, 0) >= 120 THEN 1
            WHEN COALESCE(cc.complaint_count, 0) <= 95 THEN 0
            ELSE -1
        END AS target_label
    FROM cadastral_lands c
    LEFT JOIN nearest_school ns ON c.id = ns.parcel_id
    LEFT JOIN nearest_childcare nc ON c.id = nc.parcel_id
    LEFT JOIN civil_complaints cc ON c.dong_id = cc.dong_id
    WHERE c.district_id = 1
      AND c.ownership_type IN (:owner_1, :owner_2, :owner_3)
      AND ST_IsValid(c.geom);
""")

print("Querying PostGIS spatial databases with balanced bindings...")
try:
    with engine.connect() as conn:
        result = conn.execute(query, {
            "owner_1": "국유지",
            "owner_2": "시유지",
            "owner_3": "구유지"
        })
        headers = list(result.keys())
        
        total_rows = 0
        labeled_rows = 0
        class_counts = {0: 0, 1: 0}
        
        with open(output_file, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            
            for row in result:
                total_rows += 1
                row_dict = dict(zip(headers, row))
                label = row_dict["target_label"]
                
                if label != -1:
                    writer.writerow(list(row))
                    labeled_rows += 1
                    class_counts[label] = class_counts.get(label, 0) + 1
                    
        print(f"Total rows retrieved: {total_rows}")
        print(f"Filtered to labeled cases. Training samples: {labeled_rows}")
        print(f"Class distribution: {class_counts}")
        print(f"SUCCESS: Saved training dataset to: {output_file}")
        
except Exception as e:
    print(f"Error during dataset extraction: {e}")
    exit(1)
