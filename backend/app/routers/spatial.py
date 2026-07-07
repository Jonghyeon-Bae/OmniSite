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

# 3단계 의사결정 인자별 동적 공간 데이터 밀도/통계 집계 엔진
def get_criteria_score(db: Session, key: str, dong_id: int, centroid_lng: float, centroid_lat: float, associated_file: Optional[str] = None) -> float:
    key_clean = key.lower().strip()
    
    # 1. 만약 이번 실행에서 업로드된 전용 CSV 파일(associated_file)이 존재한다면,
    # 해당 파일 데이터만 조회하여 격리 연산 수행
    if associated_file:
        check_query = text("SELECT COUNT(*) FROM city_spatial_features WHERE feature_name = :filename")
        exists_count = db.execute(check_query, {"filename": associated_file}).scalar()
        
        if exists_count > 0:
            # 동별 통계형 데이터인지 개별 포인트형 시설물 데이터인지 판별
            # (총 레코드 수가 적고 dong_id가 지정되어 있다면 행정동별 통계 데이터로 간주)
            stats_query = text("""
                SELECT COUNT(*), COUNT(DISTINCT dong_id) 
                FROM city_spatial_features
                WHERE feature_name = :filename AND dong_id IS NOT NULL
            """)
            total_cnt, distinct_dongs = db.execute(stats_query, {"filename": associated_file}).fetchone()
            
            # 동별 통계 데이터인 경우
            if total_cnt > 0 and total_cnt < 100 and distinct_dongs > 1:
                query = text("""
                    SELECT properties FROM city_spatial_features
                    WHERE feature_name = :filename AND dong_id = :dong_id
                    LIMIT 1
                """)
                row = db.execute(query, {"filename": associated_file, "dong_id": dong_id}).fetchone()
                if row:
                    properties = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                    data_dict = properties.get("data", {}) if properties else {}
                    # 지표 키워드와 유사한 컬럼 우선 탐색하여 값 파싱
                    for col_name, col_val in data_dict.items():
                        if any(w in col_name.lower() for w in [key_clean, "인구", "비율", "수", "건수", "count", "value", "ratio", "boarding"]):
                            try:
                                return float(str(col_val).replace(",", "").strip())
                            except ValueError:
                                continue
                    # 첫 번째 변환 가능한 숫자값 탐색
                    for col_name, col_val in data_dict.items():
                        try:
                            return float(str(col_val).replace(",", "").strip())
                        except ValueError:
                            continue
                return 0.0
            
            # 개별 포인트형 시설물 데이터인 경우 (공간 밀도/이격거리 연산 적용)
            radius = 500
            if any(w in key_clean for w in ["traffic", "transit", "subway", "bus"]):
                radius = 300
            elif any(w in key_clean for w in ["dumping", "trash", "garbage", "complaint", "civil"]):
                radius = 200
                
            query = text("""
                SELECT COUNT(*)
                FROM city_spatial_features
                WHERE feature_name = :filename
                  AND ST_DWithin(geom::geography, ST_MakePoint(:lng, :lat)::geography, :radius)
            """)
            res = db.execute(query, {
                "filename": associated_file,
                "lng": centroid_lng,
                "lat": centroid_lat,
                "radius": radius
            }).scalar()
            return float(res)

    # 2. 업로드 파일이 없거나 존재하지 않는 경우, 기존 글로벌 시드 데이터 Fallback 참조
    # 2-1. 대중교통 관련 (버스/지하철 유동인구)
    if any(w in key_clean for w in ["traffic", "transit", "subway", "bus"]):
        query = text("""
            SELECT COALESCE(SUM(boarding_count + alighting_count), 0)
            FROM transit_passengers p
            JOIN transit_stations s ON p.station_id = s.id
            WHERE ST_DWithin(s.geom::geography, ST_MakePoint(:lng, :lat)::geography, 300)
        """)
        res = db.execute(query, {"lng": centroid_lng, "lat": centroid_lat}).scalar()
        return float(res)
        
    # 2-2. 민원 관련
    elif any(w in key_clean for w in ["complaint", "civil_complaint"]):
        if dong_id:
            query = text("""
                SELECT COALESCE(SUM(complaint_count), 0)
                FROM civil_complaints
                WHERE dong_id = :dong_id
            """)
            res = db.execute(query, {"dong_id": dong_id}).scalar()
            return float(res)
        return 0.0
        
    # 2-3. 무단투기 및 쓰레기 관련
    elif any(w in key_clean for w in ["dumping", "trash", "garbage"]):
        query = text("""
            SELECT COUNT(*)
            FROM illegal_dumping_zones
            WHERE ST_DWithin(geom::geography, ST_MakePoint(:lng, :lat)::geography, 200)
        """)
        res = db.execute(query, {"lng": centroid_lng, "lat": centroid_lat}).scalar()
        return float(res)
        
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
              AND ST_DWithin(geom::geography, ST_MakePoint(:lng, :lat)::geography, 500)
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
        # 0. HITL 기준점 좌표 (Step 2에서 사용자가 배치한 마커 좌표)
        base_lat = ref_lat if ref_lat else 37.5302
        base_lng = ref_lng if ref_lng else 126.9724

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

        # 2. PostGIS 다기준 배제 구역(Mask) 생성 및 HITL 기준점 인근 국공유지 차집합 지적 필지 조회
        # 마커 기준 반경 1km 이내 우선 탐색 + 배제 구역 제외 + 거리순 정렬
        spatial_query = text("""
            WITH exclusion_mask AS (
                SELECT ST_Union(ST_Buffer(geom::geography, buffer_radius)::geometry) AS geom
                FROM (
                    SELECT geom, 200 AS buffer_radius FROM childcare_centers WHERE center_type IN ('초등학교', '유치원')
                    UNION ALL
                    SELECT geom, 30 AS buffer_radius FROM childcare_centers WHERE center_type = '어린이집'
                    UNION ALL
                    SELECT geom, 10 AS buffer_radius FROM transit_stations WHERE transit_type IN ('BUS', 'SUBWAY')
                ) t
            )
            SELECT c.id, c.pnu, c.jibun, c.land_use_code, c.ownership_type, 
                   ST_Area(c.geom::geography) AS area, 
                   ST_X(ST_Centroid(c.geom)) AS lng, 
                   ST_Y(ST_Centroid(c.geom)) AS lat, 
                   c.dong_id,
                   ST_Distance(ST_Centroid(c.geom)::geography, ST_MakePoint(:ref_lng, :ref_lat)::geography) AS dist_from_ref
            FROM cadastral_lands c, exclusion_mask m
            WHERE c.district_id = 1
              AND c.ownership_type IN ('국유지', '시유지', '구유지')
              AND ST_IsValid(c.geom)
              AND (m.geom IS NULL OR NOT ST_Intersects(c.geom, m.geom))
              AND ST_DWithin(ST_Centroid(c.geom)::geography, ST_MakePoint(:ref_lng, :ref_lat)::geography, 1000)
            ORDER BY dist_from_ref ASC
            LIMIT 15
        """)
        
        candidates = []
        try:
            rows = db.execute(spatial_query, {"ref_lng": base_lng, "ref_lat": base_lat}).fetchall()
            for r in rows:
                candidates.append({
                    "id": r[0], "pnu": r[1], "jibun": r[2], "land_use_code": r[3],
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
                candidates.append({
                    "id": i + 1,
                    "pnu": f"111701{1100 + i * 100}10{42 + i * 3:04d}0000",
                    "jibun": f"{ref_dong_name} {42 + i * 3}-{i + 1} ({ownership_types[i]})",
                    "land_use_code": ["잡", "대", "공"][i],
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
                score = get_criteria_score(db, k, cand["dong_id"], cand["lng"], cand["lat"], assoc_file)
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
class DebateRequest(BaseModel):
    facility_type: str = "city_feature"
    inferred_purpose: str = ""
    candidate_jibun: str = ""
    candidate_css: int = 50
    candidate_lat: float = 37.53
    candidate_lng: float = 126.97
    ahp_weights: Dict[str, float] = {}

@router.post("/spatial/debate")
async def stream_debate_sim(req: DebateRequest, db: Session = Depends(get_db)):
    from app.routers.upload import get_openai_client
    client = get_openai_client()
    
    # pgvector RAG: 도메인 관련 조례 텍스트 Top-3 청크 조회
    rag_context = ""
    try:
        from app.routers.upload import get_embedding
        query_text = f"{req.facility_type} {req.inferred_purpose}"
        query_embedding = get_embedding(query_text)
        if query_embedding:
            rag_query = text("""
                SELECT content, 1 - (embedding <=> :query_embedding) AS similarity
                FROM district_regulations
                WHERE district_id = 1
                  AND 1 - (embedding <=> :query_embedding) >= 0.35
                ORDER BY similarity DESC
                LIMIT 3
            """)
            rag_rows = db.execute(rag_query, {"query_embedding": str(query_embedding)}).fetchall()
            if rag_rows:
                chunks = [row[0] for row in rag_rows]
                rag_context = "\n---\n".join(chunks)
    except Exception:
        rag_context = ""

    # AHP 가중치 텍스트 조립
    ahp_text = ", ".join([f"{k}: {v}" for k, v in req.ahp_weights.items()]) if req.ahp_weights else "기본 균등 가중치"
    
    # CSS 등급 한글 매핑
    css_grade = "상(높음)" if req.candidate_css >= 70 else ("중(보통)" if req.candidate_css >= 40 else "하(낮음)")

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
        
        if rag_context:
            system_prompt += (
                "## 관련 자치구 조례 및 규정 (pgvector RAG 조회 결과)\n"
                f"{rag_context}\n\n"
            )
        
        system_prompt += (
            "## 토론 규칙\n"
            "위 맥락 정보와 조례를 반드시 근거로 인용하며 토론하십시오.\n"
            "찬성 측(소상공인 대표), 반대 측(구민 연대 대표), 조정안(구청 행정 사무관)의 세 발언자가 "
            "서로 번갈아 가며 한 턴씩 의견을 개진합니다.\n"
            "반드시 아래의 정해진 대화 출력 형식을 지키십시오:\n"
            "상인대표 (찬성): ... \n"
            "구민대표 (반대): ... \n"
            "조정관 (조정안): ... \n\n"
            "각 발언자는 위 맥락의 구체적인 시설 유형, 후보지 위치, CSS 점수, 조례 조항을 직접 언급하여 토론하십시오."
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
                
                while True:
                    # 비동기적으로 큐에서 데이터 획득
                    content = await asyncio.to_thread(q.get)
                    if content is None:
                        break
                    yield f"data: {json.dumps({'text': content}, ensure_ascii=False)}\n\n"
                    
            except Exception as e:
                yield f"data: {json.dumps({'text': f'토론 중 에러 발생: {str(e)}'}, ensure_ascii=False)}\n\n"
                
        return StreamingResponse(event_generator(), media_type="text/event-stream")
    else:
        # Mock Fallback: 컨텍스트 기반 대사 생성
        async def mock_event_generator():
            dialogue = [
                f"[토론 시작] '{req.candidate_jibun}' 부지의 '{req.inferred_purpose}' 입지 갈등 분석 모의 토론을 시작합니다. (CSS: {req.candidate_css}점, {css_grade})\n\n",
                f"상인대표 (찬성): 이번 {req.facility_type} 시설 도입은 '{req.candidate_jibun}' 인근 유동 인구를 불러모으고 침체된 골목 상권을 활성화하는 좋은 계기가 될 것입니다. AHP 분석({ahp_text}) 결과에서도 입지 적합성이 입증되었습니다.\n\n",
                f"구민대표 (반대): 하지만 갈등 민감도가 {req.candidate_css}점({css_grade})으로 나타난 만큼, 주거지와 지나치게 가깝습니다. 소음 유발 및 통행 불편, 그리고 청소년 교육 환경 측면에서 우려가 큽니다.\n\n",
                f"조정관 (조정안): 양측의 입장을 모두 이해합니다. 관할 자치구 조례를 준수하면서, '{req.candidate_jibun}' 인근에 완충 시설(펜스, 가림막)을 추가 설치하여 민원 피해를 최소화하는 중재안을 검토하겠습니다.\n\n",
                f"[토론 종료] 3자 토론 합의안이 성공적으로 도출되었습니다. (시설유형: {req.facility_type}, 후보지: {req.candidate_jibun})"
            ]
            for segment in dialogue:
                for char in segment:
                    yield f"data: {json.dumps({'text': char}, ensure_ascii=False)}\n\n"
                    await asyncio.sleep(0.02)
                await asyncio.sleep(0.5)
                
        return StreamingResponse(mock_event_generator(), media_type="text/event-stream")

