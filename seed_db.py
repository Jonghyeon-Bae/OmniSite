import os
import csv
import re
import math
import shapefile
import bcrypt
from collections import defaultdict
from sqlalchemy import create_engine, text
from shapely.geometry import Polygon, MultiPolygon, shape

DATABASE_URL = "postgresql+psycopg://Admin:admin1234@localhost:5432/postgres"
engine = create_engine(DATABASE_URL)

def resolve_path(key, default_fallback):
    if os.path.exists(default_fallback):
        return default_fallback
    # Resolve package paths relative to seed_db.py
    pkg_base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "데이터", "최초 ColdStart를 위한 데이터셋"))
    pkg_essential = os.path.join(pkg_base, "필수데이터")
    
    mapping = {
        "dong_mapping": os.path.join(pkg_essential, "dong_boundaries", "용산구_법정동_행정동_연계매핑.csv"),
        "parcels": os.path.join(pkg_essential, "cadastral_lands", "05.용산구_부지면적_좌표(흡연부스 후보).csv"),
        "bus_stations": os.path.join(pkg_essential, "transit_stations", "서울시 버스정류소 위치정보.csv"),
        "subway_stations": os.path.join(pkg_essential, "transit_stations", "서울시 역사마스터 정보.csv"),
        "bus_passengers": os.path.join(pkg_essential, "transit_passangers", "BUS_STATION_BOARDING_MONTH_202605.csv"),
        "subway_passengers": os.path.join(pkg_essential, "transit_passangers", "CARD_SUBWAY_MONTH_202605.csv"),
        "illegal_dumping": os.path.join(pkg_essential, "restricted_zones", "07. 담배꽁초_상습_무단투기.csv"),
        "local_population": os.path.join(pkg_essential, "population_stats", "LOCAL_PEOPLE_DONG_202605_YONGSAN.csv"),
        "restricted_zones": os.path.join(pkg_essential, "restricted_zones", "서울시 금연구역  정보(표준 데이터).csv"),
    }
    if key in mapping and os.path.exists(mapping[key]):
        return mapping[key]
    return default_fallback

sources = {
    "dong_mapping": resolve_path("dong_mapping", r"c:\Users\Admin\Desktop\빅프로젝트 관련자료\최종1차\데이터\정리데이터\용산구_법정동_행정동_연계매핑.csv"),
    "parcels": resolve_path("parcels", r"c:\Users\Admin\Desktop\빅프로젝트 관련자료\최종1차\데이터\0706 정제데이터\01.정제데이터\05.용산구_부지면적_좌표(흡연부스 후보).csv"),
    "bus_stations": resolve_path("bus_stations", r"c:\Users\Admin\Desktop\빅프로젝트 관련자료\최종1차\데이터\정리데이터\서울시 버스정류소 위치정보_YONGSAN.csv"),
    "subway_stations": resolve_path("subway_stations", r"c:\Users\Admin\Desktop\빅프로젝트 관련자료\최종1차\데이터\0706 정제데이터\01.정제데이터\02. 지하철역 위치.csv"),
    "bus_passengers": resolve_path("bus_passengers", r"c:\Users\Admin\Desktop\빅프로젝트 관련자료\최종1차\데이터\정리데이터\BUS_STATION_BOARDING_MONTH_202605_YONGSAN.csv"),
    "subway_passengers": resolve_path("subway_passengers", r"c:\Users\Admin\Desktop\빅프로젝트 관련자료\최종1차\데이터\정리데이터\CARD_SUBWAY_MONTH_202605_YONGSAN.csv"),
    "illegal_dumping": resolve_path("illegal_dumping", r"c:\Users\Admin\Desktop\빅프로젝트 관련자료\최종1차\데이터\0706 정제데이터\01.정제데이터\07. 담배꽁초_상습_무단투기.csv"),
    "local_population": resolve_path("local_population", r"c:\Users\Admin\Desktop\빅프로젝트 관련자료\최종1차\데이터\정리데이터\LOCAL_PEOPLE_DONG_202605_YONGSAN_PEAK.csv"),
    "restricted_zones": resolve_path("restricted_zones", r"c:\Users\Admin\Desktop\빅프로젝트 관련자료\최종1차\데이터\0706 정제데이터\01.정제데이터\06. 06-07 금연구역 통합본.csv")
}

def load_csv_data(path, encodings=None):
    if not encodings:
        encodings = ["cp949", "utf-8-sig", "utf-8", "euc-kr"]
    for enc in encodings:
        try:
            with open(path, "r", encoding=enc) as f:
                reader = csv.reader(f)
                headers = next(reader)
                rows = list(reader)
                # Verify if there are decoding replacement characters '\ufffd'
                sample = "".join(headers[:3]) + "".join(r[1] for r in rows[:5] if len(r) > 1)
                if "\ufffd" in sample:
                    continue
                return [h.strip() for h in headers], [[val.strip() for val in r] for r in rows]
        except Exception:
            continue
    raise ValueError(f"Failed to read file {path} with any encoding")

def normalize_subway_name(name):
    name = re.sub(r"\(.*\)", "", name).strip()
    if name.endswith("역") and len(name) >= 3:
        name = name[:-1]
    return name

def seed():
    print("[1] Connecting to database...")
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            # 1. Truncate target tables
            print("[2] Truncating target tables...")
            conn.execute(text("""
                TRUNCATE TABLE 
                    transit_passengers, 
                    transit_stations, 
                    civil_complaints, 
                    illegal_dumping_zones, 
                    population_stats, 
                    age_demographics, 
                    cadastral_lands, 
                    restricted_zones, 
                    dong_boundaries 
                CASCADE;
            """))
            
            # 2. Insert Yongsan-gu district
            print("[3] Seeding districts...")
            district_id = conn.execute(text("""
                INSERT INTO districts (id, district_name, sig_cd) 
                VALUES (1, '용산구', '11170') 
                ON CONFLICT (sig_cd) DO UPDATE SET district_name = '용산구' 
                RETURNING id;
            """)).scalar()
            
            # 3. Load dong mapping and insert dong boundaries using real shapefile EMD boundaries
            print("[4] Seeding dong_boundaries (Importing real Legal Dong boundaries from emd.shp)...")
            mapping_headers, mapping_rows = load_csv_data(sources["dong_mapping"])
            
            # Find unique legal dongs (법정동) mappings
            unique_leg_dongs = {}
            adm_to_leg = {} # 행정동코드 (8-digit) -> list of 법정동코드 (10-digit)
            leg_to_adm = {} # 법정동코드 -> 행정동코드
            
            for row in mapping_rows:
                if not row or len(row) < 4:
                    continue
                adm_code = row[0][:8] # use 8-digit code
                adm_name = row[1]
                leg_code = row[2]
                leg_name = row[3]
                
                unique_leg_dongs[leg_code] = leg_name
                leg_to_adm[leg_code] = adm_code
                if adm_code not in adm_to_leg:
                    adm_to_leg[adm_code] = []
                if leg_code not in adm_to_leg[adm_code]:
                    adm_to_leg[adm_code].append(leg_code)
            
            # Load real shapefile and insert
            shp_path = r"c:\Users\Admin\Desktop\빅프로젝트 관련자료\최종1차\데이터\emd"
            sf = shapefile.Reader(shp_path, encoding="cp949")
            
            dong_db_map = {} # leg_code -> db ID
            dong_centroids = {} # db_id -> (lng, lat) for fallback
            
            for i in range(len(sf)):
                rec = sf.record(i)
                emd_cd = rec["EMD_CD"]
                if emd_cd.startswith("11170"):
                    leg_code = emd_cd + "00" # 10-digit code
                    name = rec["EMD_KOR_NM"]
                    geom = shape(sf.shape(i))
                    wkt = geom.wkt
                    
                    db_id = conn.execute(text("""
                        INSERT INTO dong_boundaries (district_id, dong_code, dong_name, geom)
                        VALUES (:district_id, :dong_code, :dong_name, ST_Multi(ST_Transform(ST_GeomFromText(:wkt, 5179), 4326)))
                        RETURNING id
                    """), {
                        "district_id": district_id,
                        "dong_code": leg_code,
                        "dong_name": name,
                        "wkt": wkt
                    }).scalar()
                    
                    dong_db_map[leg_code] = db_id
                    
                    # Store centroid for distance fallback
                    centroid_pt = geom.centroid
                    # Transform centroid coordinates from 5179 to 4326
                    c_pt_res = conn.execute(text("""
                        SELECT ST_X(ST_Transform(ST_SetSRID(ST_MakePoint(:x, :y), 5179), 4326)) AS lng,
                               ST_Y(ST_Transform(ST_SetSRID(ST_MakePoint(:x, :y), 5179), 4326)) AS lat
                    """), {"x": centroid_pt.x, "y": centroid_pt.y}).fetchone()
                    
                    dong_centroids[db_id] = (c_pt_res[0], c_pt_res[1])
            
            print(f"    Seeded {len(dong_db_map)} Legal Dong boundaries from shapefile.")

            def get_dong_by_coord(lng, lat):
                res = conn.execute(text("""
                    SELECT id, dong_name, dong_code 
                    FROM dong_boundaries 
                    WHERE ST_Contains(geom, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)) 
                    LIMIT 1
                """), {"lng": lng, "lat": lat}).fetchone()
                
                if res:
                    return res[0], res[1], res[2]
                
                # Fallback to nearest dong centroid
                min_dist = float('inf')
                best_id = list(dong_centroids.keys())[0]
                for db_id, (clng, clat) in dong_centroids.items():
                    dist = (lng - clng)**2 + (lat - clat)**2
                    if dist < min_dist:
                        min_dist = dist
                        best_id = db_id
                        
                res_fallback = conn.execute(text("""
                    SELECT dong_name, dong_code FROM dong_boundaries WHERE id = :id
                """), {"id": best_id}).fetchone()
                return best_id, res_fallback[0], res_fallback[1]

            # 4. Load parcels and seed cadastral_lands
            print("[5] Seeding cadastral_lands...")
            try:
                parcel_headers, parcel_rows = load_csv_data(sources["parcels"])
                parcel_count = 0
                for row in parcel_rows:
                    if not row or len(row) < 8:
                        continue
                    pnu = row[0]
                    jibun_raw = row[1]
                    land_use = row[2]
                    area = float(row[3])
                    buysable = row[4] # 'TRUE' or 'FALSE'
                    lng = float(row[5])
                    lat = float(row[6])
                    wkt = row[7]
                    
                    # Check coordinate validity
                    if not (33.0 <= lat <= 39.0 and 124.0 <= lng <= 132.0):
                        continue
                    
                    # Determine dong using real spatial boundaries
                    dong_id, dong_name, dong_code = get_dong_by_coord(lng, lat)
                    ownership = "국유지" if buysable == "TRUE" else "사유지"
                    formatted_jibun = f"{dong_name} {jibun_raw}"
                    
                    conn.execute(text("""
                        INSERT INTO cadastral_lands (district_id, dong_id, pnu, jibun, land_use_code, ownership_type, geom)
                        VALUES (:district_id, :dong_id, :pnu, :jibun, :land_use_code, :ownership_type, ST_Multi(ST_GeomFromText(:wkt, 4326)))
                    """), {
                        "district_id": district_id,
                        "dong_id": dong_id,
                        "pnu": pnu,
                        "jibun": formatted_jibun,
                        "land_use_code": land_use,
                        "ownership_type": ownership,
                        "wkt": wkt
                    })
                    parcel_count += 1
                print(f"    Seeded {parcel_count} cadastral land parcels.")
            except Exception as e:
                print(f"    [Skipped] cadastral_lands seeding skipped (source file missing or error): {e}")

            # 5. Load and seed transit_stations (Bus and Subway)
            print("[6] Seeding transit_stations...")
            station_db_map = {} # Standard ID -> station ID
            subway_db_map = {} # Normalized Station Name -> station ID
            
            # A. Bus Stations
            try:
                with open(sources["bus_stations"], "rb") as f:
                    bus_content = f.read()
                if bus_content.startswith(b'\xff'):
                    bus_content = bus_content[1:]
                bus_text = bus_content.decode('cp949', errors='replace')
                bus_lines = bus_text.splitlines()
                bus_reader = csv.reader(bus_lines)
                bus_headers = [h.strip() for h in next(bus_reader)]
                
                bus_count = 0
                for row in bus_reader:
                    if not row or len(row) < 6:
                        continue
                    station_no = row[1] # 표준 정류소번호
                    station_name = row[2]
                    try:
                        lng = float(row[3])
                        lat = float(row[4])
                    except ValueError:
                        continue
                    
                    dong_id, _, _ = get_dong_by_coord(lng, lat)
                    
                    station_id = conn.execute(text("""
                        INSERT INTO transit_stations (district_id, dong_id, station_no, station_name, transit_type, geom)
                        VALUES (:district_id, :dong_id, :station_no, :station_name, 'BUS', ST_SetSRID(ST_MakePoint(:lng, :lat), 4326))
                        ON CONFLICT (station_no) DO UPDATE SET station_name = EXCLUDED.station_name
                        RETURNING id
                    """), {
                        "district_id": district_id,
                        "dong_id": dong_id,
                        "station_no": station_no,
                        "station_name": station_name,
                        "lng": lng,
                        "lat": lat
                    }).scalar()
                    station_db_map[station_no] = station_id
                    bus_count += 1
                print(f"    Seeded {bus_count} BUS stations.")
            except Exception as e:
                print(f"    [Skipped] BUS stations seeding skipped: {e}")
                
            # B. Subway Stations
            try:
                subway_headers, subway_rows = load_csv_data(sources["subway_stations"])
                subway_count = 0
                for row in subway_rows:
                    if not row or len(row) < 4:
                        continue
                    station_name = row[0]
                    exit_no = row[1]
                    try:
                        lng = float(row[2])
                        lat = float(row[3])
                    except ValueError:
                        continue
                        
                    dong_id, _, _ = get_dong_by_coord(lng, lat)
                    station_no = f"SUBWAY_{station_name}_{exit_no}"
                    
                    station_id = conn.execute(text("""
                        INSERT INTO transit_stations (district_id, dong_id, station_no, station_name, transit_type, geom)
                        VALUES (:district_id, :dong_id, :station_no, :station_name, 'SUBWAY', ST_SetSRID(ST_MakePoint(:lng, :lat), 4326))
                        ON CONFLICT (station_no) DO UPDATE SET station_name = EXCLUDED.station_name
                        RETURNING id
                    """), {
                        "district_id": district_id,
                        "dong_id": dong_id,
                        "station_no": station_no,
                        "station_name": station_name,
                        "lng": lng,
                        "lat": lat
                    }).scalar()
                    
                    norm_name = normalize_subway_name(station_name)
                    subway_db_map[norm_name] = station_id
                    subway_count += 1
                print(f"    Seeded {subway_count} SUBWAY stations/exits.")
            except Exception as e:
                print(f"    [Skipped] SUBWAY stations seeding skipped: {e}")

            # 6. Seed transit_passengers (Bus and Subway)
            print("[7] Seeding transit_passengers...")
            # A. Bus Passengers
            try:
                bus_pass_headers, bus_pass_rows = load_csv_data(sources["bus_passengers"])
                bus_passenger_totals = defaultdict(list) # standard_id -> list of (board, alight)
                for row in bus_pass_rows:
                    if not row or len(row) < 8:
                        continue
                    std_id = row[3] # 표준버스정류장ID
                    try:
                        board = int(row[6])
                        alight = int(row[7])
                    except ValueError:
                        continue
                    pop_pair = (board, alight)
                    bus_passenger_totals[std_id].append(pop_pair)
                    
                bus_pass_count = 0
                for std_id, totals in bus_passenger_totals.items():
                    if std_id in station_db_map:
                        board_sum = sum(t[0] for t in totals)
                        alight_sum = sum(t[1] for t in totals)
                        conn.execute(text("""
                            INSERT INTO transit_passengers (station_id, analysis_ym, boarding_count, alighting_count, total_volume)
                            VALUES (:station_id, '202605', :board, :alight, :total)
                        """), {
                            "station_id": station_db_map[std_id],
                            "board": board_sum,
                            "alight": alight_sum,
                            "total": board_sum + alight_sum
                        })
                        bus_pass_count += 1
                print(f"    Seeded {bus_pass_count} BUS passenger stats records.")
            except Exception as e:
                print(f"    [Skipped] BUS passengers seeding skipped: {e}")

            # B. Subway Passengers
            try:
                subway_pass_headers, subway_rows = load_csv_data(sources["subway_passengers"])
                subway_passenger_totals = defaultdict(list) # Normalized Station Name -> list of (board, alight)
                for row in subway_rows:
                    if not row or len(row) < 5:
                        continue
                    raw_name = row[2]
                    norm_name = normalize_subway_name(raw_name)
                    try:
                        board = int(row[3])
                        alight = int(row[4])
                    except ValueError:
                        continue
                        
                    subway_passenger_totals[norm_name].append((board, alight))
                    
                subway_pass_count = 0
                for norm_name, totals in subway_passenger_totals.items():
                    if norm_name in subway_db_map:
                        board_sum = sum(t[0] for t in totals)
                        alight_sum = sum(t[1] for t in totals)
                        conn.execute(text("""
                            INSERT INTO transit_passengers (station_id, analysis_ym, boarding_count, alighting_count, total_volume)
                            VALUES (:station_id, '202605', :board, :alight, :total)
                        """), {
                            "station_id": subway_db_map[norm_name],
                            "board": board_sum,
                            "alight": alight_sum,
                            "total": board_sum + alight_sum
                        })
                        subway_pass_count += 1
                print(f"    Seeded {subway_pass_count} SUBWAY passenger stats records.")
            except Exception as e:
                print(f"    [Skipped] SUBWAY passengers seeding skipped: {e}")

            # 7. Seed illegal_dumping_zones
            print("[8] Seeding illegal_dumping_zones...")
            try:
                dump_headers, dump_rows = load_csv_data(sources["illegal_dumping"])
                dump_count = 0
                for row in dump_rows:
                    if not row or len(row) < 4:
                        continue
                    addr_road = row[0]
                    addr_jibun = row[1]
                    try:
                        lng = float(row[2])
                        lat = float(row[3])
                    except ValueError:
                        continue
                        
                    if not (37.5 <= lat <= 37.58 and 126.9 <= lng <= 127.05):
                        continue
                        
                    dong_id, _, _ = get_dong_by_coord(lng, lat)
                    conn.execute(text("""
                        INSERT INTO illegal_dumping_zones (district_id, dong_id, address, detail_location, geom)
                        VALUES (:district_id, :dong_id, :address, :detail, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326))
                    """), {
                        "district_id": district_id,
                        "dong_id": dong_id,
                        "address": addr_jibun if addr_jibun else addr_road,
                        "detail": "상습 무단투기 의심 구역",
                        "lng": lng,
                        "lat": lat
                    })
                    dump_count += 1
                print(f"    Seeded {dump_count} illegal dumping zones.")
            except Exception as e:
                print(f"    [Skipped] illegal_dumping_zones seeding skipped: {e}")

            # 8. Seed population_stats and age_demographics
            print("[9] Seeding population_stats & age_demographics & civil_complaints...")
            try:
                pop_headers, pop_rows = load_csv_data(sources["local_population"])
                pop_by_adm = defaultdict(list)
                for row in pop_rows:
                    if not row or len(row) < 4:
                        continue
                    adm_code = row[2]
                    try:
                        pop = float(row[3])
                    except ValueError:
                        continue
                    pop_by_adm[adm_code].append(pop)
                    
                pop_count = 0
                age_count = 0
                comp_count = 0
                
                for adm_code, pops in pop_by_adm.items():
                    avg_pop = sum(pops) / len(pops)
                    
                    if adm_code in adm_to_leg:
                        for leg_code in adm_to_leg[adm_code]:
                            if leg_code in dong_db_map:
                                db_dong_id = dong_db_map[leg_code]
                                
                                # A. Insert population_stats
                                conn.execute(text("""
                                    INSERT INTO population_stats (dong_id, day_type, time_type, avg_population)
                                    VALUES (:dong_id, 'ALL', 'ALL', :avg_population)
                                """), {
                                    "dong_id": db_dong_id,
                                    "avg_population": avg_pop
                                })
                                pop_count += 1
                                
                                # B. Insert age_demographics (12.5% youth ratio)
                                youth_pop = int(avg_pop * 0.125)
                                conn.execute(text("""
                                    INSERT INTO age_demographics (dong_id, youth_population, total_population, youth_ratio)
                                    VALUES (:dong_id, :youth_pop, :total_pop, 0.125)
                                """), {
                                    "dong_id": db_dong_id,
                                    "youth_pop": youth_pop,
                                    "total_pop": int(avg_pop)
                                })
                                age_count += 1
                                
                                # C. Insert civil_complaints (proportional to population, random noise)
                                import random
                                random.seed(db_dong_id)
                                complaint_count = int(avg_pop * 0.005 + random.randint(10, 50))
                                conn.execute(text("""
                                    INSERT INTO civil_complaints (dong_id, complaint_count, analysis_year)
                                    VALUES (:dong_id, :complaint_count, '2026')
                                """), {
                                    "dong_id": db_dong_id,
                                    "complaint_count": complaint_count
                                })
                                comp_count += 1
                print(f"    Seeded {pop_count} population stats, {age_count} age demographics, and {comp_count} civil complaints.")
            except Exception as e:
                print(f"    [Skipped] local_population / demographics seeding skipped: {e}")

            # 9. Seed restricted_zones
            print("[10] Seeding restricted_zones...")
            try:
                rest_headers, rest_rows = load_csv_data(sources["restricted_zones"])
                rest_count = 0
                for row in rest_rows:
                    if not row or len(row) < 6:
                        continue
                    name = row[0]
                    category = row[1]
                    addr = row[2]
                    try:
                        lng = float(row[3])
                        lat = float(row[4])
                        radius_str = row[5]
                        radius = float(re.sub(r'[^0-9.]', '', radius_str))
                    except ValueError:
                        continue
                        
                    if not (33.0 <= lat <= 39.0 and 124.0 <= lng <= 132.0):
                        continue
                        
                    dong_id, _, _ = get_dong_by_coord(lng, lat)
                    
                    conn.execute(text("""
                        INSERT INTO restricted_zones (district_id, dong_id, zone_name, address, geom, zone_type, restriction_radius)
                        VALUES (:district_id, :dong_id, :zone_name, :address, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326), :zone_type, :area)
                    """), {
                        "district_id": district_id,
                        "dong_id": dong_id,
                        "zone_name": name,
                        "address": addr,
                        "lng": lng,
                        "lat": lat,
                        "zone_type": "childcare_center" if "어린이집" in category or "유치원" in category else ("school" if "학교" in category or "초등학교" in category else "nosmoking_zone"),
                        "area": radius
                    })
                    rest_count += 1
                print(f"    Seeded {rest_count} restricted zones.")
            except Exception as e:
                print(f"    [Skipped] restricted_zones seeding skipped: {e}")

            # [11] Seed default admin user if not exists
            print("[11] Seeding default admin account...")
            user_exists = conn.execute(text("SELECT COUNT(*) FROM users WHERE username = 'admin'")).scalar()
            if not user_exists:
                pwd_bytes = "admin1234".encode('utf-8')
                salt = bcrypt.gensalt()
                hashed = bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')
                
                conn.execute(text("""
                    INSERT INTO users (username, password_hash, role, department, district_id)
                    VALUES ('admin', :pwd_hash, 'admin', '스마트도시과', 1)
                """), {"pwd_hash": hashed})
                print("    Default admin account seeded successfully. (ID: admin / PW: admin1234)")
            else:
                print("    Admin account already exists. Skipping.")

            trans.commit()
            print("[+] Seeding completed successfully!")
            
        except Exception as e:
            trans.rollback()
            print(f"[-] Error during seeding: {str(e)}")
            raise e

if __name__ == "__main__":
    seed()
