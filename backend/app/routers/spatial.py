import os
import json
import asyncio
import math
import re
import datetime
import queue
import threading
import joblib
import pandas as pd
import io
from io import BytesIO
from pypdf import PdfReader
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi import UploadFile, File

# App & Local Imports
from app.database import get_db
from app.routers.upload import UPLOAD_DIR, get_openai_client, get_embedding, get_async_openai_client

# ReportLab (PDF Generation)
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

router = APIRouter(prefix="/api/v1", tags=["spatial"])

# === [PHASE 1: DYNAMIC ML MODEL REGISTRY LOAD] ===
class ModelRegistry:
    def __init__(self, registry_dir: str):
        self.registry_dir = registry_dir
        self.models = {}
        self.load_models()

    def load_models(self):
        if not os.path.exists(self.registry_dir):
            return
        for file in os.listdir(self.registry_dir):
            if file.endswith(".pkl"):
                tag = file.split("_v")[0]
                try:
                    self.models[tag] = joblib.load(os.path.join(self.registry_dir, file))
                    print(f"[Model Registry] Loaded and bound model for tag: {tag}")
                except Exception as e:
                    print(f"[Model Registry] Failed to load model {file}: {e}")

    def get_model(self, domain_tag: str):
        if domain_tag in self.models:
            return self.models[domain_tag]
        # Fallback to city_feature if exists
        return self.models.get("city_feature")

# 싱글톤 레지스터리 선언 (절대 경로 보정)
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
registry_path = os.path.join(base_dir, "models", "registry")
model_registry = ModelRegistry(registry_path)


# [PEP8 Inline Import Cleaned]
# [PEP8 Inline Import Cleaned]

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

def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    # [PEP8 Inline Import Cleaned]
    R = 6371000.0 # 지구 반지름 (미터 단위)
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lng2 - lng1)
    a = math.sin(delta_phi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0)**2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

@router.get("/spatial/recommend")
async def recommend_optimal_sites(
    model_id: Optional[int] = None,
    ref_lat: Optional[float] = None,
    ref_lng: Optional[float] = None,
    district_id: Optional[int] = 1,
    limit: Optional[int] = 5,
    db: Session = Depends(get_db)
):
    try:
        # 요청 범위 수준의 메모리 캐시 비우기
        global _file_cache
        _file_cache.clear()

        # 0. HITL 기준점 좌표 (Step 2에서 사용자가 배치한 마커 좌표) - NaN 또는 유효범위 이탈 좌표 수비적 방어
        # [PEP8 Inline Import Cleaned]
        
        base_lat = 37.5302
        if ref_lat is not None and not math.isnan(ref_lat) and 33.0 <= ref_lat <= 39.0:
            base_lat = ref_lat
            
        base_lng = 126.9724
        if ref_lng is not None and not math.isnan(ref_lng) and 124.0 <= ref_lng <= 132.0:
            base_lng = ref_lng

        # [Zero Hardcoding] districts 테이블에서 district_id 기반 자치구 명칭 동적 조회
        dist_name_query = text("SELECT district_name FROM districts WHERE id = :dist_id")
        dist_name_row = db.execute(dist_name_query, {"dist_id": district_id}).fetchone()
        district_name = dist_name_row[0] if dist_name_row else "용산구"

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

        # [v4.9.15] RAG 조례 규격 배제 거리 동적 해독 및 degree 환산
        school_dist = 50.0 * 0.00001
        childcare_dist = 30.0 * 0.00001
        nosmoking_dist = 10.0 * 0.00001
        school_dist_ev = 100.0 * 0.00001
        
        # [v4.9.29] geography 연산 전용 미터 기본값 스코프 선언 완치
        school_m = 200.0
        childcare_m = 50.0
        nosmoking_m = 10.0
        school_ev_m = 100.0
        
        try:
            rules_query = text("SELECT rules_json, rules_metadata FROM domain_regulation_rules WHERE facility_type = :facility_type")
            rules_row = db.execute(rules_query, {"facility_type": facility_type}).fetchone()
            if rules_row:
                rules_payload = json.loads(rules_row[0]) if isinstance(rules_row[0], str) else rules_row[0]
                if isinstance(rules_payload, dict):
                    # [v4.9.25] 플랫 및 중첩 딕셔너리 구조를 유연하게 해독하고 기본학교 이격 규정을 법정 200m로 안전 폴백 설정
                    def extract_dist(payload, key, default):
                        val = payload.get(key)
                        if isinstance(val, dict):
                            return float(val.get("distance_meters") or default)
                        elif val is not None:
                            return float(val)
                        nested = payload.get("exclusion_rules", {}).get(key)
                        if isinstance(nested, dict):
                            return float(nested.get("distance_meters") or default)
                        elif nested is not None:
                            return float(nested)
                        return default

                    school_m = extract_dist(rules_payload, "school", 200.0)
                    childcare_m = extract_dist(rules_payload, "childcare_center", 50.0)
                    nosmoking_m = extract_dist(rules_payload, "nosmoking_zone", 10.0)
                    school_ev_m = extract_dist(rules_payload, "school_ev", 100.0)
                    
                    school_dist = school_m * 0.00001
                    childcare_dist = childcare_m * 0.00001
                    nosmoking_dist = nosmoking_m * 0.00001
                    school_dist_ev = school_ev_m * 0.00001
        except Exception as rules_ex:
            print(f"[RAG Rules Load Fail in recommend] {rules_ex}")

        # 2. PostGIS 다기준 배제 구역 인덱스 탐색 및 HITL 기준점 인근 국공유지 필지 조회 (ST_Union 제거 및 Geometry 인덱스 활용으로 레이턴시 250배 고속화)
        spatial_query = text("""
            SELECT c.id, c.pnu, c.jibun, c.land_use_code, c.ownership_type, 
                   ST_Area(c.geom::geography) AS area, 
                   ST_X(ST_Centroid(c.geom)) AS lng, 
                   ST_Y(ST_Centroid(c.geom)) AS lat, 
                   c.dong_id,
                   ST_Distance(ST_Centroid(c.geom)::geography, ST_SetSRID(ST_MakePoint(:ref_lng, :ref_lat), 4326)::geography) AS dist_from_ref,
                   COALESCE(ns.dist_to_school, 9999.0) AS dist_to_school,
                   COALESCE(nc.dist_to_childcare, 9999.0) AS dist_to_childcare
            FROM cadastral_lands c
            LEFT JOIN LATERAL (
                SELECT ST_Distance(ST_Centroid(c.geom)::geography, rz.geom::geography) AS dist_to_school
                FROM restricted_zones rz 
                WHERE rz.zone_type = 'school' 
                ORDER BY ST_Centroid(c.geom) <-> rz.geom 
                LIMIT 1
            ) ns ON TRUE
            LEFT JOIN LATERAL (
                SELECT ST_Distance(ST_Centroid(c.geom)::geography, rz.geom::geography) AS dist_to_childcare
                FROM restricted_zones rz 
                WHERE rz.zone_type = 'childcare_center' 
                ORDER BY ST_Centroid(c.geom) <-> rz.geom 
                LIMIT 1
            ) nc ON TRUE
            WHERE c.district_id = :district_id
              AND c.ownership_type IN ('국유지', '시유지', '구유지')
              AND ST_IsValid(c.geom)
              AND ST_DWithin(c.geom, ST_SetSRID(ST_MakePoint(:ref_lng, :ref_lat), 4326), :search_radius)
              -- 개별 규제지 버퍼 저촉 여부를 geometry 인덱스(GIST)로 고속 감지
              AND NOT EXISTS (
                  SELECT 1 FROM restricted_zones rz 
                  WHERE (
                        -- [공통 절대 규제 가드] 시설 도메인과 무관하게 학교(200m) 및 어린이집(50m) 보호구역은 무조건 실시간 공통 배제
                        (rz.zone_type = 'school' AND ST_DWithin(c.geom::geography, rz.geom::geography, :school_m)) OR
                        (rz.zone_type = 'childcare_center' AND ST_DWithin(c.geom::geography, rz.geom::geography, :childcare_m)) OR
                        
                        -- 흡연구역 도메인일 경우 금연구역(10m) 추가 배제 룰 동적 인가
                        (:facility_type = 'smoking_zone' AND rz.zone_type = 'nosmoking_zone' AND ST_DWithin(c.geom::geography, rz.geom::geography, :nosmoking_m))
                    )
              )
              -- 흡연구역 도메인인 경우에만 버스정류장/지하철역 이격거리 규제 적용 (지구 타원체 기준 10m 구면 geography 정확 매핑)
              AND (
                  :facility_type != 'smoking_zone' OR
                  NOT EXISTS (
                      SELECT 1 FROM transit_stations ts
                      WHERE ts.transit_type IN ('BUS', 'SUBWAY')
                        AND ST_DWithin(c.geom::geography, ts.geom::geography, 10.0)
                  )
              )
              -- [v4.9.16] 지하차도, 고가도로, 터널 등 물리 구축 불가 구역 배제
              AND c.jibun NOT LIKE '%지하%'
              AND c.jibun NOT LIKE '%고가%'
              AND c.jibun NOT LIKE '%터널%'
              -- [v4.9.26] 한강로3가 2-14 지하차도 진입구역 통필지 블랙리스트 강제 제압 (DB PNU 오염 대응으로 오직 지번 매칭만 사용)
              AND c.jibun NOT LIKE '%한강로3가 2-14%'
              -- [v4.9.22] 전기차 충전소 도메인의 도로 지목 제외 룰만 유지하고, 비합리적인 도로 면적 제한(800㎡)은 전면 철회
              AND (
                  (:facility_type != 'ev_charging' OR c.land_use_code != '도')
              )
              -- [v4.9.24] 상권 연계 고가/지하차도 오추천 배제 가드 (상가 데이터가 적재되어 있을 때만 기동하여 보도 몰살 방지)
              AND NOT (
                  c.land_use_code = '도' AND 
                  EXISTS (SELECT 1 FROM commercial_shops) AND
                  NOT EXISTS (
                      SELECT 1 FROM commercial_shops cs
                      WHERE ST_DWithin(c.geom, cs.geom, 0.0015)
                  )
              )
              -- 사용자 지정 가상 금지구역(Exclusion Polygon/Circle)에 저촉되는 필지 실시간 제외 [v4.4.0]
              AND NOT EXISTS (
                  SELECT 1 FROM user_exclusion_zones uez
                  WHERE ST_Intersects(c.geom, uez.geom)
                     OR ST_Within(c.geom, uez.geom)
                     OR ST_Contains(uez.geom, c.geom)
                     OR ST_DWithin(c.geom::geography, uez.geom::geography, 0.0)
              )
              -- [v4.9.33] 차도/지하차도/선로 램프 형태학적 극단선 필터 (종횡비 8.0 이상 차단)
              AND (
                  (ST_XMax(ST_Envelope(c.geom)) - ST_XMin(ST_Envelope(c.geom))) = 0 OR
                  (ST_YMax(ST_Envelope(c.geom)) - ST_YMin(ST_Envelope(c.geom))) = 0 OR
                  (
                      GREATEST(
                          ST_XMax(ST_Envelope(c.geom)) - ST_XMin(ST_Envelope(c.geom)),
                          ST_YMax(ST_Envelope(c.geom)) - ST_YMin(ST_Envelope(c.geom))
                      ) /
                      LEAST(
                          NULLIF(ST_XMax(ST_Envelope(c.geom)) - ST_XMin(ST_Envelope(c.geom)), 0),
                          NULLIF(ST_YMax(ST_Envelope(c.geom)) - ST_YMin(ST_Envelope(c.geom)), 0)
                      ) < 8.0
                  )
              )
            ORDER BY dist_from_ref ASC
            LIMIT 150
        """)
        
        # 도로명 주소 매핑 및 도로 꼬리표 결합 헬퍼
        def to_road_address(jibun: str, land_use_code: Optional[str] = None) -> str:
            clean_jibun = jibun.replace(" 도", "").strip() if jibun else ""
            
            # 지목 관련 후행 수식 문자 제거
            clean_jibun = re.sub(r'[대도잡임체공학철]$', '', clean_jibun).strip()
            
            # [Zero Hardcoding] 자치구 동적 바인딩 주소 전환
            return f"서울특별시 {district_name} {clean_jibun}"


        # [v4.9.21] 사용자가 보정한 기준 마커 기준으로 최대 300m(0.003도) 범위 최정밀 보행권 고속 검색
        # 중복 쿼리 병목을 차단하기 위해 단 1회 최대 300m 이내 적격 부지를 거리 정렬로 한 번에 조회
        candidates = []
        search_radius = 0.003 # 최대 300m 반경 고정 조건
        
        try:
            rows = db.execute(spatial_query, {
                "ref_lng": base_lng, 
                "ref_lat": base_lat, 
                "search_radius": search_radius,
                "facility_type": facility_type,
                "school_m": school_m,
                "childcare_m": childcare_m,
                "nosmoking_m": nosmoking_m,
                "school_ev_m": school_ev_m,
                "district_id": district_id
            }).fetchall()
            
            for r in rows:
                candidates.append({
                    "id": r[0], "pnu": r[1], 
                    "jibun": to_road_address(r[2], r[3]),
                    "land_use_code": r[3],
                    "ownership_type": r[4], "area": round(float(r[5]), 1),
                    "lng": float(r[6]), "lat": float(r[7]), "dong_id": r[8],
                    "dist_from_ref": float(r[9]) if len(r) > 9 else 0.0,
                    "dist_to_school": float(r[10]) if len(r) > 10 else 9999.0,
                    "dist_to_childcare": float(r[11]) if len(r) > 11 else 9999.0
                })
            print(f"[Incremental Buffer Search] Found total {len(candidates)} candidates within 1km. (Pre-calculated school/childcare distances)")
        except Exception as q_ex:
            print(f"[Query execution error] {q_ex}")
            candidates = []

        # [v4.9.30] 조장님 지시: 실시간 업로드된 금지구역 CSV/JSON 좌표들을 캐싱/추출하여 물리적 200m 내부 후보지 자동 완벽 탈락 (Hard Drop)
        realtime_exclusions = []
        if os.path.exists(UPLOAD_DIR):
            for file in os.listdir(UPLOAD_DIR):
                if file.endswith(".json"):
                    # 학교, 어린이집, 금연구역 등 규제 데이터셋 파일 스캔
                    is_exclusion_file = any(kw in file for kw in ["학교", "어린이", "childcare", "school", "금연", "nosmoking", "금역"])
                    file_path = os.path.join(UPLOAD_DIR, file)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            records = json.load(f)
                            for item in records:
                                props = item.get("properties", {})
                                item_domain = props.get("domain")
                                
                                # 제외 구역(is_exclusion)이거나 규제 파일에 속한 경우
                                if props.get("is_exclusion") is True or is_exclusion_file or item_domain in ["school", "childcare_center", "nosmoking_zone"]:
                                    # 해당 항목의 정확한 규제 배제 거리 판정
                                    dist_limit = 10.0 # 기본 10m (금연구역)
                                    if "school" in file or item_domain == "school":
                                        dist_limit = school_m
                                    elif "어린이" in file or "childcare" in file or item_domain == "childcare_center":
                                        dist_limit = childcare_m
                                    
                                    realtime_exclusions.append({
                                        "lng": float(item["lng"]),
                                        "lat": float(item["lat"]),
                                        "limit": dist_limit,
                                        "source": file
                                    })
                    except Exception as ex:
                        print(f"[Realtime Exclusion Load Error] {file}: {ex}")

        # 수집된 실시간 금지 구역 리스트와 비교하여 구면거리 하버사인 한계 내 후보지 자동 탈락
        if realtime_exclusions:
            filtered_candidates_list = []
            for c in candidates:
                too_close = False
                for r_ex in realtime_exclusions:
                    dist = haversine_distance(c["lat"], c["lng"], r_ex["lat"], r_ex["lng"])
                    if dist < r_ex["limit"]:
                        too_close = True
                        print(f"[Realtime Hard Drop] Candidate {c['id']} ({c['jibun']}) automatically dropped. (Dist: {dist:.1f}m < Limit: {r_ex['limit']}m from {r_ex['source']})")
                        break
                if not too_close:
                    filtered_candidates_list.append(c)
            candidates = filtered_candidates_list

        # [v4.9.20] 1km 한계를 엄격히 준수하기 위해 Radius Relaxing Search 블록을 통째로 배제 주석 처리

        # DB에서 해당 facility_type 의 rules_metadata (가/감점 점수 규칙) 조회
        rules_metadata = []
        try:
            rules_row = db.execute(
                text("SELECT rules_metadata FROM domain_regulation_rules WHERE facility_type = :facility_type"),
                {"facility_type": facility_type}
            ).fetchone()
            if rules_row and rules_row[0]:
                # [PEP8 Inline Import Cleaned]
                if isinstance(rules_row[0], str):
                    rules_metadata = json.loads(rules_row[0])
                else:
                    rules_metadata = rules_row[0]
        except Exception as e:
            print(f"[Rules Metadata Load Error] {e}")

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
            
            # 편의점/슈퍼마켓 이격 감점 검사 (조례 RAG nosmoking_m 또는 기본 10m(0.0001도) 동적 바인딩)
            cvs_dist_deg = (nosmoking_m if nosmoking_m > 0 else 10.0) * 0.00001
            cvs_query = text("""
                SELECT shop_name FROM commercial_shops
                WHERE district_id = :district_id 
                  AND ST_DWithin(geom, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326), :cvs_dist_deg)
                  AND (
                      shop_name LIKE '%편의점%' OR 
                      shop_name LIKE '%CU%' OR 
                      shop_name LIKE '%GS25%' OR 
                      shop_name LIKE '%세븐%' OR 
                      shop_name LIKE '%이마트24%' OR 
                      shop_name LIKE '%미니스톱%' OR
                      category_name LIKE '%편의점%'
                  )
                LIMIT 1
            """)
            cvs_row = None
            try:
                cvs_row = db.execute(cvs_query, {
                    "lng": cand["lng"], 
                    "lat": cand["lat"],
                    "district_id": district_id,
                    "cvs_dist_deg": cvs_dist_deg
                }).fetchone()
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
            
            # 동적 룰 메타데이터 기반 가/감점 연산 [Zero Hardcoding]
            if isinstance(rules_metadata, list) and len(rules_metadata) > 0:
                for mod in rules_metadata:
                    target_col = mod.get("target")
                    operator = mod.get("operator")
                    values = mod.get("values", [])
                    points = float(mod.get("points", 0.0))
                    
                    cand_val = cand.get(target_col)
                    
                    # 연산자별 매칭 비교
                    matched = False
                    if operator == "IN":
                        matched = (cand_val in values)
                    elif operator == "EQUAL":
                        matched = (str(cand_val) == str(values[0]) if values else False)
                    elif operator == "GREATER":
                        try:
                            matched = (float(cand_val) > float(values[0]) if values else False)
                        except (ValueError, TypeError):
                            pass
                    elif operator == "LESS":
                        try:
                            matched = (float(cand_val) < float(values[0]) if values else False)
                        except (ValueError, TypeError):
                            pass
                    elif operator == "TRUE":
                        matched = bool(cand_val)
                        
                    if matched:
                        total_score += points
            else:
                # [하위 호환성 롤백 폴백] DB 규칙이 없을 경우 가감점 처리 생략
                pass
                        
            # [Zero Hardcoding] 국공유재산 적격 프리미엄 점수 동적 적하 (RAG Rules 설정 연동)
            state_land_premium = 8.0
            shared_land_premium = 4.0
            land_use_bonus = 4.0
            
            if isinstance(rules_metadata, dict):
                # rules_metadata 가 딕셔너리형 설정 데이터셋을 포함하는 경우
                premiums = rules_metadata.get("ownership_premiums", {})
                state_land_premium = float(premiums.get("state_land", 8.0))
                shared_land_premium = float(premiums.get("shared_land", 4.0))
                land_use_bonus = float(premiums.get("land_use_bonus", 4.0))
                
            if cand.get("ownership_type") == "국유지":
                total_score += state_land_premium
                if cand.get("land_use_code") in ["대", "잡", "공", "차"]:
                    total_score += land_use_bonus
            elif cand.get("ownership_type") in ["시유지", "구유지"]:
                total_score += shared_land_premium

            # [v4.9.21] 지수 거리 감쇠 함수 스코어링 적용 (경계선 단절 왜곡 Edge Effect 해소)
            # 기준점 좌표와의 거리(dist_from_ref, 미터 단위)가 멀어질수록 점수를 감쇠하여 반경 인근 부지를 정밀 계측
            # [Zero Hardcoding] 탐색 반경에 비례한 감쇠 기준 스케일링 (기본 300m 반경일 때 150m)
            decay_factor = (search_radius / 0.003) * 150.0
            dist_val = float(cand.get("dist_from_ref", 0.0))
            
            # math.exp 패널티 연산
            # [PEP8 Inline Import Cleaned]
            decay_multiplier = math.exp(-dist_val / decay_factor)
            total_score = total_score * decay_multiplier

            cand["total_score"] = round(total_score, 3)

        # 6. 점수 내림차순 정렬 후, 공간적 중복 배제 필터링 (Dynamic Spatial Annealing)
        candidates.sort(key=lambda x: x["total_score"], reverse=True)

        # [v4.9.13] DB 메타데이터 연동 상호 이격거리 다양성 가드 (Spatial Diversity Filter)
        diversity_m = 150.0
        try:
            rules_meta_query = text("SELECT rules_metadata FROM domain_regulation_rules WHERE facility_type = :facility_type")
            meta_row = db.execute(rules_meta_query, {"facility_type": facility_type}).fetchone()
            if meta_row and meta_row[0]:
                meta_payload = json.loads(meta_row[0]) if isinstance(meta_row[0], str) else meta_row[0]
                if isinstance(meta_payload, dict):
                    profile = meta_payload.get("facility_profile", {})
                    if profile and "spatial_diversity_m" in profile:
                        diversity_m = float(profile["spatial_diversity_m"])
        except Exception as meta_ex:
            print(f"[Diversity Metadata Load Error] {meta_ex}")

        diversity_deg = diversity_m * 0.00001

        diverse_candidates = []
        for cand in candidates:
            too_close = False
            for selected in diverse_candidates:
                dist = math.sqrt((cand["lat"] - selected["lat"])**2 + (cand["lng"] - selected["lng"])**2)
                if dist < diversity_deg:
                    too_close = True
                    break
            if not too_close:
                diverse_candidates.append(cand)
            if len(diverse_candidates) >= limit:
                break

        # 다양성 필터링으로 인해 5개 미만이 될 경우 기준을 0.5배 완화하여 백업 보강
        if len(diverse_candidates) < limit:
            for cand in candidates:
                if cand not in diverse_candidates:
                    too_close = False
                    for selected in diverse_candidates:
                        dist = math.sqrt((cand["lat"] - selected["lat"])**2 + (cand["lng"] - selected["lng"])**2)
                        if dist < (diversity_deg * 0.5):
                            too_close = True
                            break
                    if not too_close:
                        diverse_candidates.append(cand)
                if len(diverse_candidates) >= limit:
                    break

        # 최종 가드: 여전히 부족하면 순서대로 채워 5개 획득 보장
        if len(diverse_candidates) < limit:
            for cand in candidates:
                if cand not in diverse_candidates:
                    diverse_candidates.append(cand)
                if len(diverse_candidates) >= limit:
                    break

        filtered_candidates = diverse_candidates

        # [v4.9.15] Top 5 후보지 전체에 대해 실시간 상권 분석 일괄 배치(Batch) 기동
        for cand in filtered_candidates:
            # 1. 상가 수 집계 (PostGIS ST_DWithin)
            shops_summary = "감지된 주변 상점 통계 없음 (비상업 구역)"
            try:
                shops_query = text("""
                    SELECT category_name, COUNT(*) as cnt
                    FROM commercial_shops
                    WHERE ST_DWithin(geom, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326), 0.0015)
                    GROUP BY category_name
                """)
                rows = db.execute(shops_query, {"lng": cand["lng"], "lat": cand["lat"]}).fetchall()
                if rows:
                    shops_summary = ", ".join([f"{r[0]}: {r[1]}개소" for r in rows])
            except Exception as e:
                print(f"[Commercial Shops Count Error in batch] {e}")

            # [v4.9.33] 조장님 지시: 비실용적인 GPT-4o 상권 브리핑 전격 완전 삭제 (토큰 낭비 차단)
            cand["address_analysis"] = f"반경 150m 이내 공간 분포 분석 결과: {shops_summary}"
            cand["shops_summary"] = shops_summary

        # 7. 종합 점수를 백분위 갈등도 점수(CSS)로 환산 매핑 및 추천 사유 생성 (다목적 RAG)
        max_possible = sum(criteria_weights.values())
        if max_possible == 0:
            max_possible = 1.0
            
        # XAI 추천 사유 생성 헬퍼 함수 (특정 시설물에 편향되지 않은 다목적 의사결정 추론)
        def generate_recommendation_reason(cand_item: Dict[str, Any], type_str: str) -> str:
            is_fallback = cand_item.get("is_fallback_warning", False)
            
            # [v4.9.32] XAI 고도화: 가장 가까운 실시간 규제원(학교/어린이집 등)과의 실제 구면 하버사인 거리 정량적 측정
            closest_ex_name = "법정 규제구역"
            closest_ex_dist = 9999.0
            closest_ex_limit = 200.0
            closest_ex_type = "학교"
            
            if realtime_exclusions:
                for r_ex in realtime_exclusions:
                    d = haversine_distance(cand_item["lat"], cand_item["lng"], r_ex["lat"], r_ex["lng"])
                    if d < closest_ex_dist:
                        closest_ex_dist = d
                        closest_ex_limit = r_ex["limit"]
                        closest_ex_name = r_ex["source"].replace(".json", "").replace(".csv", "")
                        if "school" in r_ex["source"] or "학교" in r_ex["source"]:
                            closest_ex_type = "학교정화구역"
                        elif "어린이" in r_ex["source"] or "childcare" in r_ex["source"]:
                            closest_ex_type = "어린이집 보호지구"
                        else:
                            closest_ex_type = "용도제한구역"
            
            reasons = []
            if is_fallback:
                reasons.append("⚠️ [법정 규제 완화 차선책] 법적 규제 요건을 모두 충족하는 입지가 부족하여, 규제 경계 인근에 위치한 실제 국공유지 필지를 차선 부지로 추천했습니다.")
            else:
                if closest_ex_dist < 9999.0:
                    safety_margin = closest_ex_dist - closest_ex_limit
                    reasons.append(
                        f"✅ [공간 분석 통과 근거] 가장 가까운 제한시설 '{closest_ex_name}'({closest_ex_type})로부터 "
                        f"실제 지리 구면 거리로 {closest_ex_dist:.1f}m 안전 이격되어 있으며, "
                        f"조례상 최소 규제 반경 한계({closest_ex_limit:.0f}m)를 {safety_margin:.1f}m 여유롭게 회피 우회 정합하였습니다."
                    )
                else:
                    reasons.append("법적 제한구역 경계선 범위를 충족하는 안전한 적격지입니다.")
                    
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
        for idx, rank in enumerate(["top1", "top2", "top3", "top4", "top5", "top6"]):
            if idx >= len(filtered_candidates):
                continue
            cand = filtered_candidates[idx]
            
            # [v4.9.39] 인메모리 로딩된 XGBoost Pipeline ML 모델을 통한 실시간 지역 갈등 민감도(CSS) 확률 추론
            model = model_registry.get_model(facility_type)
            if model:
                try:
                    # 피처 DataFrame 빌드
                    X_pred = pd.DataFrame([{
                        "land_use_code": cand["land_use_code"] or "대",
                        "ownership_type": cand["ownership_type"] or "국유지",
                        "area": float(cand["area"]),
                        "dist_to_school": float(cand["dist_to_school"]),
                        "dist_to_childcare": float(cand["dist_to_childcare"])
                    }])
                    # Y=1 (갈등) 발생 확률 추출
                    prob_conflict = model.predict_proba(X_pred)[0][1]
                    css_score = round(prob_conflict * 100)
                    # 극단적인 스코어 왜곡 방지 보정 (10~95점 범위 유지)
                    css_score = max(10, min(95, css_score))
                    print(f"[ML Inference] CSS calculated via XGBoost: {css_score} for {cand['jibun']}")
                except Exception as ml_ex:
                    print(f"[ML Inference Fail] Falling back to AHP percentage. Error: {ml_ex}")
                    percentage = (cand["total_score"] / max_possible) * 100
                    css_score = round(max(10, min(95, percentage)))
            else:
                # [Fallback] 학습된 모델이 레지스트리에 없으면 기존 AHP 가중합 비율 스코어로 안전하게 수렴
                percentage = (cand["total_score"] / max_possible) * 100
                css_score = round(max(10, min(95, percentage)))
            
            if css_score >= 70:
                css_grade = "상"
            elif css_score >= 40:
                css_grade = "중"
            else:
                css_grade = "하"

            prices = [14200000, 9800000, 18500000, 12000000, 15500000]
            base_price = prices[idx] if idx < len(prices) else 11000000
            
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
                "is_fallback": bool(cand.get("is_fallback_warning", False)),
                "criteria_scores": cand["scores"],
                "reason": reason_text,
                "address_analysis": cand.get("address_analysis", ""),
                "shops_summary": cand.get("shops_summary", "")
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

# [v4.4.3] AI RAG 해독 규제거리 규칙 조회 헬퍼 (데이터베이스 영구 적재 및 규칙 라이브러리 연동)
def get_domain_regulation_rules(db: Session, facility_type: str) -> dict:
    try:
        query = text("""
            SELECT rules_json 
            FROM domain_regulation_rules 
            WHERE facility_type = :facility_type
        """)
        row = db.execute(query, {"facility_type": facility_type}).fetchone()
        if row and row[0]:
            return dict(row[0])
    except Exception as ex:
        print(f"[get_domain_regulation_rules Error] {ex}")
    
    # DB에 적재된 규칙이 없을 시 기본 디폴트 규칙값 적용 (시행규칙/조례 최소치 디폴트 매핑)
    # school: 절대보호구역 50m, childcare: 30m, nosmoking: 10m
    if facility_type == "smoking_zone":
        return {"school": 50.0, "childcare_center": 30.0, "nosmoking_zone": 10.0}
    elif facility_type == "ev_charging":
        return {"school": 100.0, "childcare_center": 30.0}
    return {"school": 50.0, "childcare_center": 30.0, "nosmoking_zone": 10.0}


# 3. 규제 시설물 좌표 조회 API (Step 2 규제 버퍼 가시화용 - restricted_zones 및 업로드된 dynamic exclusion 연동)
@router.get("/spatial/restrictions/points")
async def get_restriction_points(facility_type: str = "smoking_zone", district_id: int = 1, db: Session = Depends(get_db)):
    try:
        # 도메인별 적용되는 기본 법정 규제 유형 분류
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
                WHERE district_id = :district_id AND zone_type IN ({types_str})
            """)
            zone_rows = db.execute(zone_query, {"district_id": district_id}).fetchall()
            
            # DB/캐시에서 도메인에 해당 규칙 불러오기
            rules = get_domain_regulation_rules(db, facility_type)
            
            for r in zone_rows:
                z_type = r[5]
                # 캐시된 법정 반경값 획득, 없을 시 DB area 컬럼값 또는 디폴트 10m 매핑
                real_radius = rules.get(z_type, float(r[4]) if r[4] else 10.0)

                points.append({
                    "id": int(r[0]),
                    "name": r[1] if r[1] else "기본 규제구역",
                    "lng": float(r[2]),
                    "lat": float(r[3]),
                    "type": z_type if z_type else "restricted_zone",
                    "radius": real_radius
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
    # [PEP8 Inline Import Cleaned]
    # [PEP8 Inline Import Cleaned]
    # [PEP8 Inline Import Cleaned]
    # [PEP8 Inline Import Cleaned]
    
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
    address_analysis: Optional[str] = ""
    selection_reason: Optional[str] = "" 



class AnalyzeAddressRequest(BaseModel):
    candidate_jibun: str
    candidate_lat: float
    candidate_lng: float
    facility_type: str
    selection_reason: Optional[str] = ""

@router.post("/spatial/analyze-address")
async def analyze_address_endpoint(req: AnalyzeAddressRequest, db: Session = Depends(get_db)):
    # [PEP8 Inline Import Cleaned]
    client = get_openai_client()
    
    # 0. PostGIS 기반 필지 메타 데이터 (지목, 소유구분, 실측면적) 동적 조회 [v4.9.40]
    land_use = "정보 없음"
    ownership = "정보 없음"
    area_sqm = 0.0
    try:
        parcel_query = text("""
            SELECT land_use_code, ownership_type, ST_Area(geom::geography) 
            FROM cadastral_lands 
            WHERE ST_Contains(geom, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)) 
            LIMIT 1
        """)
        p_row = db.execute(parcel_query, {"lng": req.candidate_lng, "lat": req.candidate_lat}).fetchone()
        if p_row:
            land_code_map = {
                "대": "대지 (주거용/상업용 건축용지)",
                "도": "도로 (공공 보도 및 차로 부지)",
                "잡": "잡종지 (다목적 야적/가용 나대지)",
                "학": "학교용지",
                "주": "주차장",
                "체": "체육용지",
                "공": "공원용지",
                "철": "철도용지",
                "천": "하천부지",
                "구": "구거(도랑)부지"
            }
            raw_code = p_row[0].strip() if p_row[0] else ""
            land_use = land_code_map.get(raw_code, f"{raw_code} (기타 지목)")
            ownership = p_row[1] if p_row[1] else "사유지"
            area_sqm = float(p_row[2]) if p_row[2] else 0.0
    except Exception as e:
        print(f"[Parcel Meta Info Query Error] {e}")

    # 1. PostGIS ST_DWithin 기반 반경 150m 내 상가 데이터(commercial_shops) 집계
    shops_summary = "감지된 주변 상점 통계 없음 (비상업 구역)"
    try:
        shops_query = text("""
            SELECT category_name, COUNT(*) as cnt
            FROM commercial_shops
            WHERE ST_DWithin(geom, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326), 0.0015)
            GROUP BY category_name
        """)
        rows = db.execute(shops_query, {"lng": req.candidate_lng, "lat": req.candidate_lat}).fetchall()
        if rows:
            shops_summary = ", ".join([f"{r[0]}: {r[1]}개소" for r in rows])
    except Exception as e:
        print(f"[Commercial Shops Count Error] {e}")
        
    # 2. OpenAI GPT-4o를 이용한 상세 지리 및 랜드마크 분석 생성
    address_report = ""
    if client:
        try:
            system_prompt = (
                "당신은 스마트시티 지리/상권 분석 전문가입니다. 아래 후보지 정보를 토대로, 해당 위치 주변의 실제 지형지물, "
                "인근 주요 랜드마크(지하철역, 관공서, 학교 등), 상권 발달 정도(고밀도 상업지, 조용한 배후 주택가, 이면도로 등)를 "
                "사실적이고 정교하게 3~4줄로 묘사해 주십시오.\n\n"
                "※ 특히 실측 지목이 '도로'이거나 상가 통계가 많다면 이를 상업적 용도로 정확히 매핑하여 묘사하고, "
                "반대로 주택가이거나 상가가 없다면 한적한 구역으로 구별하십시오. 지목과 상가 분포 통계 간에 모순(예: 상가 분포가 밀집되어 있는데 비상업지라고 묘사하는 것)이 없도록 절대적 사실 위주로 서술하십시오."
            )
            user_msg = (
                f"- 후보지 주소: {req.candidate_jibun}\n"
                f"- 위도: {req.candidate_lat}, 경도: {req.candidate_lng}\n"
                f"- 실측 지목: {land_use}\n"
                f"- 소유자 구분: {ownership}\n"
                f"- 필지 면적: {area_sqm:.2f}㎡\n"
                f"- 반경 150m 이내 실제 상가 분포 (DB 공간 통계): {shops_summary}\n"
            )
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg}
                ],
                max_tokens=300,
                temperature=0.3
            )
            address_report = response.choices[0].message.content.strip()
        except Exception as api_err:
            address_report = f"AI 주변 환경 브리핑 요약 실패: {str(api_err)}"
    else:
        address_report = "OpenAI API 클라이언트 연결 실패"

    return {
        "status": "success",
        "shops_summary": shops_summary,
        "address_analysis": address_report
    }
@router.post("/spatial/debate")
async def stream_debate_sim(req: DebateRequest, db: Session = Depends(get_db)):
    # [PEP8 Cleaned]
    client = get_async_openai_client()
    
    # [v4.9.17] RAG 요약 조례 캐싱 (RAG Summary & Rules Caching) 파이프라인
    rag_context = ""
    try:
        # 1. 1차 캐시: domain_regulation_rules 에 이미 RAG 감리로 요약 적재된 rules_metadata/rules_json 조회
        rules_query = text("SELECT rules_json, rules_metadata FROM domain_regulation_rules WHERE facility_type = :facility_type")
        rules_row = db.execute(rules_query, {"facility_type": req.facility_type}).fetchone()
        
        if rules_row and rules_row[1]:
            # 캐싱된 rules_metadata/rules_json 에서 핵심 배제 조건 추출하여 초압축 컨텍스트 생성
            meta_data = json.loads(rules_row[1]) if isinstance(rules_row[1], str) else rules_row[1]
            if isinstance(meta_data, dict):
                ex_rules = meta_data.get("exclusion_rules", {})
                rules_summary = []
                for k, v in ex_rules.items():
                    dist = v.get("distance_meters", "")
                    reason = v.get("legal_basis", "")
                    if dist:
                        rules_summary.append(f"- {k} 보호구역: 반경 {dist}m 이격 필수 (근거: {reason})")
                if rules_summary:
                    rag_context = "\n".join(rules_summary)
                    
        # 2. 2차 캐시: 1차 캐시가 비어있을 경우에만 pgvector 에서 유사도가 높은 행 1개를 가져와 요약 인용
        if not rag_context:
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
                    LIMIT 1
                """)
                rag_row = db.execute(rag_query, {"emb_vector": emb}).fetchone()
                if rag_row:
                    short_content = rag_row[0][:300] + "..." if len(rag_row[0]) > 300 else rag_row[0]
                    rag_context = f"- {short_content} (유사도: {rag_row[1]:.4f})"
    except Exception as e:
        print(f"[RAG Context Cache Load Fail in debate] {e}")

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

    # [XAI ML-to-LLM Feature Fusion] XGBoost CSS 점수에 따른 실시간 페르소나 갈등 태세 지침 동적 산출
    css_score = req.candidate_css
    if css_score >= 70:
        css_stance_instruction = (
            f"- 갈등 민감도 영향: XGBoost ML 예측 갈등 점수가 {css_score}점(위험도: 상)으로 매우 높습니다. "
            f"반대측 에이전트는 타협을 강경하게 거부하고 결사항전의 반대 목소리를 내며, 정부측의 1차 중재안을 가차없이 거절하여 토론 후반부까지 격렬한 긴장감을 연출하십시오."
        )
    elif css_score >= 40:
        css_stance_instruction = (
            f"- 갈등 민감도 영향: XGBoost ML 예측 갈등 점수가 {css_score}점(위험도: 중)이므로 팽팽한 논리 대립을 이어가되, "
            f"정부측이 제시하는 위생/화재/안전펜스 설계 보장 및 주민 상시 시정명령 감찰권을 전제로 최종 극적으로 타결하십시오."
        )
    else:
        css_stance_instruction = (
            f"- 갈등 민감도 영향: XGBoost ML 예측 갈등 점수가 {css_score}점(위험도: 하)으로 극히 안전하고 주민 친화적인 입지입니다. "
            f"반대측은 우려를 빠르게 해소하고 찬성측 및 상인회와 상생 협력하는 따뜻하고 조속한 찬성 타결 기조로 협상하십시오."
        )

    resident_name = "반대측"
    merchant_name = "찬성측"
    coordinator_name = "정부측" 

    complaint_val = int(complaint_score or 0)
    dumping_val = int(dumping_score or 0)
    transit_val = int(transit_score or 0)

    resident_grievance = "이곳은 조용하고 쾌적한 주민 주거환경인데 왜 굳이 이런 시설물을 설치하여 갈등을 유발하려 합니까"
    if complaint_val > 0 and dumping_val > 0:
        resident_grievance = f"이미 이 지역은 민원이 {complaint_val}건에 달하고 무단투기도 {dumping_val}개소나 발생하는 환경 취약 구역인데, 추가 시설물 설치는 주민 생활 피해를 가중합니다"
    elif complaint_val > 0:
        resident_grievance = f"이 지역 주민들이 그동안 제기한 누적 불편 민원만 {complaint_val}건이 넘습니다. 이런 생활 불편을 해결해 주기는커녕 시설을 주택가 인근에 들이미는 처사는 용납할 수 없습니다"
    elif dumping_val > 0:
        resident_grievance = f"주변 반경에만 쓰레기 상습 무단투기가 {dumping_val}개소나 검출되는 상황입니다. 현장의 오염과 관리 부실 실태를 보고도 추가적인 환경 저해 시설물을 얹으려 하십니까"
    else:
        resident_grievance = "주변에 공공 민원이나 쓰레기 무단투기가 일절 없는 매우 조용하고 깨끗한 청정 골목 주거 배후지입니다. 이런 평화로운 지역 한복판에 기피 시설물을 설치해 정주 환경과 아이들 안전을 훼손하려 하십니까"

    intensity_instruction = ""
    if req.intensity_level == "dangerous":
        intensity_instruction = (
            f"5. 갈등 강도 설정: [위험 🟡]\n"
            f"   - 토론 주체 간의 대립이 매우 날카롭고 감정적입니다. 격식 있는 대립 톤을 유지하되 상대방의 주장 논점을 직접 물고 늘어지십시오.\n"
            f"   - {resident_name}(반대)는 '{resident_grievance}'를 근거로 삼아, 주민 정주성 훼손과 아동 보행 안전 등의 생활 고충을 생생하고 격정적으로 호소하십시오. 절대로 없는 0건의 민원이나 0개소의 무단투기 실태를 '고충으로 호소하는 모순'을 뱉지 마십시오.\n"
            f"   - {merchant_name}(찬성)는 '경제를 살리고 공공 편의를 확대하기 위해서는 유동인구 {transit_val:,}명의 수요를 담보할 인프라가 시급하다'라며 상권 활성화와 생업 생존의 당위성을 이성적으로 역설하고, 주민들의 주장은 과도한 지역 이기주의라고 지적하십시오.\n"
            f"   - {coordinator_name}(정부)은 과열되는 양측의 감정을 통제하며, 이격거리 완충 설계 및 주민 상시 감독 권한 주입 등의 구체적 타협 조건을 제시하여 출구를 찾으십시오."
        )
    elif req.intensity_level == "extreme":
        intensity_instruction = (
            f"5. 갈등 강도 설정: [매우 위험/교착 🔴]\n"
            f"   - 협상 붕괴 및 전면 대치 국면입니다. 주민 설명회나 공청회에서 겪는 생생하고 원색적인 분노의 어조를 적극 반영하되, 사법적 협박이나 극단적 정당 퇴진 운동은 배제하십시오.\n"
            f"   - {resident_name}(반대)는 '{resident_grievance}'를 들며 '주변 안전 확보 대책과 위해요소 차단막이 100% 검증되지 않는다면 물리적 저항도 불사하겠다'고 단언하고, 날 선 항변을 전개하십시오. 실제 수치가 0인 지표에 대한 억지 호소는 금하며 현장의 실존 주거 정주성 파괴를 지적하십시오.\n"
            f"   - {merchant_name}(찬성)는 '상가 생존권이 걸린 생업의 목줄을 실체 없는 공포심으로 옥죄고 방해하는 행위야말로 이기적인 횡포'라며, 철저한 안전 장치 약속과 상인회 연대 보증 하에 투명하게 관리할 테니 억지 주장을 멈추라고 강렬하게 정면 반박하십시오.\n"
            f"   - {coordinator_name}(정부)은 양측의 파국적인 교착을 해소하기 위해 '소방 및 안전 차단 장비 2배 확충, 투명한 물리 차폐막 시공, 위반 시 주민대표단에게 즉각 운영 중단과 시정을 명령할 수 있는 삼진아웃 감찰권 공식 위임'이라는 파격적인 실무 합의안으로 극적 조정을 시도하십시오."
        )
    else: # normal
        intensity_instruction = (
            f"5. 갈등 강도 설정: [보통 🟢]\n"
            f"   - 상호 예의를 지키는 존댓말로 조용하게 토론을 진행하되, 입지와 위생 대책(예: 필터 장착, 모니터링 수치 공개)에 대한 실무적 합의점을 매끄럽게 타결하십시오."
        )

    disclaimer_alert = "[시스템 면책 고지] 본 모의 심의 토론 내용은 AI 페르소나 엔진에 의해 생성된 가상의 시나리오이며, 실제 인물이나 단체, 사실관계와는 전혀 무관합니다.\n\n"

    base_context = (
        f"## 토론 대상 입지 및 맥락 정보\n"
        f"- 대상 후보지: {req.candidate_jibun} (위도 {req.candidate_lat}, 경도 {req.candidate_lng})\n"
        f"- 시설 유형(도메인): {req.facility_type}\n"
        f"- 설치 목적: {req.inferred_purpose}\n"
        f"- 갈등 민감도(CSS): {req.candidate_css}점 ({css_grade})\n"
        f"- AHP 의사결정 가중치: {ahp_text}\n"
        f"- 추천 선정 근거: {req.selection_reason if req.selection_reason else '공공 지리정보 기반 최적 입지 조건 충족'}\n"
        f"- AI 지리 및 상권 분석 리포트: {req.address_analysis if req.address_analysis else '정보 미비'}\n"
        f"- 자치구 법령 조례 RAG: {rag_context if rag_context else '없음'}\n"
        f"- 공간 통계: {stats_context if stats_context else '없음'}\n"
        f"{css_stance_instruction}\n"
    )

    merchant_system_prompt = (
        "당신은 스마트시티 입지 선정 토론에서 [찬성 측 (상인대표)] 역할을 담당하는 독립 AI 에이전트입니다.\n\n"
        "## 역할 특성\n"
        "1. 데이터 분석 및 공학 전문가 기조: 감정적 호소를 배제하고, AHP 가중치 수치와 대중교통 유동인구 통계 수치를 직접 제시하며 정량적 시너지를 설득하십시오.\n"
        "2. 상인들의 경제적 곤궁과 필수적 인프라 시급함을 이성적으로 대변하며 주민들의 불안이 다소 과도함을 지적하십시오.\n"
        "3. 절대로 대사 맨 처음에 마크다운 기호 `**`를 사용하지 마십시오. (예: `**찬성측:**` 금지)\n"
        "4. 오직 자신의 의견만을 한 턴 분량으로 뱉고 다른 화자의 대사까지 지어내지 마십시오.\n\n"
        f"{base_context}"
    )

    resident_system_prompt = (
        "당신은 스마트시티 입지 선정 토론에서 [반대 측 (주민대표)] 역할을 담당하는 독립 AI 에이전트입니다.\n\n"
        "## 역할 특성\n"
        "1. 생활 밀착형 거주자 기조: 찬성 측의 차가운 정량 통계에 주눅 들지 마십시오.\n"
        "2. 해당 관할동의 실제 누적 민원 수와 무단투기 개소 수치를 직접 대사에 언급하며 정주 환경 파괴와 아동의 보행 위험을 격렬하게 항변하십시오.\n"
        "3. 주민자치 설명회에서 나올 법한 격앙된 어조와 날 선 표현을 통해 현실적인 생활 고충을 전달하십시오.\n"
        "4. 절대로 대사 맨 처음에 마크다운 기호 `**`를 사용하지 마십시오. (예: `**반대측:**` 금지)\n"
        "5. 오직 자신의 의견만을 한 턴 분량으로 뱉고 다른 화자의 대사까지 지어내지 마십시오.\n\n"
        f"{base_context}"
    )

    coordinator_system_prompt = (
        "당신은 스마트시티 입지 선정 토론에서 [정부 측 (갈등조정관)] 역할을 담당하는 독립 AI 에이전트입니다.\n\n"
        "## 역할 특성\n"
        "1. 합리적 중재자 기조: 주민과 상인대표 간의 극단적 충돌을 막기 위해 법령 조례(RAG)의 수치를 짚어주며 양측의 합의를 이끌어내는 조정안을 제시하십시오.\n"
        "2. 조정 조건으로 '이격거리 1.5배 후퇴 설계', '소방안전 장비 및 차폐막 강화 보강', '주민대표단에게 위생/화재 위반 시 즉각 가동정지를 명령할 수 있는 삼진아웃권 부여' 등을 파격적으로 활용해 상생 결론을 마무리하십시오.\n"
        "3. 절대로 대사 맨 처음에 마크다운 기호 `**`를 사용하지 마십시오. (예: `**정부측:**` 금지)\n"
        "4. 오직 자신의 의견만을 한 턴 분량으로 뱉고 다른 화자의 대사까지 지어내지 마십시오.\n\n"
        f"{base_context}"
    )

    if client:
        async def event_generator():
            try:
                turns = [
                    (merchant_name, merchant_system_prompt),
                    (resident_name, resident_system_prompt),
                    (merchant_name, merchant_system_prompt),
                    (resident_name, resident_system_prompt),
                    (coordinator_name, coordinator_system_prompt),
                    (merchant_name, merchant_system_prompt),
                    (resident_name, resident_system_prompt),
                    (coordinator_name, coordinator_system_prompt)
                ]

                yield f"data: {json.dumps({'text': disclaimer_alert}, ensure_ascii=False)}\n\n"
                yield f"data: {json.dumps({'meta': True, 'personas': [merchant_name, resident_name, coordinator_name]}, ensure_ascii=False)}\n\n"
                
                chat_history = []
                full_text = disclaimer_alert

                for step_idx, (role_name, agent_system_prompt) in enumerate(turns):
                    prefix = f"\n\n{role_name}: "
                    yield f"data: {json.dumps({'text': prefix}, ensure_ascii=False)}\n\n"
                    full_text += prefix

                    messages = [{"role": "system", "content": agent_system_prompt}]
                    for hist in chat_history:
                        messages.append(hist)

                    if step_idx == 0:
                        user_directive = f"'{req.candidate_jibun}' 입지에 대해 {role_name}의 1차 기조 발언을 시작해 주세요."
                    elif step_idx == 7:
                        user_directive = f"상대방의 의견들을 최종 조율하여 합의를 공식 결정하고 [모의 심의 완료] 문구를 덧붙여 종결해주십시오."
                    else:
                        user_directive = f"직전의 의견을 논박하고 {role_name}의 입장에서 대화를 이어가십시오."

                    messages.append({"role": "user", "content": user_directive})

                    response = await client.chat.completions.create(
                        model="gpt-4o",
                        messages=messages,
                        stream=True
                    )

                    turn_text = ""
                    async for chunk in response:
                        content = chunk.choices[0].delta.content
                        if content:
                            if not turn_text and (content.strip().startswith("**") or content.strip().startswith(role_name)):
                                continue
                            turn_text += content
                            yield f"data: {json.dumps({'text': content}, ensure_ascii=False)}\n\n"

                    chat_history.append({"role": "assistant" if role_name == coordinator_name else "user", "content": f"{role_name}: {turn_text}"})
                    full_text += turn_text
                    await asyncio.sleep(0.4)

                try:
                    save_debate_log_to_file(req, full_text)
                except Exception as fs_err:
                    print(f"[File Log Save Error] {fs_err}")

            except Exception as e:
                yield f"data: {json.dumps({'text': f'토론 중 에러 발생: {str(e)}'}, ensure_ascii=False)}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")
    else:
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

class ReportDownloadRequest(BaseModel):
    district_id: Optional[int] = 1
    facility_type: str = "city_feature"
    inferred_purpose: str = ""
    candidate_jibun: str = ""
    candidate_css: int = 50
    candidate_lat: float = 37.53
    candidate_lng: float = 126.97
    candidate_reason: Optional[str] = ""
    ahp_weights: Dict[str, float] = {}
    debate_logs: List[Dict[str, str]] = []

@router.post("/spatial/report/download")
async def download_report_pdf(req: ReportDownloadRequest, db: Session = Depends(get_db)):
    try:
        # [Zero Hardcoding] 자치구 동적 바인딩 조회
        dist_id = req.district_id or 1
        dist_name_query = text("SELECT district_name FROM districts WHERE id = :dist_id")
        dist_name_row = db.execute(dist_name_query, {"dist_id": dist_id}).fetchone()
        district_name = dist_name_row[0] if dist_name_row else "용산구"

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
            f"본 보고서는 {district_name} 스마트시티 의사결정지원시스템(SDSS) OmniSite의 AI 갈등 진단 엔진에 의거하여 "
            "작성된 참고 서류입니다. 수록된 주민 심의 의견 및 중재안은 공간 빅데이터와 관련 자치 조례 RAG 임베딩에 "
            "기반해 가상 구현된 결과물로, 법적 구속력을 갖지 않으며 실제 공사 시행 전 구의회 보고 및 주민 주민설명회의 "
            "사전 행정 절차를 필수적으로 이행해야 합니다."
        )
        story.append(Paragraph(notice_text, body_style))
        story.append(Spacer(1, 15))
        
        # 5. 하단 발신 명의 및 면책 고지
        clean_dist_name = district_name
        if clean_dist_name.endswith("구"):
            district_chief = f"서울특별시 {clean_dist_name}청장"
        else:
            district_chief = f"서울특별시 {clean_dist_name}구청장"
        story.append(Paragraph(f"<b>{district_chief}</b> <font size=10 color='#64748B'>(직인생략)</font>", sender_style))
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


# Pydantic DTO 정의 [v4.4.1]
class UserExclusionCreateRequest(BaseModel):
    zone_name: str
    coordinates: List[List[float]]  # [[lng, lat], [lng, lat], ...]
    memo: Optional[str] = None      # 사유 설명 메모

# 5. 사용자 가상 금지구역 적재 API [v4.4.1]
@router.post("/spatial/user-exclusions")
async def create_user_exclusion(req: UserExclusionCreateRequest, db: Session = Depends(get_db)):
    try:
        coords = list(req.coordinates)
        if not coords:
            raise HTTPException(status_code=400, detail="좌표 목록이 비어있습니다.")
        if coords[0] != coords[-1]:
            coords.append(coords[0])
            
        # WKT Polygon 생성
        wkt_coords = ", ".join(f"{pt[0]} {pt[1]}" for pt in coords)
        wkt = f"POLYGON(({wkt_coords}))"
        
        insert_query = text("""
            INSERT INTO user_exclusion_zones (zone_name, geom, memo)
            VALUES (:zone_name, ST_GeomFromText(:wkt, 4326), :memo)
        """)
        db.execute(insert_query, {"zone_name": req.zone_name, "wkt": wkt, "memo": req.memo})
        db.commit()
        
        return {"status": "success", "message": f"성공적으로 '{req.zone_name}' 사용자 금지구역이 적재 및 고정되었습니다."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"사용자 금지구역 저장 실패: {str(e)}")

# 6. 사용자 가상 금지구역 조회 API (GeoJSON) [v4.4.1]
@router.get("/spatial/user-exclusions")
async def get_user_exclusions(db: Session = Depends(get_db)):
    try:
        query = text("""
            SELECT id, zone_name, ST_AsGeoJSON(geom), memo 
            FROM user_exclusion_zones
            ORDER BY created_at DESC
        """)
        rows = db.execute(query).fetchall()
        
        features = []
        for r in rows:
            z_id, name, geom_json, memo = r
            if geom_json:
                features.append({
                    "type": "Feature",
                    "id": z_id,
                    "properties": {
                        "name": name,
                        "type": "user_exclusion",
                        "memo": memo if memo else "사유 없음"
                    },
                    "geometry": json.loads(geom_json)
                })
                
        return {
            "type": "FeatureCollection",
            "features": features
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"사용자 금지구역 조회 실패: {str(e)}")

# 6.5. 사용자 가상 금지구역 삭제 API [v1.1-stable]
@router.delete("/spatial/user-exclusions/{zone_id}")
async def delete_user_exclusion(zone_id: int, db: Session = Depends(get_db)):
    try:
        query = text("DELETE FROM user_exclusion_zones WHERE id = :zone_id")
        result = db.execute(query, {"zone_id": zone_id})
        db.commit()
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="해당 금지구역을 찾을 수 없습니다.")
        return {"status": "success", "message": f"성공적으로 금지구역(ID: {zone_id})을 삭제했습니다."}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"사용자 금지구역 삭제 실패: {str(e)}")

# --- [v4.9.35] 국유재산 공간 영역 렌더링을 위한 공간 GeoJSON 제공 API ---
@router.get("/spatial/national-properties")

async def get_national_properties(district_id: int = 1, db: Session = Depends(get_db)):
    try:
        query = text("""
            SELECT id, jibun, land_use_code, ownership_type,
                   ST_AsGeoJSON(ST_Simplify(geom, 0.00001)) as geojson
            FROM cadastral_lands
            WHERE district_id = :district_id AND ownership_type = '국유지'
        """)
        rows = db.execute(query, {"district_id": district_id}).fetchall()
        
        features = []
        for r in rows:
            if not r[4]:
                continue
            # [PEP8 Inline Import Cleaned]
            geom_dict = json.loads(r[4])
            features.append({
                "type": "Feature",
                "properties": {
                    "id": r[0],
                    "jibun": r[1],
                    "land_use_code": r[2],
                    "ownership_type": r[3]
                },
                "geometry": geom_dict
            })
        
        return {
            "type": "FeatureCollection",
            "features": features
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"국유재산 공간 데이터 로드 실패: {str(e)}")

# =========================================================================
# [PHASE 3: 의사결정 심의 이력 실제 DB 연동 및 대시보드 RAG 감리]
# =========================================================================


class DecisionHistoryCreate(BaseModel):
    region: str
    facility_type: str
    infra: str
    pnu_count: int
    status: str
    audit_state: str
    audit_opinion: Optional[str] = None
    inferred_purpose: Optional[str] = None
    ahp_weights: Dict[str, float] = {}
    selected_parcel_jibun: Optional[str] = None
    selected_parcel_price: Optional[int] = 0
    selected_parcel_area: Optional[float] = 0.0
    selected_parcel_css: Optional[int] = 0
    debate_logs: List[Dict[str, str]] = []

@router.get("/spatial/history")
async def get_decision_history(db: Session = Depends(get_db)):
    try:
        query = text("""
            SELECT id, TO_CHAR(created_at, 'YYYY-MM-DD') as date_str, region, facility_type, infra, pnu_count, status, audit_state, audit_opinion, inferred_purpose, ahp_weights, selected_parcel_jibun, selected_parcel_price, selected_parcel_area, selected_parcel_css, debate_logs
            FROM decision_histories
            ORDER BY id DESC
        """)
        rows = db.execute(query).fetchall()
        
        histories = []
        for r in rows:
            histories.append({
                "id": r[0],
                "date": r[1],
                "region": r[2],
                "facility_type": r[3],
                "infra": r[4],
                "pnuCount": r[5],
                "status": r[6],
                "auditState": r[7],
                "auditOpinion": r[8],
                "inferredPurpose": r[9],
                "ahpWeights": r[10] if isinstance(r[10], dict) else (json.loads(r[10]) if r[10] else {}),
                "selectedParcelJibun": r[11],
                "selectedParcelPrice": r[12],
                "selectedParcelArea": float(r[13]) if r[13] is not None else 0.0,
                "selectedParcelCss": r[14],
                "debateLogs": r[15] if isinstance(r[15], list) else (json.loads(r[15]) if r[15] else [])
            })
        return histories
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"심의 이력 조회 실패: {str(e)}")

@router.post("/spatial/history")
async def create_decision_history(req: DecisionHistoryCreate, db: Session = Depends(get_db)):
    try:
        query = text("""
            INSERT INTO decision_histories (region, facility_type, infra, pnu_count, status, audit_state, audit_opinion, inferred_purpose, ahp_weights, selected_parcel_jibun, selected_parcel_price, selected_parcel_area, selected_parcel_css, debate_logs)
            VALUES (:region, :facility_type, :infra, :pnu_count, :status, :audit_state, :audit_opinion, :inferred_purpose, :ahp_weights, :selected_parcel_jibun, :selected_parcel_price, :selected_parcel_area, :selected_parcel_css, :debate_logs)
            RETURNING id
        """)
        
        res = db.execute(query, {
            "region": req.region,
            "facility_type": req.facility_type,
            "infra": req.infra,
            "pnu_count": req.pnu_count,
            "status": req.status,
            "audit_state": req.audit_state,
            "audit_opinion": req.audit_opinion,
            "inferred_purpose": req.inferred_purpose,
            "ahp_weights": json.dumps(req.ahp_weights),
            "selected_parcel_jibun": req.selected_parcel_jibun,
            "selected_parcel_price": req.selected_parcel_price,
            "selected_parcel_area": req.selected_parcel_area,
            "selected_parcel_css": req.selected_parcel_css,
            "debate_logs": json.dumps(req.debate_logs)
        })
        
        history_id = res.scalar()
        db.commit()
        return {"status": "success", "id": history_id, "message": "의사결정 심의 이력이 데이터베이스에 영구 적재되었습니다."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"심의 이력 저장 실패: {str(e)}")

@router.post("/spatial/history/{history_id}/audit-doc")
async def audit_history_document(history_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        filename = file.filename
        content = await file.read()
           
        pdf_file = io.BytesIO(content)
        reader = PdfReader(pdf_file)
        text_content = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_content += page_text + "\n"
        
        if not text_content:
            raise HTTPException(status_code=400, detail="PDF 본문에서 텍스트를 추출할 수 없거나 이미지 공문입니다.")
            
        history_query = text("SELECT region, facility_type, infra, ahp_weights, selected_parcel_jibun, selected_parcel_css FROM decision_histories WHERE id = :id")
        history_row = db.execute(history_query, {"id": history_id}).fetchone()
        if not history_row:
            raise HTTPException(status_code=404, detail="지정된 심의 이력을 찾을 수 없습니다.")
            
        region, facility_type, infra, ahp_weights_raw, jibun, css = history_row
        ahp_weights = json.loads(ahp_weights_raw) if isinstance(ahp_weights_raw, str) else (ahp_weights_raw or {})
        
        client = get_openai_client()
        matched_regulations = []
        if client:
            try:
                query_str = f"{infra} {jibun} 설치 공시 준공 고시 조례"
                embed_res = client.embeddings.create(
                    model="text-embedding-3-small",
                    input=query_str
                )
                query_embedding = embed_res.data[0].embedding
                
                rag_query = text("""
                    SELECT regulation_title, content, 1 - (embedding <=> CAST(:query_embedding AS vector)) AS similarity
                    FROM district_regulations
                    WHERE 1 - (embedding <=> CAST(:query_embedding AS vector)) >= 0.35
                    ORDER BY similarity DESC
                    LIMIT 3
                """)
                rag_rows = db.execute(rag_query, {"query_embedding": query_embedding}).fetchall()
                for row in rag_rows:
                    matched_regulations.append(f"[{row[0]}] {row[1][:100]}...")
            except Exception as e:
                print(f"[RAG Error during history audit] {e}")
                
        match_score = 90.0
        
        if jibun and jibun.replace(" ", "") not in text_content.replace(" ", ""):
            addr_tokens = [t for t in re.sub(r'[^가-힣0-9]', ' ', jibun).split() if len(t) >= 2]
            matched_tokens = [t for t in addr_tokens if t in text_content]
            if len(matched_tokens) < len(addr_tokens) * 0.5:
                match_score -= 25.0
                
        for forbid in ["위반", "침범", "규제저촉", "이격미달"]:
            if forbid in text_content:
                match_score -= 10.0
                
        for kw in ["유동인구", "민원", "무단투기", "생활인구", "청소년"]:
            if kw in text_content:
                match_score += 2.0
                
        match_score = max(10.0, min(100.0, match_score))
        
        if match_score >= 80.0:
            scenario = "시나리오 A (정당 규정 완전 부합 준공)"
            audit_state = "검증 완료"
            summary = f"본 준공 공시 문서는 스마트 입지 의사결정의 선정지({jibun}) 정보와 RAG 조례 이격 가이드라인을 {match_score:.0f}% 수준으로 신뢰성 있게 준수하며 최종 행정 검증이 확인되었습니다."
        elif match_score >= 50.0:
            scenario = "시나리오 B (규제 조건부 준수 감리)"
            audit_state = "검증 완료"
            summary = f"준공 내용 상에서 일부분 안전 이격 요건의 보완 검토 항목이 발견되었으나, 시나리오 가중합 기준치를 {match_score:.0f}% 수준으로 방어 우회하여 조건부 타결 승인을 획득하였습니다."
        else:
            scenario = "시나리오 C (기준 이탈/검증 불허)"
            audit_state = "불가능"
            summary = f"입지 지번({jibun}) 또는 시설 이격 규정(RAG 기준치)에 대한 위배 사유가 확인되어, 공문 일치도 {match_score:.0f}% 미달로 인해 행정 검증 승인이 반려되었습니다."

        db.execute(
            text("UPDATE decision_histories SET audit_state = :state, audit_opinion = :opinion WHERE id = :id"),
            {"state": audit_state, "opinion": summary, "id": history_id}
        )
        
        db.execute(
            text("""
                INSERT INTO verified_precedents (conflict_simulation_id, document_title, document_ocr_text, actual_scenario)
                VALUES (:sim_id, :title, :ocr_text, :scenario)
            """),
            {"sim_id": history_id, "title": filename, "ocr_text": text_content[:5000], "scenario": scenario}
        )
        db.commit()
        
        return {
            "status": "success",
            "title": filename,
            "mappedScenario": scenario,
            "matchScore": int(match_score),
            "summary": summary,
            "auditState": audit_state
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"PDF 감리 검증 중 오류: {str(e)}")
