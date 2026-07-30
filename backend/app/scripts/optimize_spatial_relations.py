import sys
import os

# Add the app directory to the system path to allow imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app.database import engine
from sqlalchemy import text
import time

def optimize_spatial_relations():
    """
    1. Adds is_restricted, dist_to_school_m, dist_to_childcare_m to cadastral_lands.
    2. Performs the heavy spatial intersection/distance calculations in batch.
    3. Updates cadastral_lands with the scalar results.
    """
    print("[Spatial Optimizer] Starting offline spatial denormalization...")
    start_time = time.time()
    
    with engine.begin() as conn:
        # Step 1: Add columns if they do not exist
        print("[Spatial Optimizer] Ensuring target columns exist in cadastral_lands...")
        
        check_col = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='cadastral_lands' AND column_name='is_restricted';
        """)
        if not conn.execute(check_col).fetchone():
            conn.execute(text("ALTER TABLE cadastral_lands ADD COLUMN is_restricted BOOLEAN DEFAULT FALSE;"))
            conn.execute(text("ALTER TABLE cadastral_lands ADD COLUMN dist_to_school_m NUMERIC DEFAULT 9999.0;"))
            conn.execute(text("ALTER TABLE cadastral_lands ADD COLUMN dist_to_childcare_m NUMERIC DEFAULT 9999.0;"))
            print("[Spatial Optimizer] Columns added.")
        else:
            # Reset values for a clean run
            conn.execute(text("UPDATE cadastral_lands SET is_restricted = FALSE, dist_to_school_m = 9999.0, dist_to_childcare_m = 9999.0;"))
            print("[Spatial Optimizer] Columns already exist. Reset values to default.")
            
        # Step 2: Compute is_restricted (bridge_tunnel, exclusion, etc.)
        # If a parcel intersects with any restricted_zone of type 'bridge_tunnel', 'exclusion', 'smoking_zone'
        print("[Spatial Optimizer] Calculating 'is_restricted' (Intersection with bridges/tunnels)...")
        update_restricted = text("""
            UPDATE cadastral_lands c
            SET is_restricted = TRUE
            FROM restricted_zones r
            WHERE r.zone_type IN ('bridge_tunnel', 'exclusion', 'smoking_zone')
            AND ST_Intersects(c.geom, r.geom);
        """)
        res1 = conn.execute(update_restricted)
        print(f"[Spatial Optimizer] Marked {res1.rowcount} parcels as restricted.")
        
        # Step 3: Compute dist_to_school_m
        print("[Spatial Optimizer] Calculating 'dist_to_school_m'...")
        update_school = text("""
            WITH nearest_school AS (
                SELECT c.id AS parcel_id, MIN(ST_Distance(c.geom::geography, r.geom::geography)) as min_dist
                FROM cadastral_lands c
                CROSS JOIN LATERAL (
                    SELECT geom FROM restricted_zones 
                    WHERE zone_type = 'school'
                    ORDER BY c.geom <-> geom LIMIT 1
                ) r
                GROUP BY c.id
            )
            UPDATE cadastral_lands c
            SET dist_to_school_m = ns.min_dist
            FROM nearest_school ns
            WHERE c.id = ns.parcel_id;
        """)
        res2 = conn.execute(update_school)
        print(f"[Spatial Optimizer] Updated distance to school for {res2.rowcount} parcels.")
        
        # Step 4: Compute dist_to_childcare_m
        print("[Spatial Optimizer] Calculating 'dist_to_childcare_m'...")
        update_childcare = text("""
            WITH nearest_childcare AS (
                SELECT c.id AS parcel_id, MIN(ST_Distance(c.geom::geography, r.geom::geography)) as min_dist
                FROM cadastral_lands c
                CROSS JOIN LATERAL (
                    SELECT geom FROM restricted_zones 
                    WHERE zone_type = 'childcare'
                    ORDER BY c.geom <-> geom LIMIT 1
                ) r
                GROUP BY c.id
            )
            UPDATE cadastral_lands c
            SET dist_to_childcare_m = ns.min_dist
            FROM nearest_childcare ns
            WHERE c.id = ns.parcel_id;
        """)
        res3 = conn.execute(update_childcare)
        print(f"[Spatial Optimizer] Updated distance to childcare for {res3.rowcount} parcels.")
        
    end_time = time.time()
    print(f"[Spatial Optimizer] Completed successfully in {end_time - start_time:.2f} seconds.")

if __name__ == "__main__":
    optimize_spatial_relations()
