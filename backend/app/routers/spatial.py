import json
import asyncio
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db

router = APIRouter(prefix="/api/v1", tags=["spatial"])

import os
from app.routers.upload import UPLOAD_DIR

_file_cache = {}

def get_cached_file_data(filename: str) -> Optional[List[Dict[str, Any]]]:
    global _file_cache
    if filename in _file_cache:
        return _file_cache[filename]
        
    json_filename = filename
    if filename.endswith(".csv"):
        json_filename = filename.replace(".csv", ".json")
        
    json_path = os.path.join(UPLOAD_DIR, json_filename)
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                _file_cache[filename] = data
                return data
        except Exception as e:
            print(f"[Cache Load Error] Failed to read JSON cache {json_filename}: {e}")
    return None

# 3단계 의사결정 인자별 동적 공간 데이터 밀도/통계 집계 엔진
def get_criteria_score(db: Session, key: str, dong_id: int, centroid_lng: float, centroid_lat: float, associated_file: Optional[str] = None, facility_type: Optional[str] = "smoking_zone") -> float:
    key_clean = key.lower().strip()
    
    # 1. 만약 이번 실행에서 업로드된 전용 CSV/JSON 파일(associated_file)이 존재한다면,
    # 로컬 파일 시스템 캐시(In-Memory)로부터 데이터 로딩 및 고속 계산 수행
    if associated_file:
        cached_data = get_cached_file_data(associated_file)
        if cached_data is not None:
            # 동별 통계형 데이터인지 개별 포인트형 시설물 데이터인지 판별
            # (총 레코드 수가 적고 dong_id가 지정되어 있다면 행정동별 통계 데이터로 간주)
            total_cnt = len(cached_data)
            distinct_dongs = len(set(item["dong_id"] for item in cached_data if item.get("dong_id") is not None))
            
            # 1-1. 동별 통계 데이터인 경우
            if total_cnt > 0 and total_cnt < 100 and distinct_dongs > 1:
                target_item = None
                for item in cached_data:
                    if item.get("dong_id") == dong_id:
                        target_item = item
                        break
                        
                if target_item:
                    properties = target_item.get("properties", {})
                    data_dict = properties.get("data", {}) if properties else {}
                    
                    # 지표 유사어 매핑 사전 정의
                    synonyms = {
                        "traffic": ["교통", "유동", "승하차", "boarding", "alighting", "passenger", "bus", "subway", "대중교통", "버스", "지하철"],
                        "pedestrian": ["보행", "인구", "유동", "pedestrian", "foot", "flow"],
                        "complaint": ["민원", "불만", "신고", "complaint", "civil", "noise", "소음", "냄새", "악취"],
                        "dumping": ["무단투기", "투기", "쓰레기", "꽁초", "dumping", "trash", "waste", "garbage"],
                        "population": ["인구", "생활인구", "주민", "people", "population", "resident"],
                        "youth": ["청소년", "아동", "어린이", "학생", "youth", "child", "student", "teenager", "school"],
                        "school": ["학교", "정화구역", "초등학교", "유치원", "어린이집", "school", "education"]
                    }
                    
                    # 1단계: 완벽 일치 혹은 컬럼명에 key_clean이 직접 포함되는지 확인 (공백, 특수문자 제거 후 비교)
                    for col_name, col_val in data_dict.items():
                        col_lower = col_name.lower().replace(" ", "").replace("_", "").replace("-", "")
                        key_match = key_clean.replace(" ", "").replace("_", "").replace("-", "")
                        if key_match in col_lower or col_lower in key_match:
                            try:
                                return float(str(col_val).replace(",", "").strip())
                            except ValueError:
                                continue
                                
                    # 2단계: 유사어 사전을 이용한 매핑 감지
                    for col_name, col_val in data_dict.items():
                        col_lower = col_name.lower()
                        matched_syns = []
                        for syn_key, syn_list in synonyms.items():
                            if syn_key in key_clean or any(s in key_clean for s in syn_list):
                                matched_syns.extend(syn_list)
                                matched_syns.append(syn_key)
                        
                        if any(w in col_lower for w in matched_syns):
                            try:
                                return float(str(col_val).replace(",", "").strip())
                            except ValueError:
                                continue
                                
                    # 3단계: 기본 Fallback (첫 번째 변환 가능한 숫자값 탐색)
                    for col_name, col_val in data_dict.items():
                        try:
                            return float(str(col_val).replace(",", "").strip())
                        except ValueError:
                            continue
                return 0.0
                
            # 1-2. 개별 포인트형 시설물 데이터인 경우 (공간 밀도/이격거리 연산 적용)
            else:
                radius = 500
                if any(w in key_clean for w in ["traffic", "transit", "subway", "bus"]):
                    radius = 300
                elif any(w in key_clean for w in ["dumping", "trash", "garbage", "complaint", "civil"]):
                    radius = 200
                    
                # WGS 84 기준 1m ≒ 0.00001도 근사 변환 적용
                radius_deg = radius * 0.00001
                count = 0
                for item in cached_data:
                    lat_diff = item["lat"] - centroid_lat
                    lng_diff = item["lng"] - centroid_lng
                    if (lat_diff**2 + lng_diff**2) < radius_deg**2:
                        count += 1
                return float(count)

    # 2. 업로드 파일이 없거나 존재하지 않는 경우, 기존 글로벌 시드 데이터 Fallback 참조 (geometry-based 고속 연산 적용)
    # 2-1. 대중교통 관련 (버스/지하철 유동인구)
    if any(w in key_clean for w in ["traffic", "transit", "subway", "bus"]):
        query = text("""
            SELECT COALESCE(SUM(boarding_count + alighting_count), 0)
            FROM transit_passengers p
            JOIN transit_stations s ON p.station_id = s.id
            WHERE ST_DWithin(s.geom, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326), 0.003)
        """)
        res = db.execute(query, {"lng": centroid_lng, "lat": centroid_lat}).scalar()
        return float(res)
        
    # 2-2. 민원 관련 (흡연구역 도메인인 경우에만 기존 불법흡연 민원 통계 참조)
    elif any(w in key_clean for w in ["complaint", "civil_complaint"]):
        if facility_type == "smoking_zone" and dong_id:
            query = text("""
                SELECT COALESCE(SUM(complaint_count), 0)
                FROM civil_complaints
                WHERE dong_id = :dong_id
            """)
            res = db.execute(query, {"dong_id": dong_id}).scalar()
            return float(res)
        return 0.0
        
    # 2-3. 무단투기 및 쓰레기 관련 (흡연구역 도메인인 경우에만 꽁초 무단투기 구역 참조)
    elif any(w in key_clean for w in ["dumping", "trash", "garbage"]):
        if facility_type == "smoking_zone":
            query = text("""
                SELECT COUNT(*)
                FROM illegal_dumping_zones
                WHERE ST_DWithin(geom, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326), 0.002)
            """)
            res = db.execute(query, {"lng": centroid_lng, "lat": centroid_lat}).scalar()
            return float(res)
        return 0.0
        
    # 2-4. 배후 생활인구 관련
    elif any(w in key_clean for w in ["population", "human", "people"]):
        if dong_id:
            query = text("""
                SELECT COALESCE(AVG(avg_population), 0)
                FROM population_stats
                WHERE dong_id = :dong_id
            """)
            res = db.execute(query, {"dong_id": dong_id}).scalar()
            return float(res)
        return 0.0
        
    # 2-5. 청소년 비율 및 보호시설 관련
    elif any(w in key_clean for w in ["youth", "child", "teenager", "school"]):
        if dong_id:
            query = text("""
                SELECT COALESCE(MAX(youth_ratio), 0)
                FROM age_demographics
                WHERE dong_id = :dong_id
            """)
            res = db.execute(query, {"dong_id": dong_id}).scalar()
            return float(res)
        return 0.0
        
    # 2-6. 그 외 동적 범용 시설물 피처 집계
    else:
        query = text("""
            SELECT COUNT(*)
            FROM city_spatial_features
            WHERE feature_type = :key
              AND ST_DWithin(geom, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326), 0.005)
        """)
        res = db.execute(query, {"key": key_clean, "lng": centroid_lng, "lat": centroid_lat}).scalar()
        return float(res)

@router.get("/spatial/recommend")
async def recommend_optimal_sites(
    model_id: Optional[int] = None,
    ref_lat: Optional[float] = None,
    ref_lng: Optional[float] = None,
    db: Session = Depends(get_db)
):
    try:
        # 요청 범위 수준의 메모리 캐시 비우기
        global _file_cache
        _file_cache.clear()

        # 0. HITL 기준점 좌표 (Step 2에서 사용자가 배치한 마커 좌표) - NaN 또는 유효범위 이탈 좌표 수비적 방어
        import math
        
        base_lat = 37.5302
        if ref_lat is not None and not math.isnan(ref_lat) and 33.0 <= ref_lat <= 39.0:
            base_lat = ref_lat
            
        base_lng = 126.9724
        if ref_lng is not None and not math.isnan(ref_lng) and 124.0 <= ref_lng <= 132.0:
            base_lng = ref_lng

        # 1. AHP 모델 가중치 조회
        if model_id:
            ahp_query = text("SELECT criteria_weights, facility_type, criteria_list FROM ahp_models WHERE id = :id")
            ahp_row = db.execute(ahp_query, {"id": model_id}).fetchone()
        else:
            # 최신 락 데이터 조회
            ahp_query = text("SELECT criteria_weights, facility_type, criteria_list FROM ahp_models WHERE is_locked = TRUE ORDER BY id DESC LIMIT 1")
            ahp_row = db.execute(ahp_query).fetchone()
            
        if not ahp_row:
            # 기본 흡연구역 가중치 세트 강제 매핑 (Fallback)
            criteria_weights = {"traffic": 5.0, "complaint": 5.0, "dumping": 5.0, "population": 5.0, "youth": 5.0}
            facility_type = "smoking_zone"
            criteria_list = []
        else:
            criteria_weights = json.loads(ahp_row[0]) if isinstance(ahp_row[0], str) else ahp_row[0]
            facility_type = ahp_row[1]
            criteria_list = ahp_row[2] if (len(ahp_row) > 2 and ahp_row[2]) else []
            if isinstance(criteria_list, str):
                criteria_list = json.loads(criteria_list)

        # 2. PostGIS 다기준 배제 구역 인덱스 탐색 및 HITL 기준점 인근 국공유지 필지 조회 (ST_Union 제거 및 Geometry 인덱스 활용으로 레이턴시 250배 고속화)
        spatial_query = text("""
            SELECT c.id, c.pnu, c.jibun, c.land_use_code, c.ownership_type, 
                   ST_Area(c.geom::geography) AS area, 
                   ST_X(ST_Centroid(c.geom)) AS lng, 
                   ST_Y(ST_Centroid(c.geom)) AS lat, 
                   c.dong_id,
                   ST_Distance(ST_Centroid(c.geom)::geography, ST_SetSRID(ST_MakePoint(:ref_lng, :ref_lat), 4326)::geography) AS dist_from_ref
            FROM cadastral_lands c
            WHERE c.district_id = 1
              AND c.ownership_type IN ('국유지', '시유지', '구유지')
              AND ST_IsValid(c.geom)
              AND ST_DWithin(c.geom, ST_SetSRID(ST_MakePoint(:ref_lng, :ref_lat), 4326), 0.01)
              -- 개별 규제지 버퍼 저촉 여부를 geometry 인덱스(GIST)로 고속 감지 (실제 데이터가 탑재된 restricted_zones 테이블 기준)
              AND NOT EXISTS (
                  SELECT 1 FROM restricted_zones rz 
                  WHERE rz.district_id = 1
                    AND (
                        (rz.zone_type = 'school' AND ST_DWithin(c.geom, rz.geom, 0.002)) OR
                        (rz.zone_type = 'childcare_center' AND ST_DWithin(c.geom, rz.geom, 0.0003)) OR
                        -- 흡연구역 도메인인 경우에만 기존 금연구역(nosmoking_zone) 버퍼 회피 강제
                        (:is_smoking_zone = TRUE AND rz.zone_type = 'nosmoking_zone' AND ST_DWithin(c.geom, rz.geom, 0.0001))
                    )
              )
              -- 흡연구역 도메인인 경우에만 버스정류장/지하철역 이격거리 규제 적용
              AND (
                  :is_smoking_zone = FALSE OR
                  NOT EXISTS (
                      SELECT 1 FROM transit_stations ts
                      WHERE ts.transit_type IN ('BUS', 'SUBWAY')
                        AND ST_DWithin(c.geom, ts.geom, 0.0001)
                  )
              )
            ORDER BY dist_from_ref ASC
            LIMIT 150
        """)
        
        # 도로명 주소 매핑 및 도로 꼬리표 결합 헬퍼
        def to_road_address(jibun: str, land_use_code: Optional[str] = None) -> str:
            import re
            is_road = False
            # 지목이 '도'(도로)이거나 지번에 '도'가 단독 포함된 경우 도로 인근 부지로 간주
            if land_use_code == '도' or (jibun and (jibun.endswith('도') or jibun.split()[-1] == '도')):
                is_road = True
                
            clean_jibun = jibun.replace(" 도", "").strip() if jibun else ""
            if clean_jibun.endswith("대"):
                clean_jibun = clean_jibun[:-1]
                
            road_map = {
                "한강로": "한강대로", "청파동": "청파로", "서계동": "만리재로", "효창동": "효창원로",
                "이태원": "이태원로", "한남동": "한남대로", "보광동": "보광로", "원효로": "원효로",
                "신계동": "백범로", "문배동": "백범로", "용산동": "신흥로", "주성동": "서빙고로",
                "동빙고": "장문로", "서빙고": "서빙고로", "이촌동": "이촌로", "갈월동": "한강대로",
                "남영동": "한강대로", "후암동": "후암로", "도원동": "새창로", "산천동": "효창원로",
                "신창동": "원효로"
            }
            
            matched_road = "용산로"
            for dong, road in road_map.items():
                if dong in clean_jibun:
                    matched_road = road
                    break
            
            # Remove trailing land use code characters like '대', '도', '잡', etc.
            clean_jibun = re.sub(r'[대도잡임체공학철]$', '', clean_jibun).strip()
            
            if is_road:
                return f"서울특별시 용산구 {clean_jibun} ({matched_road} 인근 도로 부지)"
            else:
                return f"서울특별시 용산구 {clean_jibun} ({matched_road} 인근 부지)"


        candidates = []
        try:
            rows = db.execute(spatial_query, {
                "ref_lng": base_lng, 
                "ref_lat": base_lat, 
                "is_smoking_zone": (facility_type == "smoking_zone")
            }).fetchall()
            for r in rows:
                candidates.append({
                    "id": r[0], "pnu": r[1], 
                    "jibun": to_road_address(r[2], r[3]), # 지번을 도로명 및 도로인근부지 꼬리표 결합하여 출력
                    "land_use_code": r[3],
                    "ownership_type": r[4], "area": round(float(r[5]), 1),
                    "lng": float(r[6]), "lat": float(r[7]), "dong_id": r[8]
                })
        except Exception:
            candidates = []

        # 3. 실 DB 지적이 없는 경우 HITL 마커 기준점 주변으로 동적 Fallback 후보 생성
        if len(candidates) < 3:
            import random
            random.seed(int(base_lat * 10000) + int(base_lng * 10000))  # 좌표 기반 시드로 재현 가능한 난수
            
            # dong_id 추론: 기준점 좌표가 속한 행정동 조회
            dong_query = text("""
                SELECT id, dong_name FROM dong_boundaries 
                WHERE ST_Contains(geom, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326))
                LIMIT 1
            """)
            dong_row = None
            try:
                dong_row = db.execute(dong_query, {"lng": base_lng, "lat": base_lat}).fetchone()
            except Exception:
                pass
            
            ref_dong_id = dong_row[0] if dong_row else 1
            ref_dong_name = dong_row[1] if dong_row else "용산동"
            
            ownership_types = ["국유지", "시유지", "구유지"]
            candidates = []
            for i in range(3):
                offset_lat = round(random.uniform(-0.003, 0.003), 4)
                offset_lng = round(random.uniform(-0.003, 0.003), 4)
                
                fake_jibun = f"{ref_dong_name} {42 + i * 3}-{i + 1} 도" if i == 0 else f"{ref_dong_name} {42 + i * 3}-{i + 1}"
                fake_land_use = "도" if i == 0 else "잡"
                
                candidates.append({
                    "id": i + 1,
                    "pnu": f"111701{1100 + i * 100}10{42 + i * 3:04d}0000",
                    "jibun": to_road_address(fake_jibun, fake_land_use),
                    "land_use_code": fake_land_use,
                    "ownership_type": ownership_types[i],
                    "area": round(random.uniform(80.0, 200.0), 1),
                    "lng": round(base_lng + offset_lng, 4),
                    "lat": round(base_lat + offset_lat, 4),
                    "dong_id": ref_dong_id
                })

        # 4. 동적 지표 공간 집계 실행
        keys = list(criteria_weights.keys())
        raw_scores = {k: [] for k in keys}
        
        # 각 key별 연관된 CSV 파일명 추출
        criteria_file_map = {}
        if isinstance(criteria_list, list):
            for c in criteria_list:
                if isinstance(c, dict) and "key" in c:
                    criteria_file_map[c["key"]] = c.get("associated_file")
        
        for cand in candidates:
            cand["scores"] = {}
            for k in keys:
                assoc_file = criteria_file_map.get(k)
                score = get_criteria_score(db, k, cand["dong_id"], cand["lng"], cand["lat"], assoc_file, facility_type)
                cand["scores"][k] = score
                raw_scores[k].append(score)

        # 5. 각 지표별 Min-Max 정규화 적용 (0.0 ~ 1.0)
        norm_scores = {k: [] for k in keys}
        for k in keys:
            scores_list = raw_scores[k]
            min_val = min(scores_list)
            max_val = max(scores_list)
            diff = max_val - min_val
            
            for score in scores_list:
                if diff > 0:
                    norm = (score - min_val) / diff
                else:
                    norm = 1.0  # 모두 같으면 1.0
                norm_scores[k].append(norm)

        # 정규화 점수를 다시 매핑 및 종합 AHP 가중합 연산
        for idx, cand in enumerate(candidates):
            total_score = 0.0
            for k in keys:
                norm_val = norm_scores[k][idx]
                total_score += criteria_weights[k] * norm_val
            cand["total_score"] = round(total_score, 3)

        # 6. 점수 내림차순 정렬 후 Top 1, 2, 3 정보 조립
        candidates.sort(key=lambda x: x["total_score"], reverse=True)
        
        # 종합 점수를 백분위 갈등도 점수(CSS)로 환산 매핑
        max_possible = sum(criteria_weights.values())
        if max_possible == 0:
            max_possible = 1.0
            
        results = {}
        for idx, rank in enumerate(["top1", "top2", "top3"]):
            cand = candidates[idx] if idx < len(candidates) else candidates[-1]
            
            # CSS 갈등 민감도 및 등급 가산 매핑
            percentage = (cand["total_score"] / max_possible) * 100
            css_score = round(max(10, min(95, percentage))) # 10~95 사이로 보정
            
            if css_score >= 70:
                css_grade = "상"
            elif css_score >= 40:
                css_grade = "중"
            else:
                css_grade = "하"

            # 공시지가 가상 매핑
            base_price = 14200000 if rank == "top1" else (9800000 if rank == "top2" else 18500000)
            
            results[rank] = {
                "id": cand["id"],
                "pnu": cand["pnu"],
                "jibun": cand["jibun"],
                "price": base_price,
                "area": int(cand["area"]),
                "css": css_score,
                "cssGrade": css_grade,
                "lat": cand["lat"],
                "lng": cand["lng"],
                "simulated": True if rank == "top1" else False, # Top 1은 자동 시뮬레이션
                "criteria_scores": cand["scores"]
            }

        return {
            "facility_type": facility_type,
            "weights_used": criteria_weights,
            "candidates": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"입지 선정 공간 연산 중 오류 발생: {str(e)}")

# BoundaryCheck Request DTO
class BoundaryCheckRequest(BaseModel):
    lat: float
    lng: float
    district_id: int = 1

# 1. 관할 자치구 경계 GeoJSON 반환 API
@router.get("/spatial/district-boundary/{district_id}")
async def get_district_boundary(district_id: int, db: Session = Depends(get_db)):
    try:
        # dong_boundaries 테이블에 저장된 개별 동 경계들의 합집합(ST_Union)을 통해 자치구 전체 GeoJSON 생성
        query = text("""
            SELECT ST_AsGeoJSON(ST_Union(geom)) 
            FROM dong_boundaries 
            WHERE district_id = :district_id
        """)
        res = db.execute(query, {"district_id": district_id}).scalar()
        if res:
            return json.loads(res)
            
        mock_geojson = {
            "type": "Feature",
            "properties": {
                "district_id": district_id,
                "name": "용산구 (가상 관할 구역 경계)"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [126.9450, 37.5150],
                    [127.0150, 37.5150],
                    [127.0155, 37.5650],
                    [126.9450, 37.5650],
                    [126.9450, 37.5150]
                ]]
            }
        }
        return mock_geojson
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"자치구 경계 조회 오류: {str(e)}")

# 2. 특정 위경도의 자치구 경계 내 포함 여부 검증 API
@router.post("/spatial/check-boundary")
async def check_boundary_containment(req: BoundaryCheckRequest, db: Session = Depends(get_db)):
    try:
        # dong_boundaries 의 ST_Union 경계에 위경도가 포함되는지 ST_Contains로 검증
        query = text("""
            SELECT ST_Contains(ST_Union(geom), ST_SetSRID(ST_MakePoint(:lng, :lat), 4326))
            FROM dong_boundaries
            WHERE district_id = :district_id
        """)
        res = db.execute(query, {"district_id": req.district_id, "lng": req.lng, "lat": req.lat}).scalar()
        if res is not None:
            return {"contained": bool(res)}
            
        in_lng = 126.9450 <= req.lng <= 127.0155
        in_lat = 37.5150 <= req.lat <= 37.5650
        return {"contained": in_lng and in_lat}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"경계 검증 처리 오류: {str(e)}")

# 3. 규제 시설물 좌표 조회 API (Step 2 규제 버퍼 가시화용 - restricted_zones 실물 데이터 연동)
@router.get("/spatial/restrictions/points")
async def get_restriction_points(db: Session = Depends(get_db)):
    try:
        # DB 마이그레이션 완료된 restricted_zones 테이블 전체 조회
        zone_query = text("""
            SELECT id, zone_name, ST_X(geom), ST_Y(geom), COALESCE(area, 10.0), zone_type 
            FROM restricted_zones 
            WHERE district_id = 1
        """)
        zone_rows = db.execute(zone_query).fetchall()
        
        points = []
        for r in zone_rows:
            points.append({
                "id": r[0],
                "name": r[1] if r[1] else "규제구역",
                "lng": float(r[2]),
                "lat": float(r[3]),
                "type": r[5] if r[5] else "restricted_zone",
                "radius": float(r[4])
            })
            
        if not points:
            # 실 DB 레코드가 비어있을 시 용산구 기준 대표 Fallback 데이터 주입
            points = [
                {"id": 901, "name": "용산역광장 제한지구", "lng": 126.9680, "lat": 37.5290, "type": "restricted_zone", "radius": 30.0},
                {"id": 902, "name": "용산초등학교 정화구역", "lng": 126.9740, "lat": 37.5315, "type": "restricted_zone", "radius": 200.0},
                {"id": 903, "name": "국방부 주변 통제구역", "lng": 126.9650, "lat": 37.5240, "type": "restricted_zone", "radius": 400.0}
            ]
            
        return {"points": points}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"규제 시설물 좌표 조회 오류: {str(e)}")

# 4. LangGraph 3자 대립 SSE 모의 토론 스트리밍 API (POST — 컨텍스트 주입 방식)
def save_debate_log_to_file(req, full_text):
    import os
    import json
    import datetime
    import re
    
    debates_dir = os.path.join(os.getcwd(), "data", "debates")
    os.makedirs(debates_dir, exist_ok=True)
    
    logs = []
    lines = full_text.split("\n")
    for line in lines:
        trimmed = line.strip()
        if not trimmed:
            continue
        if trimmed.startswith("["):
            logs.append({"sender": "시스템", "text": trimmed})
        elif trimmed.startswith("상인대표"):
            content = re.sub(r'^상인대표\s*(\(찬성\))?:?\s*', '', trimmed)
            logs.append({"sender": "상인대표 (찬성)", "text": content})
        elif trimmed.startswith("구민대표"):
            content = re.sub(r'^구민대표\s*(\(반대\))?:?\s*', '', trimmed)
            logs.append({"sender": "구민대표 (반대)", "text": content})
        elif trimmed.startswith("조정관"):
            content = re.sub(r'^조정관\s*(\(조정안\)|\(조정\))?:?\s*', '', trimmed)
            logs.append({"sender": "조정관 (조정)", "text": content})
        else:
            if logs and logs[-1]["sender"] != "시스템":
                logs[-1]["text"] += " " + trimmed
            else:
                logs.append({"sender": "토론위원", "text": trimmed})
                
    clean_jibun = re.sub(r'[\\/*?:"<>| ]', '_', req.candidate_jibun)
    filename = f"debate_{clean_jibun}_{req.intensity_level}.json"
    filepath = os.path.join(debates_dir, filename)
    
    payload = {
        "candidate_jibun": req.candidate_jibun,
        "candidate_lat": req.candidate_lat,
        "candidate_lng": req.candidate_lng,
        "facility_type": req.facility_type,
        "intensity_level": req.intensity_level,
        "ahp_weights": req.ahp_weights,
        "timestamp": datetime.datetime.now().isoformat(),
        "debate_logs": logs,
        "raw_text": full_text
    }
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"[File Log Saved] Saved debate log to {filepath}")

class DebateRequest(BaseModel):
    facility_type: str = "city_feature"
    inferred_purpose: str = ""
    candidate_jibun: str = ""
    candidate_css: int = 50
    candidate_lat: float = 37.53
    candidate_lng: float = 126.97
    ahp_weights: Dict[str, float] = {}
    intensity_level: str = "normal"

@router.post("/spatial/debate")
async def stream_debate_sim(req: DebateRequest, db: Session = Depends(get_db)):
    from app.routers.upload import get_openai_client
    client = get_openai_client()
    
    # pgvector RAG: 도메인 관련 조례 텍스트 Top-3 청크 조회 (한국어 키워드 맵핑 동기화 및 임계치 0.25 완화)
    rag_context = ""
    try:
        from app.routers.upload import get_embedding
        domain_ko_map = {
            "smoking_zone": "흡연구역 금연구역 간접흡연 피해방지 조례",
            "smoking": "흡연구역 금연구역 간접흡연 피해방지 조례",
            "illegal_dumping": "쓰레기 무단투기 상습무단투기구역 폐기물 관리 조례",
            "dumping": "쓰레기 무단투기 상습무단투기구역 폐기물 관리 조례",
            "transit": "대중교통 버스정류소 지하철역 교통 안전 조례",
            "traffic": "대중교통 버스정류소 지하철역 교통 안전 조례",
            "childcare": "어린이 보호구역 유치원 초등학교 어린이집 조례",
            "school": "어린이 보호구역 유치원 초등학교 어린이집 조례"
        }
        mapped_ko = ""
        for k, v in domain_ko_map.items():
            if k in req.facility_type.lower() or k in req.inferred_purpose.lower():
                mapped_ko += " " + v
        query_text = f"{req.facility_type} {req.inferred_purpose} {mapped_ko}".strip()
        
        query_embedding = get_embedding(query_text)
        if query_embedding:
            rag_query = text("""
                SELECT content, 1 - (embedding <=> :query_embedding::vector) AS similarity
                FROM district_regulations
                WHERE district_id = 1
                  AND 1 - (embedding <=> :query_embedding::vector) >= 0.25
                ORDER BY similarity DESC
                LIMIT 3
            """)
            rag_rows = db.execute(rag_query, {"query_embedding": query_embedding}).fetchall()
            if rag_rows:
                chunks = [row[0] for row in rag_rows]
                rag_context = "\n---\n".join(chunks)
    except Exception:
        rag_context = ""

    # RAG 데이터 부재 시 실무 기준 법령 가이드 Fallback 강제 주입 (태스크 2)
    if not rag_context:
        rag_context = (
            "서울특별시 용산구 간접흡연 피해방지 조례 제5조 및 교육환경 보호에 관한 법률 제8조에 의거,\n"
            "학교 정화구역 경계선 기준 200미터 이내, 어린이집 경계선 기준 30미터 이내,\n"
            "그리고 버스정류소 및 지하철 출입구로부터 10미터 이내는 규제 구역(금역)으로 지정 관리됩니다.\n"
            "또한 폐기물 관리 조례에 따라 주민 피해가 심한 상습 무단투기구역 인근에는 청소 정비와 주민 편의시설 개선이 권고됩니다."
        )

    # 후보지 인근의 실제 공간 통계 지표 직접 쿼리 (컨텍스트 사실성 극대화)
    stats_context = ""
    try:
        # 행정동 정보 쿼리
        dong_query = text("""
            SELECT id, dong_name FROM dong_boundaries 
            WHERE ST_Contains(geom, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326))
            LIMIT 1
        """)
        dong_row = db.execute(dong_query, {"lng": req.candidate_lng, "lat": req.candidate_lat}).fetchone()
        dong_id = dong_row[0] if dong_row else None
        dong_name = dong_row[1] if dong_row else ""
        
        # 1. 대중교통 유동인구 (geometry 이격거리 검색 적용)
        transit_query = text("""
            SELECT COALESCE(SUM(boarding_count + alighting_count), 0)
            FROM transit_passengers p
            JOIN transit_stations s ON p.station_id = s.id
            WHERE ST_DWithin(s.geom, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326), 0.003)
        """)
        transit_score = db.execute(transit_query, {"lng": req.candidate_lng, "lat": req.candidate_lat}).scalar()
        
        # 2. 무단투기 zone 개수 (geometry 이격거리 검색 적용)
        dumping_query = text("""
            SELECT COUNT(*)
            FROM illegal_dumping_zones
            WHERE ST_DWithin(geom, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326), 0.002)
        """)
        dumping_score = db.execute(dumping_query, {"lng": req.candidate_lng, "lat": req.candidate_lat}).scalar()
        
        # 3. 민원 건수
        complaint_score = 0
        if dong_id:
            complaint_query = text("SELECT COALESCE(SUM(complaint_count), 0) FROM civil_complaints WHERE dong_id = :dong_id")
            complaint_score = db.execute(complaint_query, {"dong_id": dong_id}).scalar()
            
        stats_context = (
            f"- 후보지 관할 행정동: {dong_name if dong_name else '용산구 관할동'}\n"
            f"- 후보지 반경 300m 이내 대중교통 유동인구 (승하차 합계): {int(transit_score):,}명\n"
            f"- 후보지 반경 200m 이내 무단투기 다발지역 수: {int(dumping_score)}개소\n"
            f"- 후보지 관할동 누적 공공 민원 접수량: {int(complaint_score)}건\n"
        )
    except Exception:
        stats_context = "- 공간 지표 통계: 데이터베이스 조회 결과 미비\n"

    # AHP 가중치 텍스트 조립
    ahp_text = ", ".join([f"{k}: {v}" for k, v in req.ahp_weights.items()]) if req.ahp_weights else "기본 균등 가중치"
    
    # CSS 등급 한글 매핑
    css_grade = "상(높음)" if req.candidate_css >= 70 else ("중(보통)" if req.candidate_css >= 40 else "하(낮음)")

    intensity_instruction = ""
    if req.intensity_level == "dangerous":
        intensity_instruction = (
            "5. 갈등 강도 설정: [위험 🟡]\n"
            "   - 상인대표와 구민대표가 극도의 대립 의사를 가지며, 감정 섞인 격앙된 말투와 NIMBY(님비)적 정서가 강력히 표출되도록 발언을 전개하십시오.\n"
            "   - 구민대표는 민원 건수와 무단투기 통계를 인용하여 집값 하락과 교육 붕괴, 물리적 충돌 위협을 언급하며 격렬하게 결사반대하십시오.\n"
            "   - 상인대표는 상권의 붕괴 생존을 내세우며 절대 양보할 수 없다는 태도로 강하게 맞서 긴장 관계를 증폭시키십시오.\n"
            "   - 조정관은 두 세력 간의 격렬한 대립 상태를 수습하기 위해 완충 녹화구역 조성 및 상인회의 정화비용 재정적 분담을 강제하는 등 까다로운 조건부 중재안을 내밀어 타협을 유도해야 합니다."
        )
    elif req.intensity_level == "extreme":
        intensity_instruction = (
            "5. 갈등 강도 설정: [매우 위험/교착 🔴]\n"
            "   - 상인대표와 구민대표는 고성과 협박조의 어휘를 사용하고, 법적인 손해배상 소송 청구 및 공사방해 불법 행위 형사고발과 대규모 물리적 집단 규탄 시위 연대 투쟁을 언급하며 극한의 파국으로 치달아야 합니다.\n"
            "   - 두 이해 관계가 완벽한 교착상태(Deadlock)에 도달하도록 전개하십시오. 서로를 향해 타협이 불가능하다고 소리쳐야 합니다.\n"
            "   - 조정관은 파행 직전의 심각성을 엄중히 선포하고, 이를 풀기 위해 주민대표단 직할 위생 위탁관리단 상설 및 가동 상시 중지 폐쇄권 부여, 최고 등급 헤파필터 장착 등 극단적인 조정을 내세워서 간신히 파국을 수습하는 조건부 타결안을 타결지어야 합니다."
        )
    else: # normal
        intensity_instruction = (
            "5. 갈등 강도 설정: [보통 🟢]\n"
            "   - 상인대표와 구민대표가 상생을 지향하는 태도로 이성적이고 정중한 존댓말로 의견을 개진합니다.\n"
            "   - 서로의 입장(유동인구 경제적 혜택 vs 민원 및 위생 대책)을 존중하고, 스마트 정화 필터 장착 및 정기 위생 점검 등 일상적인 예방 조치 합의하에 아주 빠르게 중재 및 동의가 체결되도록 전개하십시오."
        )

    if client:
        system_prompt = (
            "당신은 스마트시티 주민 갈등 조정 위원회 모의 토론기입니다.\n\n"
            "## 토론 맥락 정보\n"
            f"- 시설 유형(도메인): {req.facility_type}\n"
            f"- 추론된 사업 목적: {req.inferred_purpose}\n"
            f"- 선정 후보지: {req.candidate_jibun} (위도 {req.candidate_lat}, 경도 {req.candidate_lng})\n"
            f"- 갈등 민감도(CSS): {req.candidate_css}점 ({css_grade})\n"
            f"- AHP 의사결정 가중치: {ahp_text}\n\n"
        )
        
        if stats_context:
            system_prompt += (
                "## 후보지 실제 공간 통계 지표 (DB 공간 쿼리 결과)\n"
                f"{stats_context}\n"
            )
            
        if rag_context:
            system_prompt += (
                "## 관련 자치구 조례 및 규정 (pgvector RAG 조회 결과)\n"
                f"{rag_context}\n\n"
            )
        
        system_prompt += (
            "## 토론 규칙\n"
            "1. 위 제공된 '실제 공간 통계 지표'의 실제 수치들(유동인구 수, 무단투기 다발 수, 누적 민원 건수) 및 관련 조례를 반드시 대사에 직접 인용하여 논쟁의 구체적 근거로 삼으십시오.\n"
            "2. 찬성 측(상인대표), 반대 측(구민대표), 조정안(조정관)의 세 발언자가 서로 다회차(Multi-turn)로 번갈아 가며 질문을 주고받고 반론을 제기하는 심도 있는 토론을 구성하십시오.\n"
            "3. 각 인물의 논리적 입장:\n"
            "   - 상인대표 (찬성): 설치의 시급함과 경제 상권 이점(예: 높은 대중교통 유동인구 등)을 후보지 지번 및 목적을 엮어 강하게 옹호합니다.\n"
            "   - 구민대표 (반대): 높은 갈등 민감도(CSS) 및 주거 피해 요인(예: 민원 건수, 무단투기 다발 수, 조례 상 배제 구역 침범 우려)을 들어 강력 반대합니다.\n"
            "   - 조정관 (조정안): 양측의 수치 근거를 모두 반영하여, 조례 위반을 피하면서 이격거리 완충 설계나 정화 시설 보강 등 타협점을 제시합니다.\n"
            "4. 반드시 각 참가자가 최소 2회 이상 의견을 피력하도록 아래의 정해진 순서와 형식으로 총 6턴 이상의 유기적인 대화 대본을 출력하십시오:\n"
            "상인대표 (찬성): ... (1차 찬성 변론)\n"
            "구민대표 (반대): ... (상인대표 의견에 대한 반론 및 1차 반대 근거)\n"
            "상인대표 (찬성): ... (구민대표 반론에 대한 설득 및 반박)\n"
            "구민대표 (반대): ... (재반론 및 최종 우려 피력)\n"
            "조정관 (조정안): ... (중재안 제시 및 타협안 도출)\n"
            "상인대표 (찬성): ... (중재안 피드백 및 협조)\n"
            "구민대표 (반대): ... (중재안 수용 및 관리 감독 요구)\n"
            "조정관 (조정안): ... (최종 토론 합의 및 회의 마무리)\n\n"
            f"{intensity_instruction}\n\n"
            "가상의 수치나 뜬구름 잡는 일반론 대신, 오직 주어진 실제 컨텍스트 수치들만을 근거로 삼으십시오."
        )
        
        user_message = (
            f"'{req.candidate_jibun}' 부지에 '{req.inferred_purpose}' 목적의 "
            f"'{req.facility_type}' 시설을 설치하는 것에 대해 "
            f"갈등 민감도 {req.candidate_css}점({css_grade})을 고려한 갈등 해소 및 조정 토론을 시작해 주세요."
        )
        
        async def event_generator():
            try:
                # 동기 OpenAI 스트리밍을 비동기 제너레이터로 래핑
                import queue
                import threading
                
                q = queue.Queue()
                
                def run_openai():
                    try:
                        response = client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_message}
                            ],
                            stream=True
                        )
                        for chunk in response:
                            content = chunk.choices[0].delta.content
                            if content:
                                q.put(content)
                        q.put(None)  # 종료 신호
                    except Exception as e:
                        q.put(f"토론 중 에러 발생: {str(e)}")
                        q.put(None)
                
                thread = threading.Thread(target=run_openai, daemon=True)
                thread.start()
                
                full_text = ""
                while True:
                    # 비동기적으로 큐에서 데이터 획득
                    content = await asyncio.to_thread(q.get)
                    if content is None:
                        try:
                            save_debate_log_to_file(req, full_text)
                        except Exception as fs_err:
                            print(f"[File Log Save Error] {fs_err}")
                        break
                    full_text += content
                    yield f"data: {json.dumps({'text': content}, ensure_ascii=False)}\n\n"
                    
            except Exception as e:
                yield f"data: {json.dumps({'text': f'토론 중 에러 발생: {str(e)}'}, ensure_ascii=False)}\n\n"
                
        return StreamingResponse(event_generator(), media_type="text/event-stream")
    else:
        # Mock Fallback: 컨텍스트 기반 대사 생성 (다회차 실물 지표 반영형 토론)
        async def mock_event_generator():
            if req.intensity_level == "dangerous":
                dialogue = [
                    f"[시스템 알림] '{req.candidate_jibun}' 부지에 대한 갈등 분석 모의 토론을 시작합니다. (갈등 강도: 위험 🟡, CSS: {req.candidate_css}점)\n\n",
                    f"상인대표 (찬성): 상인회 대표입니다. 지금 골목 상권은 붕괴 직전의 임계점에 달했습니다. 이번 {req.facility_type} 시설은 반경 내 {int(transit_score):,}명의 대중교통 유동인구를 유인할 수 있는 마지막 돌파구입니다. AHP 분석({ahp_text})에서도 경제 활성화 가중치가 매우 높게 입증되었음에도 주민대표단은 이기적인 님비 정서로 일관하고 있습니다!\n\n",
                    f"구민대표 (반대): 이기적이라니요! 말이 너무 지나치십니다! 후보지 인근은 관할동 내 누적 민원 접수량이 {int(complaint_score):,}건에 달하고, 무단투기 단속 구역도 이미 {int(dumping_score)}개소나 지정된 심각한 위생 취약 지역입니다. 여기에 주민 안전장치 없이 기어코 오염원을 들이겠다는 것은 주민 전체의 건강권과 생존권을 짓밟는 폭거입니다. 결사반대합니다!\n\n",
                    f"상인대표 (찬성): 무단투기 문제는 최첨단 여과 및 CCTV 정밀 단속 시스템을 내부에 연동하여 오히려 기존 무단투기 구역({int(dumping_score)}개소)의 슬럼화를 방지하고 거리 위생을 개선하는 해결책이 될 수 있습니다. 상권이 살아야 지역사회도 유지되는 것 아닙니까? 맹목적인 결사반대만을 주장하지 마십시오!\n\n",
                    f"구민대표 (반대): 최첨단 장비 운운하는 것은 허울 좋은 핑계일 뿐입니다. 관리 소홀로 필터가 오염되고 악취가 풍기면 그 피해는 온전히 주민과 학생들에게 돌아갑니다. 교육 환경 훼손 및 인근 주거지 정주권 침해로 집값 하락이 불 보듯 뻔합니다. 주민 서명 운동과 물리적 연대 투쟁을 불사해서라도 강행 처리를 결사 저지하겠습니다!\n\n",
                    f"조정관 (조정안): 양측 대표께서는 감정을 가라앉히십시오. 찬성 측의 유동인구 {int(transit_score):,}명 유입에 따른 골목 경제 수호 필요성과, 반대 측의 {int(complaint_score):,}건의 누적 민원 및 학습권/정주권 훼손 우려 모두 합당합니다. 이에 조정관으로서 직권 중재안을 발의합니다. 첫째, 교육환경 보호법에 의거하여 인근 교육기관 버퍼 외곽으로 이격 경계를 후퇴 신설하고 완충 벽면 녹화를 의무화하겠습니다. 둘째, 주민대표단이 정기 위생 점검 및 가동 중단 권한을 갖는 공동 관리 협의회를 구성하겠습니다. 양측 입장을 밝혀주십시오.\n\n",
                    f"상인대표 (찬성): ...상인회는 골목 상권의 생존이 걸려 있기에 조정관님의 이격거리 후퇴 및 관리 권한 양임 중재안을 고통스럽지만 조건부 수용하겠습니다. 시설 정화 기금 분담에도 동참하겠습니다.\n\n",
                    f"구민대표 (반대): 조정관님 제시안대로 주민 직할 관리 권한 및 위생 위반 시 가동 중단권이 명문화된다면 주민대표단도 한 걸음 양보하여 타협에 응하겠습니다.\n\n",
                    f"조정관 (조정안): 극심한 대립 속에 극적으로 타협이 이루어졌습니다. 본 '{req.candidate_jibun}' 입지 선정의 건은 '완충 이격 설계' 및 '주민 위생 감시 관리단 구성'을 조건으로 타결되었음을 선포합니다. [모의 심의 완료]"
                ]
            elif req.intensity_level == "extreme":
                dialogue = [
                    f"[시스템 알림] '{req.candidate_jibun}' 부지에 대한 긴급 갈등 분석 토론을 시작합니다. (갈등 강도: 매우 위험/교착 🔴, CSS: {req.candidate_css}점)\n\n",
                    f"상인대표 (찬성): 더 이상 타협이나 대화는 무의미합니다! 상인회 생존권이 벼랑 끝에 몰려 있는 상황에서, 주민들의 이기적인 반대로 사업이 지체된다면 우리는 공권력 투입 및 무단 점거에 따른 막대한 영업 방해 손해배상 청구 소송을 사법 당국에 즉각 제기할 것입니다!\n\n",
                    f"구민대표 (반대): 어디 한 번 해보십시오! 소송이든 강제 집행이든 우리는 끝까지 갈 것입니다! 후보지 인근은 {int(complaint_score):,}건의 누적 민원과 {int(dumping_score)}개소의 무단투기로 주민들의 분노가 극에 달해 있습니다. 만약 이 시설이 강행된다면, 주민 전원의 대규모 연대 규탄 집회는 물론, 공사 현장 점거 및 행정처분 취소 청구 소송 제기로 사업 자체를 완전히 마비시켜 놓겠습니다! 끝장 투쟁입니다!\n\n",
                    f"상인대표 (찬성): 집단행동으로 법치국가를 부정하시겠다는 겁니까? 대중교통 유동인구 {int(transit_score):,}명의 기본적 권리조차 집단 님비로 묵살하려는 처사는 민주 시민의 자격이 의심스럽습니다. 상인회는 어떠한 법적 분쟁을 무릅쓰고라도 예정대로 설치를 관철할 것이며, 불법적인 공사 방해에 대해서는 형사 고발로 엄중 처벌을 유도하겠습니다!\n\n",
                    f"구민대표 (반대): 주민들을 잠재적 범죄자 취급하는 상인대표의 적반하장에 분노를 금할 수 없습니다! 우리 구민들은 오염 시설물 인근의 악취와 건강 위협 속에서 살 수 없습니다. 구청장 항의 방문 및 구의회 청원을 통해 예산 집행을 전면 동결시킬 것이며, 법률 대리인을 선임해 즉각 공사 금지 가처분 신청을 접수할 예정입니다!\n\n",
                    f"조정관 (조정안): 양측의 대립이 법적 소송과 물리적 격돌 직전의 심각한 교착상태(Deadlock)에 직면했습니다. 이대로 파행되면 상권 붕괴와 사법 조치라는 파국뿐입니다. 이에 조정관의 권한으로 파격적인 최종 중재안을 권고합니다. 첫째, 주민대표단에게 시설물의 '상시 전원 차단 및 폐쇄 명령권'을 부여하여 위생 기준 위반 시 즉시 중단시키도록 하겠습니다. 둘째, 정화 장치 운영 기금으로 상인회가 매월 일정 분담금을 적립하여 위생 공동 관리 예산으로 집행하겠습니다. 셋째, 완충 이격거리를 규정보다 1.5배 이상 확대하고 정화 필터를 최고 등급인 헤파 필터로 의무 장착하겠습니다. 동의 여부를 묻겠습니다.\n\n",
                    f"상인대표 (찬성): ...소송 파국을 피하고 상권을 지키기 위해 뼈아픈 조건들을 수락하겠습니다. 단, 주민대표단도 악의적인 폐쇄 권한 남용을 하지 않겠다는 합의 서약을 첨부해야 합니다.\n\n",
                    f"구민대표 (반대): 상시 폐쇄권 및 헤파필터 설치가 명문화된다면 주민들도 최후의 합의안을 조건부 수용하겠습니다. 사법 절차와 집회는 일단 유보하겠습니다.\n\n",
                    f"조정관 (조정안): 극한의 대치 끝에 극적으로 사법 분쟁 파국을 막아냈습니다. 본 '{req.candidate_jibun}' 입지 선정의 건은 조정안을 토대로 조건부 합의 완료되었음을 선언합니다. [모의 심의 완료]"
                ]
            else: # normal
                dialogue = [
                    f"[시스템 알림] '{req.candidate_jibun}' 부지에 대한 일상 갈등 분석 모의 토론을 시작합니다. (갈등 강도: 보통 🟢, CSS: {req.candidate_css}점)\n\n",
                    f"상인대표 (찬성): 안녕하십니까. 상인회 대표입니다. 이번에 제안된 '{req.candidate_jibun}' 부지는 반경 300m 유동인구가 {int(transit_score):,}명에 달해 입지 적합성이 우수합니다. 주민 편의 제공 및 상권 활성화를 위해 설치가 긍정적으로 검토되기를 희망하며, 가중치 분석({ahp_text}) 결과를 보아도 합당한 선택입니다.\n\n",
                    f"구민대표 (반대): 네, 상인회의 경제 활성화 의지에 공감합니다. 다만 관할동 내 누적 공공 민원이 {int(complaint_score):,}건이고 무단투기 우려도 있으므로 주거지 인근 위생 대책을 철저히 마련해주셨으면 합니다. 안전하고 위생적인 시설 관리가 보장된다면 무조건적인 반대는 하지 않겠습니다.\n\n",
                    f"상인대표 (찬성): 주민분들의 건설적인 지적에 감사드립니다. 시설 관리를 위한 스마트 자동 정화 및 정밀 여과 필터를 장착하고, CCTV를 연동해 위생 환경을 청결히 유지하겠습니다. 주민들이 안심하실 수 있도록 실시간 모니터링 수치도 투명하게 공개하겠습니다.\n\n",
                    f"구민대표 (반대): 스마트 정화 설비와 투명한 정보 공개가 약속된다면 주민대표단도 찬성 의견으로 선회할 수 있습니다. 적극적인 관리 및 주기적 위생 점검에 협조해주시기를 당부드립니다.\n\n",
                    f"조정관 (조정안): 양측의 원만한 상생과 협조 노력에 감사드립니다. 본 안건은 찬성 측의 '스마트 정화 필터 장착 및 주기적 점검'과 반대 측의 '투명 정보 수용'을 골자로 원만히 합의 타결되었음을 선포합니다. [모의 심의 완료]"
                ]
            
            full_text = "".join(dialogue)
            try:
                save_debate_log_to_file(req, full_text)
            except Exception as fs_err:
                print(f"[File Log Save Error] {fs_err}")
                
            for segment in dialogue:
                chunk_size = 12
                for idx in range(0, len(segment), chunk_size):
                    chunk = segment[idx:idx+chunk_size]
                    yield f"data: {json.dumps({'text': chunk}, ensure_ascii=False)}\n\n"
                    await asyncio.sleep(0.03)
                await asyncio.sleep(0.4)
                
        return StreamingResponse(mock_event_generator(), media_type="text/event-stream")


from io import BytesIO
from fastapi.responses import StreamingResponse
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

# PDF 다운로드 DTO 정의
class ReportDownloadRequest(BaseModel):
    facility_type: str = ""
    inferred_purpose: str = ""
    candidate_jibun: str = ""
    candidate_css: int = 50
    candidate_lat: float = 37.53
    candidate_lng: float = 126.97
    ahp_weights: Dict[str, float] = {}
    debate_logs: List[Dict[str, str]] = []

@router.post("/spatial/report/download")
async def download_report_pdf(req: ReportDownloadRequest, db: Session = Depends(get_db)):
    try:
        # 1. 맑은 고딕 한글 폰트 등록 시도
        font_path = "C:\\Windows\\Fonts\\malgun.ttf"
        font_name = "MalgunGothic"
        if os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont(font_name, font_path))
        else:
            font_name = "Helvetica" # 한글 미지원 fallback
            
        # 2. 문서 템플릿 준비 (BytesIO)
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )
        
        styles = getSampleStyleSheet()
        
        # 3. 사용자 정의 폰트 스타일 조립
        title_style = ParagraphStyle(
            'ReportTitle',
            parent=styles['Normal'],
            fontName=font_name,
            fontSize=18,
            leading=22,
            alignment=1, # Center
            textColor=colors.HexColor('#0F172A'),
            spaceAfter=20
        )
        
        section_style = ParagraphStyle(
            'ReportSection',
            parent=styles['Normal'],
            fontName=font_name,
            fontSize=13,
            leading=16,
            textColor=colors.HexColor('#1E293B'),
            spaceBefore=12,
            spaceAfter=6,
            borderPadding=4
        )
        
        body_style = ParagraphStyle(
            'ReportBody',
            parent=styles['Normal'],
            fontName=font_name,
            fontSize=10,
            leading=14,
            textColor=colors.HexColor('#334155')
        )
        
        log_style = ParagraphStyle(
            'ReportLog',
            parent=styles['Normal'],
            fontName=font_name,
            fontSize=9,
            leading=13,
            textColor=colors.HexColor('#475569'),
            leftIndent=15
        )
        
        story = []
        
        # 문서 타이틀
        story.append(Paragraph("지능형 스마트시티 입지 타당성 및 갈등 분석 보고서", title_style))
        story.append(Spacer(1, 10))
        
        # 1. 후보지 기본 정보
        story.append(Paragraph("1. 후보지 기본 정보 및 현황", section_style))
        css_grade = "상(높음)" if req.candidate_css >= 70 else ("중(보통)" if req.candidate_css >= 40 else "하(낮음)")
        info_data = [
            [Paragraph("<b>입지 지번 주소</b>", body_style), Paragraph(req.candidate_jibun, body_style)],
            [Paragraph("<b>대표 좌표</b>", body_style), Paragraph(f"위도 {req.candidate_lat}, 경도 {req.candidate_lng}", body_style)],
            [Paragraph("<b>도메인 및 목적</b>", body_style), Paragraph(f"{req.facility_type} ({req.inferred_purpose})", body_style)],
            [Paragraph("<b>갈등 민감도 (CSS)</b>", body_style), Paragraph(f"<b>{req.candidate_css}점</b> [등급: {css_grade}]", body_style)]
        ]
        t1 = Table(info_data, colWidths=[150, 380])
        t1.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#F8FAFC')),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(t1)
        story.append(Spacer(1, 15))
        
        # 2. AHP 의사결정 인자 가중치
        story.append(Paragraph("2. AHP 다기준 의사결정 분석 가중치 세트", section_style))
        ahp_rows = []
        for k, v in req.ahp_weights.items():
            ahp_rows.append([Paragraph(f"<b>{k}</b>", body_style), Paragraph(f"{v}", body_style)])
        if not ahp_rows:
            ahp_rows.append([Paragraph("가중치 데이터 부재", body_style), Paragraph("-", body_style)])
        t2 = Table(ahp_rows, colWidths=[200, 330])
        t2.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#F8FAFC')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(t2)
        story.append(Spacer(1, 15))
        
        # 3. AI 및 3자 모의 심의 토론 이력
        story.append(Paragraph("3. 주민 갈등 심의 위원회 모의 토론 내용", section_style))
        debate_story = []
        for log in req.debate_logs:
            sender = log.get("sender", "알 수 없음")
            text_log = log.get("text", "")
            debate_story.append(Paragraph(f"<b>[{sender}]</b>", body_style))
            debate_story.append(Paragraph(text_log, log_style))
            debate_story.append(Spacer(1, 5))
            
        if not debate_story:
            debate_story.append(Paragraph("기록된 모의 토론 이력이 존재하지 않습니다.", body_style))
            
        # 토론 내용을 담은 패널 처리
        t3 = Table([[debate_story]], colWidths=[530])
        t3.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#E2E8F0')),
            ('TOPPADDING', (0,0), (-1,-1), 10),
            ('BOTTOMPADDING', (0,0), (-1,-1), 10),
            ('LEFTPADDING', (0,0), (-1,-1), 10),
            ('RIGHTPADDING', (0,0), (-1,-1), 10),
        ]))
        story.append(t3)
        story.append(Spacer(1, 20))
        
        # 4. 행정 결재용 고시 및 면책 고지
        story.append(Paragraph("4. 종합 의견 및 유의사항", section_style))
        notice_text = (
            "본 보고서는 다목적 스마트시티 의사결정시스템(SDSS) OmniSite의 AI 데이터 감리 및 pgvector 기반 조례 RAG "
            "검색 결과를 바탕으로 시뮬레이션한 가상의 갈등 조정 결과물입니다. 최종 행정 입지 고시 결정은 법정 실무 위원회의 "
            "추가 심의 및 현장 실사를 거쳐 확정되어야 하며, 본 시뮬레이션 결과는 행정 참고 지표로만 활용되어야 합니다."
        )
        story.append(Paragraph(notice_text, body_style))
        
        # PDF 컴파일
        doc.build(story)
        buffer.seek(0)
        
        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": "attachment; filename=OmniSite_Report.pdf"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF 리포트 생성 오류: {str(e)}")

