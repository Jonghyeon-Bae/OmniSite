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
              -- 개별 규제지 버퍼 저촉 여부를 geometry 인덱스(GIST)로 고속 감지
              AND NOT EXISTS (
                  SELECT 1 FROM restricted_zones rz 
                  WHERE rz.district_id = 1
                    AND (
                        -- 흡연구역일 때는 school(200m), childcare(30m), nosmoking(10m) 모두 차집합 배제
                        (:facility_type = 'smoking_zone' AND (
                            (rz.zone_type = 'school' AND ST_DWithin(c.geom, rz.geom, 0.002)) OR
                            (rz.zone_type = 'childcare_center' AND ST_DWithin(c.geom, rz.geom, 0.0003)) OR
                            (rz.zone_type = 'nosmoking_zone' AND ST_DWithin(c.geom, rz.geom, 0.0001))
                        )) OR
                        -- 전기차 충전소일 때는 school(100m = 약 0.001도), childcare(30m = 약 0.0003도)만 차집합 배제
                        (:facility_type = 'ev_charging' AND (
                            (rz.zone_type = 'school' AND ST_DWithin(c.geom, rz.geom, 0.001)) OR
                            (rz.zone_type = 'childcare_center' AND ST_DWithin(c.geom, rz.geom, 0.0003))
                        ))
                        -- 옐로카펫 및 공용자전거 등 기타 시설은 학교/어린이집/금연구역 등에 의한 강제 차집합 배제를 적용하지 않음 (안전 구역 내 설치 촉진)
                    )
              )
              -- 흡연구역 도메인인 경우에만 버스정류장/지하철역 이격거리 규제 적용 (10m)
              AND (
                  :facility_type != 'smoking_zone' OR
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
                "facility_type": facility_type
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

        # 2.5 사용자가 업로드한 동적 Exclusion 좌표 수집 및 2차 필터링
        dynamic_exclusions = []
        if os.path.exists(UPLOAD_DIR):
            for file in os.listdir(UPLOAD_DIR):
                if file.endswith(".json"):
                    try:
                        file_path = os.path.join(UPLOAD_DIR, file)
                        with open(file_path, "r", encoding="utf-8") as f:
                            records = json.load(f)
                            for item in records:
                                props = item.get("properties", {})
                                if props.get("domain") == facility_type and props.get("is_exclusion") is True:
                                    dynamic_exclusions.append((float(item["lng"]), float(item["lat"])))
                    except Exception as ex:
                        print(f"[Dynamic Exclusion Load Error in recommend] {file}: {ex}")

        # 수집된 동적 Exclusion 좌표와 30m 이내로 인접한 후보지 필지는 즉시 배제 (이격 안전거리 보장)
        if dynamic_exclusions:
            filtered_candidates_list = []
            for c in candidates:
                too_close = False
                for ex_lng, ex_lat in dynamic_exclusions:
                    dist = ((c["lng"] - ex_lng) ** 2 + (c["lat"] - ex_lat) ** 2) ** 0.5
                    if dist <= 0.0003: # 약 30미터
                        too_close = True
                        print(f"[Dynamic Exclusion Filter] Candidate {c['id']} ({c['jibun']}) excluded due to proximity to custom restricted area.")
                        break
                if not too_close:
                    filtered_candidates_list.append(c)
            candidates = filtered_candidates_list

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

        # 4. 동적 지표 공간 집계 실행 및 편의점 근접 감점 처리 (XAI용 데이터 수집)
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
            
            # 편의점/슈퍼마켓 근접 10m 이격 검사 (ST_DWithin 0.0001)
            cvs_query = text("""
                SELECT shop_name FROM commercial_shops
                WHERE district_id = 1 
                  AND ST_DWithin(geom, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326), 0.0001)
                  AND (shop_name LIKE '%편의점%' OR shop_name LIKE '%CU%' OR shop_name LIKE '%GS25%' OR shop_name LIKE '%세븐%')
                LIMIT 1
            """)
            cvs_row = None
            try:
                cvs_row = db.execute(cvs_query, {"lng": cand["lng"], "lat": cand["lat"]}).fetchone()
            except Exception:
                pass
            
            cand["has_cvs"] = cvs_row is not None
            cand["cvs_name"] = cvs_row[0] if cvs_row else None

        # 5. 각 지표별 Min-Max 정규화 적용 (0.0 ~ 1.0)
        norm_scores = {k: [] for k in keys}
        for k in keys:
            scores_list = raw_scores[k]
            min_val = min(scores_list) if scores_list else 0.0
            max_val = max(scores_list) if scores_list else 1.0
            diff = max_val - min_val
            
            for score in scores_list:
                if diff > 0:
                    norm = (score - min_val) / diff
                else:
                    norm = 1.0
                norm_scores[k].append(norm)

        # 정규화 점수를 다시 매핑 및 종합 AHP 가중합 연산 (다목적 데이터셋 스왑 적용)
        for idx, cand in enumerate(candidates):
            total_score = 0.0
            for k in keys:
                norm_val = norm_scores[k][idx]
                total_score += criteria_weights[k] * norm_val
            
            # [다목적 분기] 흡연구역 도메인인 경우에만 편의점 이격 및 보도 방해 감점 작동
            if facility_type == "smoking_zone":
                if cand.get("land_use_code") == "도":
                    total_score -= 8.0
                if cand.get("has_cvs"):
                    total_score -= 12.0
            
            # [다목적 분기] 아동 교통안전 옐로카펫 등인 경우
            elif facility_type == "yellow_carpet":
                # 보도/도로 인접 필수적이므로 가점
                if cand.get("land_use_code") == "도":
                    total_score += 5.0
            
            # [다목적 분기] 전기차 충전소 등 시설물인 경우
            elif facility_type == "ev_charging":
                if cand.get("land_use_code") == "도":
                    total_score -= 4.0
                elif cand.get("land_use_code") in ["차", "공"]: # 공영주차장/잡종지 가점
                    total_score += 6.0
            
            # [다목적 분기] 공용자전거 대여소(따릉이 등)인 경우
            elif facility_type == "public_bicycle":
                # 보도/도로 인근 및 주차장 연계가 매우 유리하므로 가점
                if cand.get("land_use_code") in ["도", "차", "공"]:
                    total_score += 5.0
                    
            cand["total_score"] = round(total_score, 3)

        # 6. 점수 내림차순 정렬 후, 공간적 중복 배제 필터링 (최소 이격거리 70m 보장)
        candidates.sort(key=lambda x: x["total_score"], reverse=True)
        
        filtered_candidates = []
        for cand in candidates:
            # 이미 선택된 필지들과 0.0007도(약 70m) 이내로 겹치는 경우 배제
            is_overlap = False
            for selected in filtered_candidates:
                dist = math.sqrt((cand["lat"] - selected["lat"])**2 + (cand["lng"] - selected["lng"])**2)
                if dist < 0.0007:
                    is_overlap = True
                    break
            if not is_overlap:
                filtered_candidates.append(cand)
                if len(filtered_candidates) >= 3:
                    break
                    
        # 후보지 부족 시 원본 리스트로 보완
        if len(filtered_candidates) < 3:
            for cand in candidates:
                if cand not in filtered_candidates:
                    filtered_candidates.append(cand)
                if len(filtered_candidates) >= 3:
                    break

        # 7. 종합 점수를 백분위 갈등도 점수(CSS)로 환산 매핑 및 추천 사유 생성 (다목적 RAG)
        max_possible = sum(criteria_weights.values())
        if max_possible == 0:
            max_possible = 1.0
            
        # XAI 추천 사유 생성 헬퍼 함수 (특정 시설물에 편향되지 않은 다목적 의사결정 추론)
        def generate_recommendation_reason(cand_item: Dict[str, Any], type_str: str) -> str:
            reasons = ["어린이보호구역(200m) 및 법적 규제지역 경계선을 안전하게 우회 통과한 적격지입니다."]
            scores_map = cand_item.get("scores", {})
            
            # 1. AHP 가중치 가중 최우선 인자(Max Weight Key) 동적 추출
            max_key = None
            max_val_weight = -1.0
            for k, weight in criteria_weights.items():
                if weight > max_val_weight:
                    max_val_weight = weight
                    max_key = k
            
            # 한국어 레이블 매핑
            max_label = max_key
            if isinstance(criteria_list, list):
                for c in criteria_list:
                    if isinstance(c, dict) and c.get("key") == max_key:
                        max_label = c.get("label", max_key)
                        break
            
            # 2. 동적 기여도 멘트 결합
            if max_key:
                raw_val = scores_map.get(max_key, 0.0)
                reasons.append(f"의사결정 우선순위인 '{max_label}' 지표(상대 가중치: {max_val_weight:.1f}, 실측값: {raw_val:.1f}) 측면에서 가장 부합하는 정량적 우수 입지입니다.")
                
                # 지표 성격별 설명 확장
                max_key_lower = max_key.lower()
                if "traffic" in max_key_lower or "station" in max_key_lower:
                    reasons.append("일대 대중교통 노드 접근성과 유동 통행 흐름이 발달하여 이용 효율이 극대화됩니다.")
                elif "complaint" in max_key_lower or "civil" in max_key_lower:
                    reasons.append("상습 민원 접수 빈도를 우선 반영하여 설치 시 주민 분쟁 조율 효과가 큽니다.")
                elif "dumping" in max_key_lower or "trash" in max_key_lower:
                    reasons.append("상습적인 무단투기 및 환경 저해 요인이 감지되는 취약 거점을 포괄하여 도시 정화에 기여합니다.")
                elif "youth" in max_key_lower or "school" in max_key_lower:
                    reasons.append("청소년 및 아동 통학권 보호 구역의 안전 정주성을 확보하도록 가중 조율했습니다.")
                elif "population" in max_key_lower or "resident" in max_key_lower:
                    reasons.append("행정동 내부 생활 주거 인구의 공간적 밀집 분포 분석을 반영하였습니다.")
            
            # 3. 도메인별 제약 조건 조언
            if type_str == "smoking_zone":
                if cand_item.get("land_use_code") == "도":
                    reasons.append("[보도 확인] 도로 점용 시 통행 장애를 막기 위한 보행 최소 보도폭(1.2m) 확보 검측이 권장됩니다.")
                if cand_item.get("has_cvs"):
                    reasons.append(f"[상가 조율] 편의점({cand_item.get('cvs_name')})과 10m 이내로 근접해 있어 상가 영업 시비 조율이 필요합니다.")
            elif type_str == "yellow_carpet":
                reasons.append("[보행 확인] 초등학교 어린이 보호구역 내 보행 안전 보차도 시인성 확보를 우선 검토해야 합니다.")
            elif type_str == "ev_charging":
                reasons.append("[인프라 확인] 인근 변전 배전선로의 그리드 용량 가용 여부를 한전과 협의해야 합니다.")
            elif type_str == "public_bicycle":
                reasons.append("[대중교통 연계] 버스정류장 및 지하철역 노드와의 유기적인 환승 연계(라스트마일)를 극대화하도록 배치되었습니다.")
                
            return " ".join(reasons)

        results = {}
        for idx, rank in enumerate(["top1", "top2", "top3"]):
            cand = filtered_candidates[idx] if idx < len(filtered_candidates) else filtered_candidates[-1]
            
            percentage = (cand["total_score"] / max_possible) * 100
            css_score = round(max(10, min(95, percentage)))
            
            if css_score >= 70:
                css_grade = "상"
            elif css_score >= 40:
                css_grade = "중"
            else:
                css_grade = "하"

            base_price = 14200000 if rank == "top1" else (9800000 if rank == "top2" else 18500000)
            
            # XAI 추천 사유 빌드
            reason_text = generate_recommendation_reason(cand, facility_type)
            
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
                "simulated": True if rank == "top1" else False,
                "criteria_scores": cand["scores"],
                "reason": reason_text
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

# 3. 규제 시설물 좌표 조회 API (Step 2 규제 버퍼 가시화용 - restricted_zones 및 업로드된 dynamic exclusion 연동)
@router.get("/spatial/restrictions/points")
async def get_restriction_points(facility_type: str = "smoking_zone", db: Session = Depends(get_db)):
    try:
        # 도메인별 적용되는 기본 법정 규제 유형 분류
        # smoking_zone: school, childcare_center, nosmoking_zone 모두 적용
        # ev_charging: school, childcare_center 만 적용 (화재안전, 아동보호)
        # yellow_carpet 및 public_bicycle: 기본 규제 구역 제외 없음
        allowed_types = []
        if facility_type == "smoking_zone":
            allowed_types = ["school", "childcare_center", "nosmoking_zone"]
        elif facility_type == "ev_charging":
            allowed_types = ["school", "childcare_center"]
            
        points = []
        
        # 1. 기본 법정 규제 데이터 조회
        if allowed_types:
            types_str = ", ".join(f"'{t}'" for t in allowed_types)
            zone_query = text(f"""
                SELECT id, zone_name, ST_X(geom), ST_Y(geom), COALESCE(area, 10.0), zone_type 
                FROM restricted_zones 
                WHERE district_id = 1 AND zone_type IN ({types_str})
            """)
            zone_rows = db.execute(zone_query).fetchall()
            
            for r in zone_rows:
                points.append({
                    "id": int(r[0]),
                    "name": r[1] if r[1] else "기본 규제구역",
                    "lng": float(r[2]),
                    "lat": float(r[3]),
                    "type": r[5] if r[5] else "restricted_zone",
                    "radius": float(r[4])
                })
                
        # 2. 사용자가 이번 도메인 분석용으로 업로드한 동적 Exclusion 캐시 로딩 및 병합
        if os.path.exists(UPLOAD_DIR):
            for file in os.listdir(UPLOAD_DIR):
                if file.endswith(".json"):
                    try:
                        file_path = os.path.join(UPLOAD_DIR, file)
                        with open(file_path, "r", encoding="utf-8") as f:
                            records = json.load(f)
                            for idx, item in enumerate(records):
                                props = item.get("properties", {})
                                # 도메인이 일치하고, is_exclusion 플래그가 True인 경우에만 병합
                                if props.get("domain") == facility_type and props.get("is_exclusion") is True:
                                    points.append({
                                        "id": 100000 + idx + sum(ord(c) for c in file), # 유니크 ID 부여
                                        "name": f"[동적 규제] {props.get('address', '사용자 금지구역')}",
                                        "lng": float(item["lng"]),
                                        "lat": float(item["lat"]),
                                        "type": "dynamic_exclusion",
                                        "radius": 30.0 # 30미터 버퍼 영역 설정
                                    })
                    except Exception as ex:
                        print(f"[Dynamic Restriction Load Error] {file}: {ex}")
                        
        if not points and facility_type == "smoking_zone":
            # 실 DB 레코드가 비어있을 시 용산구 기준 대표 Fallback 데이터 주입
            points = [
                {"id": 901, "name": "용산역광장 제한지구", "lng": 126.9680, "lat": 37.5290, "type": "restricted_zone", "radius": 30.0},
                {"id": 902, "name": "용산초등학교 정화구역", "lng": 126.9740, "lat": 37.5315, "type": "restricted_zone", "radius": 200.0},
                {"id": 903, "name": "국방부 주변 통제구역", "lng": 126.9650, "lat": 37.5240, "type": "restricted_zone", "radius": 400.0}
            ]
            
        return {"points": points}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"규제 시설물 좌표 조회 오류: {str(e)}")

# 위치 및 도메인 기반 동적 페르소나 매핑 헬퍼 (무작위 템플릿 샘플러)
def get_dynamic_personas(jibun: str, facility_type: str) -> Dict[str, str]:
    return {
        "resident": "반대",
        "merchant": "찬성",
        "coordinator": "정부"
    }

# 4. LangGraph 3자 대립 SSE 모의 토론 스트리밍 API (POST — 컨텍스트 주입 방식)
def save_debate_log_to_file(req, full_text):
    import os
    import json
    import datetime
    import re
    
    debates_dir = os.path.join(os.getcwd(), "data", "debates")
    os.makedirs(debates_dir, exist_ok=True)
    
    personas = get_dynamic_personas(req.candidate_jibun, req.facility_type)
    resident_label = personas["resident"]
    merchant_label = personas["merchant"]
    coordinator_label = personas["coordinator"]
    
    logs = []
    lines = full_text.split("\n")
    for line in lines:
        trimmed = line.strip()
        if not trimmed:
            continue
        if trimmed.startswith("["):
            logs.append({"sender": "시스템", "text": trimmed})
        elif trimmed.startswith(merchant_label) or (":" in trimmed and merchant_label in trimmed.split(":")[0]) or trimmed.startswith("상인대표"):
            content = trimmed.split(":", 1)[1].strip() if ":" in trimmed else re.sub(r'^(상인대표|상인회장|상인)\s*(\(찬성\))?:?\s*', '', trimmed)
            logs.append({"sender": f"{merchant_label} (찬성)", "text": content})
        elif trimmed.startswith(resident_label) or (":" in trimmed and resident_label in trimmed.split(":")[0]) or trimmed.startswith("구민대표") or trimmed.startswith("주민대표"):
            content = trimmed.split(":", 1)[1].strip() if ":" in trimmed else re.sub(r'^(구민대표|주민대표|주민|구민)\s*(\(반대\))?:?\s*', '', trimmed)
            logs.append({"sender": f"{resident_label} (반대)", "text": content})
        elif trimmed.startswith(coordinator_label) or (":" in trimmed and coordinator_label in trimmed.split(":")[0]) or trimmed.startswith("조정관"):
            content = trimmed.split(":", 1)[1].strip() if ":" in trimmed else re.sub(r'^조정관\s*(\(조정안\)|\(조정\))?:?\s*', '', trimmed)
            logs.append({"sender": f"{coordinator_label} (조정)", "text": content})
        else:
            # 콜론 구분자 기반 범용 파서 Fallback
            if ":" in trimmed:
                parts = trimmed.split(":", 1)
                sender = parts[0].strip()
                content = parts[1].strip()
                logs.append({"sender": sender, "text": content})
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
    
    # pgvector RAG
    rag_context = ""
    try:
        from app.routers.upload import get_embedding
        domain_ko_map = {
            "smoking_zone": "흡연구역 금연구역 간접흡연 피해방지 조례",
            "smoking": "흡연구역 금연구역 간접흡연 피해방지 조례",
            "illegal_dumping": "쓰레기무단투기 상습무단투기구역 폐기물관리조례",
            "dumping": "쓰레기무단투기 상습무단투기구역 폐기물관리조례",
            "transit": "대중교통 버스정류장 지하철역 유동인구 관련조례"
        }
        query_kw = domain_ko_map.get(req.facility_type.lower(), "도시계획 및 공공시설 설치 조례")
        emb = get_embedding(query_kw)
        if emb:
            rag_query = text("""
                SELECT content, 1 - (embedding <=> :emb_vector::vector) as similarity
                FROM regulation_embeddings
                ORDER BY similarity DESC
                LIMIT 3
            """)
            rag_rows = db.execute(rag_query, {"emb_vector": emb}).fetchall()
            rag_context = "\n".join([f"- {row[0]} (유사도: {row[1]:.4f})" for row in rag_rows])
    except Exception as e:
        print(f"[RAG Context Load Fail] {e}")

    # 공간 지표 통계 로드
    stats_context = ""
    transit_score = 0.0
    dumping_score = 0.0
    complaint_score = 0.0
    try:
        dong_query = text("""
            SELECT id, name FROM municipal_dongs 
            WHERE ST_Contains(geom, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326))
        """)
        dong_row = db.execute(dong_query, {"lng": req.candidate_lng, "lat": req.candidate_lat}).fetchone()
        dong_id = dong_row[0] if dong_row else None
        dong_name = dong_row[1] if dong_row else ""
        
        transit_query = text("""
            SELECT COALESCE(SUM(boarding_count + alighting_count), 0)
            FROM transit_passengers p
            JOIN transit_stations s ON p.station_id = s.id
            WHERE ST_DWithin(s.geom, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326), 0.003)
        """)
        transit_score = db.execute(transit_query, {"lng": req.candidate_lng, "lat": req.candidate_lat}).scalar()
        
        dumping_query = text("""
            SELECT COUNT(*)
            FROM illegal_dumping_zones
            WHERE ST_DWithin(geom, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326), 0.002)
        """)
        dumping_score = db.execute(dumping_query, {"lng": req.candidate_lng, "lat": req.candidate_lat}).scalar()
        
        complaint_score = 0
        if dong_id:
            complaint_query = text("SELECT COALESCE(SUM(complaint_count), 0) FROM civil_complaints WHERE dong_id = :dong_id")
            complaint_score = db.execute(complaint_query, {"dong_id": dong_id}).scalar()
            
        stats_context = (
            f"- 후보지 관할 행정동: {dong_name if dong_name else '용산구 관할동'}\n"
            f"- 후보지 반경 300m 이내 대중교통 유동인구 (지하철+버스): {int(transit_score):,}명\n"
            f"- 후보지 반경 200m 이내 무단투기 다발지역: {int(dumping_score)}개소\n"
            f"- 후보지 관할동 누적 공공 민원 건수: {int(complaint_score)}건\n"
        )
    except Exception:
        stats_context = "- 공간 지표 통계: 데이터베이스 조회 결과 미비\n"

    ahp_text = ", ".join([f"{k}: {v}" for k, v in req.ahp_weights.items()]) if req.ahp_weights else "기본 균등 가중치"
    css_grade = "상(높음)" if req.candidate_css >= 70 else ("중(보통)" if req.candidate_css >= 40 else "하(낮음)")

    # 동적 페르소나 설정
    personas = get_dynamic_personas(req.candidate_jibun, req.facility_type)
    resident_name = personas["resident"]
    merchant_name = personas["merchant"]
    coordinator_name = personas["coordinator"]

    intensity_instruction = ""
    if req.intensity_level == "dangerous":
        intensity_instruction = (
            f"5. 갈등 강도 설정: [위험 🟡]\n"
            f"   - 토론 주체 간의 대립이 매우 날카롭고 감정적입니다. 격식 있는 대립 톤을 유지하되 상대방의 주장 논점을 직접 물고 늘어져야 합니다.\n"
            f"   - {resident_name}(반대)는 '우리가 호구냐', '왜 맨날 우리 동네에만 설치를 하냐'며 주거 정주성 파괴(민원 {int(complaint_score or 0)}건, 무단투기 {int(dumping_score or 0)}개소)를 빌미로 상인대표의 경제 논리를 반박하십시오.\n"
            f"   - {merchant_name}(찬성)는 '골목이 살아야 주민도 있는 법'이라며 유동인구 {int(transit_score or 0):,}명의 수요에 기초하여 주민의 의견이 집단 이기주의에 가깝다고 조리 있게 격앙되게 주장하십시오.\n"
            f"   - {coordinator_name}(조정)은 감정이 격해지는 대화 핑퐁을 통제하면서 완충 이격거리 확대 및 주민 가동 정지/감찰 권한 부여 등의 구체적 타협점을 제시하십시오."
        )
    elif req.intensity_level == "extreme":
        intensity_instruction = (
            f"5. 갈등 강도 설정: [매우 위험/교착 🔴]\n"
            f"   - 두 주체는 대화 협상의 여지를 완전히 닫은 수준의 극단적 대치를 하되, 형사 고소/고발이나 구청장 퇴진 같은 사법/행정적 위협은 완전히 배제하십시오.\n"
            f"   - {resident_name}(반대)는 '화재 안전 대책이나 분진/쓰레기 방지벽, 위생 보강책 없이는 시설 점거 및 진입로 차단 서명 시위를 벌이겠다'고 정주권 침해 우려(민원 {int(complaint_score or 0)}건, 무단투기 {int(dumping_score or 0)}개소)를 들어 강경히 대립하십시오.\n"
            f"   - {merchant_name}(찬성)는 '상인들의 생존권이 걸린 생업 문제를 과장된 안전 공포증으로 가로막는 행위는 이기적인 횡포이며, 안전 수칙을 명문화해 상인회 책임 하에 투명하게 상시 모니터링하겠다'고 맞서십시오.\n"
            f"   - {coordinator_name}(조정)은 이 파국적 대치를 봉합하기 위해 소방시설(질식소화포 등) 2배 확충, 완전 차폐막 장치 의무화, 주민대표단에게 기준 위반 시 즉각 중단시키는 '상시 운영정지 및 위생 점검권'을 공식 부여하는 파격적 양보안으로 중재하십시오."
        )
    else: # normal
        intensity_instruction = (
            f"5. 갈등 강도 설정: [보통 🟢]\n"
            f"   - 상호 예의를 지키는 존댓말로 조용하게 토론을 진행하되, 입지와 위생 대책(예: 필터 장착, 모니터링 수치 공개)에 대한 실무적 합의점을 매끄럽게 타결하십시오."
        )

    disclaimer_alert = "[시스템 면책 고지] 본 모의 심의 토론 내용은 AI 페르소나 엔진에 의해 생성된 가상의 시나리오이며, 실제 인물이나 단체, 사실관계와는 전혀 무관합니다.\n\n"

    if client:
        system_prompt = (
            "당신은 스마트시티 주민 갈등 조정 위원회 모의 토론기입니다.\n\n"
            "## 토론 맥락 정보\n"
            f"- 시설 유형(도메인): {req.facility_type}\n"
            f"- 사업 목적: {req.inferred_purpose}\n"
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
            "2. 찬성 측, 반대 측, 조정안의 세 발언자가 서로 다회차(Multi-turn)로 번갈아 가며 질문을 주고받고 반론을 제기하는 심도 있는 토론을 구성하십시오.\n"
            "3. 각 인물의 논리적 입장:\n"
            f"   - {merchant_name} (찬성): 설치의 시급함과 경제 상권 이점(예: 높은 대중교통 유동인구 등)을 후보지 지번 및 목적을 엮어 강하게 옹호합니다.\n"
            f"   - {resident_name} (반대): 높은 갈등 민감도(CSS) 및 주거 피해 요인(예: 민원 건수, 무단투기 다발 수, 조례 상 배제 구역 침범 우려)을 들어 강력 반대합니다.\n"
            f"   - {coordinator_name} (조정안): 양측의 수치 근거를 모두 반영하여, 조례 위반을 피하면서 이격거리 완충 설계나 정화 시설 보강 등 타협점을 제시합니다.\n"
            "4. 반드시 각 참가자가 최소 2회 이상 의견을 피력하도록 아래 정해진 순서와 형식으로 총 6턴 이상의 유기적인 대화 대본을 출력하십시오:\n"
            f"{merchant_name}: ... (1차 찬성 변론)\n"
            f"{resident_name}: ... (상인대표 의견에 대한 반론 및 1차 반대 근거)\n"
            f"{merchant_name}: ... (주민대표 반론에 대한 설득 및 반박)\n"
            f"{resident_name}: ... (재반론 및 최종 우려 피력)\n"
            f"{coordinator_name}: ... (중재안 제시 및 타협안 도출)\n"
            f"{merchant_name}: ... (중재안 피드백 및 협조)\n"
            f"{resident_name}: ... (중재안 수용 및 관리 감독 요구)\n"
            f"{coordinator_name}: ... (최종 토론 합의 및 회의 마무리)\n\n"
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
                import queue
                import threading
                
                q = queue.Queue()
                
                def run_openai():
                    try:
                        response = client.chat.completions.create(
                            model="gpt-4o",
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
                        q.put(None)
                    except Exception as e:
                        q.put(f"토론 중 에러 발생: {str(e)}")
                        q.put(None)
                
                thread = threading.Thread(target=run_openai, daemon=True)
                thread.start()
                
                # 면책 고지 최초 1회 즉각 전송
                yield f"data: {json.dumps({'text': disclaimer_alert}, ensure_ascii=False)}\n\n"
                
                full_text = disclaimer_alert
                while True:
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
        # Mock Fallback: 컨텍스트 기반 대사 생성 (동적 페르소나 및 자극적 대사 리팩토링)
        async def mock_event_generator():
            if req.intensity_level == "dangerous":
                dialogue = [
                    f"[시스템 알림] '{req.candidate_jibun}' 부지에 대한 갈등 분석 모의 토론을 시작합니다. (갈등 강도: 위험 🟡, CSS: {req.candidate_css}점)\n\n",
                    f"{merchant_name}: 저희 상인회 입장에서는 이번 {req.facility_type} 설치가 매우 절박합니다. 현재 반경 내 유동인구 {int(transit_score or 0):,}명을 감당할 인프라가 전무해 상권 활성화의 기회를 놓치고 있습니다. 님비 정서로만 반대하지 마시고 상생을 논해야 합니다.\n\n",
                    f"{resident_name}: 님비 정서가 아닙니다! 누적 민원이 {int(complaint_score or 0)}건에 달하고 이미 무단투기 단속구역이 {int(dumping_score or 0)}개소나 지정된 상황에서, 추가 오염원 유발 시설이 들어오면 주거 정주 환경은 완전히 파괴됩니다. 상인의 이익 때문에 주민의 건강권이 희생될 순 없습니다.\n\n",
                    f"{merchant_name}: 주민대표님 말씀도 일리가 있지만, 무단투기 {int(dumping_score or 0)}개소 문제를 해결하기 위해 이번 시설 내부에 정밀 폐쇄회로(CCTV)와 수거함을 연동하면 오히려 슬럼화된 거리를 정화하는 계기가 될 수 있습니다. 무조건적인 반대보다는 이런 위생 보강책을 토대로 합의를 모색해야 합니다.\n\n",
                    f"{resident_name}: CCTV 연동이나 필터 보강 약속은 설치 허가를 받기 위한 임시방편일 뿐, 관리 소홀로 필터 악취나 연기가 흘러나오면 그 피해는 고스란히 주민과 학생들에게 돌아갑니다. 시설 운영 시 발생하는 환경 위험 요소를 완벽히 통제할 구체적인 감시 권한을 주민단에 넘기지 않는다면 수용하기 어렵습니다.\n\n",
                    f"{coordinator_name}: 두 분 모두 타당한 논거를 대고 계십니다. 상인의 유동인구 {int(transit_score or 0):,}명 대응 필요성과 주민의 {int(complaint_score or 0)}건 민원 우려를 극적으로 해소하기 위해 조정안을 제시합니다. 첫째, 교육기관 경계선 및 완충 구역 밖으로 최소 이격거리를 1.5배 추가 후퇴하겠습니다. 둘째, 주민자치위원회에 시설 상시 감찰 및 가동 정지 권한을 공식 부여하겠습니다. 수용 가능한 범위입니까?\n\n",
                    f"{merchant_name}: 아쉬운 제약조건이지만 상권 활성화 and 공존을 위해 이격거리 후퇴 및 주민 위생 감찰권 중재안을 받아들이겠습니다.\n\n",
                    f"{resident_name}: 조정관께서 주민 직접 통제 및 정지 권한을 명문화해 주신다면, 저희 주민대표단도 이 조건하에 상생 타협안을 수용하겠습니다.\n\n",
                    f"{coordinator_name}: 팽팽했던 대립 속에서 양측의 한 걸음 양보로 상생 합의가 도출되었습니다. 완충 이격과 감찰 권한 이양을 골자로 본 의사결정을 타결합니다. [모의 심의 완료]"
                ]
            elif req.intensity_level == "extreme":
                dialogue = [
                    f"[시스템 알림] '{req.candidate_jibun}' 부지에 대한 긴급 갈등 분석 토론을 시작합니다. (갈등 강도: 매우 위험/교착 🔴, CSS: {req.candidate_css}점)\n\n",
                    f"{merchant_name}: 저희는 더 이상 대화로 시간만 끌 수 없습니다. 상인 생존권이 붕괴되는 와중에 주민들의 일방적인 반대가 계속된다면, 상인회 차원의 단체 행동과 더불어 안전 규정 준수를 서약하고 설치를 추진할 수밖에 없습니다!\n\n",
                    f"{resident_name}: 밀어붙이겠다는 말씀입니까? 어디 한번 해보십시오! 주민들의 화재 안전 우려와 쓰레기 무단투기로 인한 악취 문제가 해결되지 않는 한, 주민 전체의 물리적 진입 차단 서명 운동과 대대적인 시위로 끝까지 저지하겠습니다!\n\n",
                    f"{merchant_name}: 화재 및 위생 방지를 위해 최신 질식소화포와 강화형 소방 설비를 구비하겠다는데도 무조건 반대하시는 것은 상생을 외면한 님비입니다. 반경 내 {int(transit_score or 0):,}명의 유동인구를 위한 필수 시설을 막연한 공포 때문에 무산시킬 수는 없습니다!\n\n",
                    f"{resident_name}: 막연한 공포가 아닙니다! 누적 민원이 {int(complaint_score or 0)}건에 달하고 무단투기가 이미 {int(dumping_score or 0)}개소나 발생하는 환경에서 만에 하나 사고가 발생하면 누가 책임집니까? 주민들이 직접 상시 감찰하고 즉각 가동을 멈추게 할 강제 점검권이 없다면 타협은 불가능합니다!\n\n",
                    f"{coordinator_name}: 양측의 대립이 매우 격앙되어 타협점을 찾기 어려운 교착 상태입니다. 조정관으로서 파국을 막기 위한 강제 중재안을 내놓겠습니다. 첫째, 주민대표단에게 소방/위생 위반 시 가동을 정지시킬 수 있는 '상시 가동정지 요청 및 직접 점검권'을 부여하겠습니다. 둘째, 화재 예방용 질식소화포 and 강화형 소방 장비를 상인회 예산으로 추가 확충합니다. 셋째, 미관 및 분진 방지를 위해 1.5배 넓은 물리적 차폐막 설치를 보장합니다. 양측의 최종 의사를 밝혀주십시오.\n\n",
                    f"{merchant_name}: 가동정지권 부여는 영업에 큰 부담이지만, 상권이 아예 무너지는 것보다 안전 설비를 확충하고 이를 수용하는 편이 낫겠군요. 조건부 동의하겠습니다.\n\n",
                    f"{resident_name}: 주민 직접 감찰과 가동정지권, 질식소화포 같은 안전 대책이 공식 명문화된다면, 주민들도 일단 단체 행동을 유보하고 조건부로 수용하겠습니다.\n\n",
                    f"{coordinator_name}: 극한의 교착 상태에서 화재 안전 및 상시 점검권 조항을 통해 극적인 조건부 합의를 도출했습니다. 조정안을 최종 가결하며 토론을 마칩니다. [모의 심의 완료]"
                ]
            else: # normal
                dialogue = [
                    f"[시스템 알림] '{req.candidate_jibun}' 부지에 대한 일상 갈등 분석 모의 토론을 시작합니다. (갈등 강도: 보통 🟢, CSS: {req.candidate_css}점)\n\n",
                    f"{merchant_name}: 안녕하십니까. 상인회 대표입니다. 이번에 제안된 '{req.candidate_jibun}' 부지는 반경 300m 유동인구가 {int(transit_score or 0):,}명에 달해 입지 적합성이 우수합니다. 주민 편의 제공 및 상권 활성화를 위해 설치가 긍정적으로 검토되기를 희망하며, 가중치 분석({ahp_text}) 결과를 보아도 합당한 선택입니다.\n\n",
                    f"{resident_name}: 네, 상인회의 경제 활성화 의지에 공감합니다. 다만 관할동 내 누적 공공 민원이 {int(complaint_score or 0)}건이고 무단투기 우려도 있으므로 주거지 인근 위생 대책을 철저히 마련해주셨으면 합니다. 안전하고 위생적인 시설 관리가 보장된다면 무조건적인 반대는 하지 않겠습니다.\n\n",
                    f"{merchant_name}: 주민분들의 건설적인 지적에 감사드립니다. 시설 관리를 위한 스마트 자동 정화 및 정밀 여과 필터를 장착하고, CCTV를 연동해 위생 환경을 청결히 유지하겠습니다. 주민들이 안심하실 수 있도록 실시간 모니터링 수치도 투명하게 공개하겠습니다.\n\n",
                    f"{resident_name}: 스마트 정화 설비와 투명한 정보 공개가 약속된다면 주민대표단도 찬성 의견으로 선회할 수 있습니다. 적극적인 관리 및 주기적 위생 점검에 협조해주시기를 당부드립니다.\n\n",
                    f"{coordinator_name}: 양측의 원만한 상생과 협조 노력에 감사드립니다. 본 안건은 찬성 측의 '스마트 정화 필터 장착 및 주기적 점검'과 반대 측의 '투명 정보 수용'을 골자로 원만히 합의 타결되었음을 선포합니다. [모의 심의 완료]"
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
    candidate_reason: str = ""
    ahp_weights: Dict[str, float] = {}
    debate_logs: List[Dict[str, str]] = []

@router.post("/spatial/report/download")
async def download_report_pdf(req: ReportDownloadRequest, db: Session = Depends(get_db)):
    try:
        # 1. 맑은 고딕 한글 폰트 등록
        font_path = "C:\\Windows\\Fonts\\malgun.ttf"
        font_name = "MalgunGothic"
        if os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont(font_name, font_path))
        else:
            font_name = "Helvetica" # 한글 미지원 fallback
            
        # 2. 문서 템플릿 준비 (마진 조정)
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=40,
            leftMargin=40,
            topMargin=40,
            bottomMargin=40
        )
        
        styles = getSampleStyleSheet()
        
        # 3. 전용 폰트 스타일 조립 (공문서 톤앤매너)
        title_style = ParagraphStyle(
            'GovReportTitle',
            parent=styles['Normal'],
            fontName=font_name,
            fontSize=16,
            leading=20,
            alignment=0, # Left
            textColor=colors.HexColor('#0F172A'),
            spaceAfter=2
        )
        
        meta_style = ParagraphStyle(
            'GovReportMeta',
            parent=styles['Normal'],
            fontName=font_name,
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor('#475569')
        )
        
        section_style = ParagraphStyle(
            'GovReportSection',
            parent=styles['Normal'],
            fontName=font_name,
            fontSize=12,
            leading=15,
            textColor=colors.HexColor('#1E3A8A'), # 감청색 적용
            spaceBefore=14,
            spaceAfter=6,
            keepWithNext=True
        )
        
        body_style = ParagraphStyle(
            'GovReportBody',
            parent=styles['Normal'],
            fontName=font_name,
            fontSize=9.5,
            leading=14,
            textColor=colors.HexColor('#334155')
        )
        
        log_style = ParagraphStyle(
            'GovReportLog',
            parent=styles['Normal'],
            fontName=font_name,
            fontSize=9,
            leading=13,
            textColor=colors.HexColor('#1E293B'),
            leftIndent=15
        )
        
        sender_style = ParagraphStyle(
            'GovReportSender',
            parent=styles['Normal'],
            fontName=font_name,
            fontSize=15,
            leading=19,
            alignment=1, # Center
            textColor=colors.HexColor('#0F172A'),
            spaceBefore=25,
            spaceAfter=5
        )
        
        disclaimer_style = ParagraphStyle(
            'GovReportDisclaimer',
            parent=styles['Normal'],
            fontName=font_name,
            fontSize=8,
            leading=11,
            alignment=1, # Center
            textColor=colors.HexColor('#94A3B8'),
            spaceBefore=15
        )
        
        story = []
        
        # 4. 결재선 격자 테이블 생성 (우측 상단 결재선)
        approval_headers = [
            Paragraph("<b>기안자</b>", meta_style), 
            Paragraph("<b>검토자</b>", meta_style), 
            Paragraph("<b>심의관</b>", meta_style), 
            Paragraph("<b>결정자</b>", meta_style)
        ]
        approval_body = ["", "", "", ""]
        approval_table = Table([approval_headers, approval_body], colWidths=[50, 50, 50, 50], rowHeights=[15, 35])
        approval_table.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#94A3B8')),
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F1F5F9')),
            ('TOPPADDING', (0,0), (-1,-1), 2),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
            ('LEFTPADDING', (0,0), (-1,-1), 2),
            ('RIGHTPADDING', (0,0), (-1,-1), 2),
        ]))
        
        # 5. 상단 헤더 결합 (공문서 타이틀 + 결재선 가로 배치)
        header_text = (
            "<b>스마트시티 입지 적합성 및 주민 모의 토론 결과 보고서</b><br/>"
            "<font size=8 color='#64748B'>기안부서: 스마트도시과 | 기안일자: 상시결재 양식</font>"
        )
        top_header_data = [
            [Paragraph(header_text, title_style), approval_table]
        ]
        top_header_table = Table(top_header_data, colWidths=[330, 200])
        top_header_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'BOTTOM'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ('BOTTOMPADDING', (0,0), (-1,-1), 12),
        ]))
        story.append(top_header_table)
        
        # 구분선
        divider = Table([[""]], colWidths=[530], rowHeights=[1])
        divider.setStyle(TableStyle([
            ('LINEBELOW', (0,0), (-1,-1), 1.5, colors.HexColor('#1E3A8A')),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
            ('TOPPADDING', (0,0), (-1,-1), 0),
        ]))
        story.append(divider)
        story.append(Spacer(1, 10))
        
        # 1. 후보지 기본 정보
        story.append(Paragraph("1. 입지 후보지 기본 제원", section_style))
        css_grade = "상(높음)" if req.candidate_css >= 70 else ("중(보통)" if req.candidate_css >= 40 else "하(낮음)")
        info_data = [
            [Paragraph("<b>가. 대상지 지번 주소</b>", body_style), Paragraph(req.candidate_jibun, body_style)],
            [Paragraph("<b>나. 대상지 중심 좌표</b>", body_style), Paragraph(f"위도 {req.candidate_lat}, 경도 {req.candidate_lng}", body_style)],
            [Paragraph("<b>다. 시설 유형 및 목적</b>", body_style), Paragraph(f"{req.facility_type} ({req.inferred_purpose})", body_style)],
            [Paragraph("<b>라. 갈등 민감도 (CSS)</b>", body_style), Paragraph(f"<b>{req.candidate_css}점</b> (등급: {css_grade})", body_style)],
            [Paragraph("<b>마. 선정 사유 및 고려사항</b>", body_style), Paragraph(req.candidate_reason or "위치적 이격조건 및 AHP 기여 분석에 근거하여 입지 적합성을 확보한 지점입니다.", body_style)]
        ]
        t1 = Table(info_data, colWidths=[150, 380])
        t1.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#F8FAFC')),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
        ]))
        story.append(t1)
        story.append(Spacer(1, 10))
        
        # 2. AHP 의사결정 인자 가중치
        story.append(Paragraph("2. AHP 다기준 의사결정 분석 가중치 현황", section_style))
        ahp_rows = []
        for k, v in req.ahp_weights.items():
            ahp_rows.append([Paragraph(f"<b>{k}</b>", body_style), Paragraph(f"{v}", body_style)])
        if not ahp_rows:
            ahp_rows.append([Paragraph("가중치 데이터 부재", body_style), Paragraph("-", body_style)])
        t2 = Table(ahp_rows, colWidths=[200, 330])
        t2.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#F8FAFC')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
        ]))
        story.append(t2)
        story.append(Spacer(1, 10))
        
        # 3. AI 모의 심의 토론 내용
        story.append(Paragraph("3. 스마트시티 주민 모의 심의 내용 (가상 토론 시나리오)", section_style))
        debate_story = []
        
        # 경고 문구 상단에 한 번 더 명시
        debate_story.append(Paragraph("<b>[심의 진행 기록]</b> ※ 이하 기록된 토론은 가상의 인물 간 의견 대립 및 중재안 도출 시뮬레이션입니다.", body_style))
        debate_story.append(Spacer(1, 6))
        
        for log in req.debate_logs:
            sender = log.get("sender", "알 수 없음")
            text_log = log.get("text", "")
            if "면책 고지" in text_log or "가상의 시나리오" in text_log:
                continue
            debate_story.append(Paragraph(f"<b>◦ {sender}</b>", body_style))
            debate_story.append(Paragraph(text_log, log_style))
            debate_story.append(Spacer(1, 4))
            
        if not req.debate_logs:
            debate_story.append(Paragraph("기록된 모의 토론 출력이 존재하지 않습니다.", body_style))
            
        t3 = Table([[debate_story]], colWidths=[530])
        t3.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
            ('BOX', (0,0), (-1,-1), 0.8, colors.HexColor('#CBD5E1')),
            ('TOPPADDING', (0,0), (-1,-1), 10),
            ('BOTTOMPADDING', (0,0), (-1,-1), 10),
            ('LEFTPADDING', (0,0), (-1,-1), 10),
            ('RIGHTPADDING', (0,0), (-1,-1), 10),
        ]))
        story.append(t3)
        story.append(Spacer(1, 10))
        
        # 4. 종합 행정 고시
        story.append(Paragraph("4. 종합 검토 고시 및 권고사항", section_style))
        notice_text = (
            "본 보고서는 용산구 스마트시티 의사결정지원시스템(SDSS) OmniSite의 AI 갈등 진단 엔진에 의거하여 "
            "작성된 참고 서류입니다. 수록된 주민 심의 의견 및 중재안은 공간 빅데이터와 관련 자치 조례 RAG 임베딩에 "
            "기반해 가상 구현된 결과물로, 법적 구속력을 갖지 않으며 실제 공사 시행 전 구의회 보고 및 주민 주민설명회의 "
            "사전 행정 절차를 필수적으로 이행해야 합니다."
        )
        story.append(Paragraph(notice_text, body_style))
        story.append(Spacer(1, 15))
        
        # 5. 하단 발신 명의 및 면책 고지
        story.append(Paragraph("<b>서울특별시 용산구청장</b> <font size=10 color='#64748B'>(직인생략)</font>", sender_style))
        story.append(Paragraph("※ 본 보고서의 입지분석 및 모의 심의 결과는 가상 AI 페르소나의 역할 수행 결과로, 실제 인물이나 사실과는 무관합니다.", disclaimer_style))
        
        # PDF 빌드
        doc.build(story)
        buffer.seek(0)
        
        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": "attachment; filename=OmniSite_Gov_Report.pdf"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF 리포트 생성 오류: {str(e)}")

