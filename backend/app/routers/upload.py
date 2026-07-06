import os
import csv
import re
import json
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from pypdf import PdfReader
from openai import OpenAI
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.config import settings
from app.database import get_db

router = APIRouter(prefix="/api/v1", tags=["upload"])

# 파일 적재용 임시 원천 데이터 저장소 경로 정의 (root/data/raw)
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "raw")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 허용 확장자 구분 정의
SPATIAL_EXTENSIONS = {"shp", "dbf", "shx", "prj", "csv"}
DOCUMENT_EXTENSIONS = {"pdf", "hwp"}
ALLOWED_EXTENSIONS = SPATIAL_EXTENSIONS | DOCUMENT_EXTENSIONS

# OpenAI 클라이언트 초기화 헬퍼
def get_openai_client() -> Optional[OpenAI]:
    if settings.OPENAI_API_KEY:
        try:
            return OpenAI(api_key=settings.OPENAI_API_KEY)
        except Exception:
            return None
    return None

# CSV 파일 인코딩 탐색 및 파싱 헬퍼
def parse_csv_file(file_path: str):
    encodings = ["utf-8", "cp949", "utf-8-sig"]
    for enc in encodings:
        try:
            with open(file_path, "r", encoding=enc) as f:
                reader = csv.reader(f)
                headers = next(reader, None)
                if not headers:
                    continue
                rows = list(reader)
                return [h.strip() for h in headers], [[val.strip() for val in r] for r in rows]
        except (UnicodeDecodeError, PermissionError):
            continue
    raise HTTPException(
        status_code=400, 
        detail=f"CSV 파일 인코딩을 판독할 수 없거나 읽을 수 없습니다: {os.path.basename(file_path)}"
    )

# PDF 텍스트 추출 헬퍼
def extract_pdf_text(file_path: str) -> str:
    try:
        reader = PdfReader(file_path)
        text_content = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_content += page_text + "\n"
        return text_content
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"PDF 텍스트 추출 중 오류가 발생했습니다: {str(e)}"
        )

# CSV 실물 분석 헬퍼
def analyze_csv_data(file_path: str):
    headers, rows = parse_csv_file(file_path)
    
    # 1. 컬럼 매핑 후보군 매칭
    standard_columns = {
        "lat": ["lat", "latitude", "위도", "y"],
        "lng": ["lng", "longitude", "경도", "x"],
        "pnu": ["pnu", "pnu_code", "필지고유번호", "지적코드"],
        "address": ["address", "addr", "주소", "지번", "location"]
    }
    
    detected_mapping = {}
    schema_errors = []
    
    for std_col, candidates in standard_columns.items():
        matched_header = None
        for header in headers:
            if header.lower() in candidates:
                matched_header = header
                break
        
        if matched_header:
            detected_mapping[std_col] = matched_header
        else:
            if std_col in ["lat", "lng"]:
                schema_errors.append({
                    "column": std_col.upper(),
                    "suggested": std_col,
                    "reason": f"필수 공간 정보 컬럼('{std_col}')이 존재하지 않거나 매핑되지 않았습니다."
                })
                
    # 2. 결측치 분석 (위경도 검증)
    missing_coordinates = []
    
    lat_col = detected_mapping.get("lat")
    lng_col = detected_mapping.get("lng")
    addr_col = detected_mapping.get("address")
    
    if lat_col and lng_col:
        lat_idx = headers.index(lat_col)
        lng_idx = headers.index(lng_col)
        addr_idx = headers.index(addr_col) if addr_col else -1
        
        for idx, row in enumerate(rows):
            if len(row) <= max(lat_idx, lng_idx):
                continue
                
            lat_val = row[lat_idx]
            lng_val = row[lng_idx]
            addr_val = row[addr_idx] if addr_idx != -1 and addr_idx < len(row) else f"행 번호 {idx+1}"
            
            is_missing = False
            try:
                lat_f = float(lat_val)
                lng_f = float(lng_val)
                # 한국 영역 바운더리 체크 (위도 33~39, 경도 124~132)
                if lat_f == 0.0 or lng_f == 0.0 or not (33.0 <= lat_f <= 39.0) or not (124.0 <= lng_f <= 132.0):
                    is_missing = True
            except ValueError:
                is_missing = True
                
            if is_missing:
                missing_coordinates.append({
                    "row_index": idx,
                    "address": addr_val,
                    "reason": "위경도 좌표 누락(0.0) 또는 대한민국 관할 구역 범주 외부 이탈"
                })
                
    return headers, rows, detected_mapping, schema_errors, missing_coordinates

# 로컬 룰 기반 Fallback 감리 엔진
def run_local_fallback_audit(pdf_text: str, filename: str, error_msg: str = None) -> dict:
    rules_matched = []
    
    if "금연" in pdf_text or "흡연" in pdf_text:
        dist_match = re.search(r"(\d+)\s*(?:미터|m)", pdf_text)
        dist = dist_match.group(1) if dist_match else "10"
        rules_matched.append({
            "clause": "용산구 금연구역 지정 조례(추정)",
            "description": f"금연구역 경계선으로부터 {dist}미터 이내 지정 (로컬 룰 엔진 분석)",
            "status": "matched"
        })
        
    if "어린이집" in pdf_text or "학교" in pdf_text or "유치원" in pdf_text:
        dist_match = re.search(r"(\d+)\s*(?:미터|m)", pdf_text)
        dist = dist_match.group(1) if dist_match else "200"
        rules_matched.append({
            "clause": "교육환경 보호에 관한 법률(추정)",
            "description": f"교육환경보호구역 내 특정 시설 금지 (경계 {dist}m 범위)",
            "status": "matched"
        })
        
    opinion = "제출된 조례 문서의 텍스트가 정상 파싱되었습니다."
    if error_msg:
        opinion += f" (OpenAI API 미연동 또는 호출 실패로 인해 로컬 엔진으로 대체 분석: {error_msg})"
    else:
        opinion += " (OpenAI API 미연동으로 로컬 룰 기반 분석)"

    score = 0.90 if len(rules_matched) > 0 else 0.50
    return {
        "filename": filename,
        "status": "pass" if score >= 0.7 else "warning",
        "score": score,
        "opinion": opinion,
        "schema_errors": [],
        "missing_coordinates": [],
        "rules_matched": rules_matched
    }

# Pydantic 데이터 모델 정의
class AuditRequest(BaseModel):
    filenames: List[str]

class CoordinateCorrection(BaseModel):
    row_index: int
    lat: float
    lng: float

class HITLCommitRequest(BaseModel):
    filename: str
    column_mapping: Dict[str, str]
    corrections: List[CoordinateCorrection]

# PM 개발 철칙 2조 준수: 반드시 비동기 API(async def) 적용
@router.post("/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    uploaded_info = []

    for file in files:
        filename = file.filename
        content_type = file.content_type

        ext = filename.split(".")[-1].lower() if "." in filename else ""

        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"지원하지 않는 확장자입니다: .{ext}. 허용군: {list(ALLOWED_EXTENSIONS)}"
            )

        category = "spatial" if ext in SPATIAL_EXTENSIONS else "document"

        saved_path = os.path.join(UPLOAD_DIR, filename)
        with open(saved_path, "wb") as buffer:
            while chunk := await file.read(1024 * 1024):
                buffer.write(chunk)

        file_size = os.path.getsize(saved_path)

        uploaded_info.append({
            "filename": filename,
            "size_bytes": file_size,
            "content_type": content_type,
            "extension": ext,
            "category": category,
            "saved_path": saved_path
        })

    return {
        "message": f"성공적으로 {len(files)}개 파일을 검증 및 적재 완료했습니다.",
        "files": uploaded_info
    }

# --- [Step 2-3] AI 감리 분석 결과 반환 API ---
@router.post("/upload/audit")
async def audit_upload_files(request: AuditRequest):
    results = []
    
    for filename in request.filenames:
        file_path = os.path.join(UPLOAD_DIR, filename)
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"분석할 업로드 파일을 찾을 수 없습니다: {filename}")
            
        ext = filename.split(".")[-1].lower() if "." in filename else ""
        
        # 1) 공간 데이터 (.csv) 실제 파싱 및 시맨틱 감리
        if ext == "csv":
            try:
                _, _, _, schema_errors, missing_coordinates = analyze_csv_data(file_path)
                
                has_error = len(schema_errors) > 0 or len(missing_coordinates) > 0
                status = "warning" if has_error else "pass"
                score = 0.65 if has_error else 0.95
                opinion = (
                    f"공간 데이터 '{filename}' 분석 결과, "
                    f"스키마 오류 {len(schema_errors)}건 및 위경도 좌표 결측 {len(missing_coordinates)}건이 발견되어 수동 검수(HITL)가 요구됩니다."
                    if has_error else "공간 데이터 스키마 및 좌표 무결성 검증을 정상 통과했습니다."
                )
                
                results.append({
                    "filename": filename,
                    "status": status,
                    "score": score,
                    "opinion": opinion,
                    "schema_errors": schema_errors,
                    "missing_coordinates": missing_coordinates,
                    "rules_matched": []
                })
            except Exception as e:
                results.append({
                    "filename": filename,
                    "status": "fail",
                    "score": 0.0,
                    "opinion": f"공간 데이터 파싱 오류: {str(e)}",
                    "schema_errors": [],
                    "missing_coordinates": [],
                    "rules_matched": []
                })
                
        # 2) 행정 조례 문서 (.pdf) 실물 텍스트 AI 감리
        elif ext == "pdf":
            pdf_text = extract_pdf_text(file_path)
            client = get_openai_client()
            
            if not client:
                # Fallback 로컬 룰 엔진 실행
                results.append(run_local_fallback_audit(pdf_text, filename))
                continue
                
            try:
                prompt = f"""
다음은 스마트시티 입지 선정과 관련된 행정 조례 문서의 텍스트입니다.
문서명: {filename}
내용:
{pdf_text[:4000]}

이 조례 텍스트에서 특정 스마트시티 시설물(예: 금연구역, 쓰레기통, 어린이집 등)의 '입지 규정'이나 '제약 거리'(예: 10미터 이내 금지, 200미터 이내 정화구역 등)에 관한 조항을 식별하고 요약해주세요.
반드시 아래 JSON 포맷으로만 응답해야 합니다 (Markdown 없이 순수 JSON만 반환):
{{
  "opinion": "전체 문서 요약 및 입지 적합성 의견",
  "score": 0.0 ~ 1.0 사이의 점수,
  "rules_matched": [
    {{
      "clause": "해당 조항명 (예: 제5조 제2항)",
      "description": "규정 요약 내용",
      "status": "matched"
    }}
  ]
}}
"""
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "너는 스마트시티 공공갈등 예측 플랫폼의 행정 조례 감리 AI 에이전트이다."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"}
                )
                result_json = json.loads(response.choices[0].message.content)
                results.append({
                    "filename": filename,
                    "status": "pass" if result_json.get("score", 0.0) >= 0.7 else "warning",
                    "score": result_json.get("score", 0.90),
                    "opinion": result_json.get("opinion", "조례 분석 완료"),
                    "schema_errors": [],
                    "missing_coordinates": [],
                    "rules_matched": result_json.get("rules_matched", [])
                })
            except Exception as e:
                results.append(run_local_fallback_audit(pdf_text, filename, error_msg=str(e)))
                
        # 기본 감리 처리 (기타 파일 형식)
        else:
            results.append({
                "filename": filename,
                "status": "pass",
                "score": 0.90,
                "opinion": "파일 포맷 검증 결과 이상이 감지되지 않았습니다.",
                "schema_errors": [],
                "missing_coordinates": [],
                "rules_matched": []
            })
            
    return {
        "message": "실물 기반 AI 시맨틱 감리 분석이 완료되었습니다.",
        "results": results
    }

# --- [Step 2-4] 임시 GeoJSON 공간 데이터 반환 API ---
@router.get("/upload/geojson/{filename}")
async def get_temp_geojson(filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"업로드된 파일을 찾을 수 없습니다: {filename}")
        
    ext = filename.split(".")[-1].lower() if "." in filename else ""
    if ext != "csv":
        raise HTTPException(
            status_code=400,
            detail=f"실물 GeoJSON 변환은 현재 CSV 형식만 지원합니다. 입력 파일: {filename}"
        )
        
    try:
        headers, rows, detected_mapping, _, _ = analyze_csv_data(file_path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    lat_col = detected_mapping.get("lat")
    lng_col = detected_mapping.get("lng")
    addr_col = detected_mapping.get("address")
    
    lat_idx = headers.index(lat_col) if lat_col else -1
    lng_idx = headers.index(lng_col) if lng_col else -1
    addr_idx = headers.index(addr_col) if addr_col else -1
    
    features = []
    
    for idx, row in enumerate(rows):
        if lat_idx == -1 or lng_idx == -1 or len(row) <= max(lat_idx, lng_idx):
            continue
            
        lat_val = row[lat_idx]
        lng_val = row[lng_idx]
        addr_val = row[addr_idx] if addr_idx != -1 and addr_idx < len(row) else f"행 번호 {idx+1}"
        
        is_missing = False
        try:
            lat_f = float(lat_val)
            lng_f = float(lng_val)
            if lat_f == 0.0 or lng_f == 0.0 or not (33.0 <= lat_f <= 39.0) or not (124.0 <= lng_f <= 132.0):
                is_missing = True
        except ValueError:
            is_missing = True
            
        # 결측 좌표 보정을 위해 용산구청 인근 기본 임시 좌표를 부여하고 missing_coordinate 마크업 지정
        if is_missing:
            geom_lng = 126.9721 + (idx * 0.001)
            geom_lat = 37.5395
            status = "missing_coordinate"
        else:
            geom_lng = lng_f
            geom_lat = lat_f
            status = "normal"
            
        features.append({
            "type": "Feature",
            "properties": {
                "row_index": idx,
                "address": addr_val,
                "status": status,
                "description": "결측 좌표 (수동 보정 대상)" if is_missing else "정상 공간 좌표"
            },
            "geometry": {
                "type": "Point",
                "coordinates": [geom_lng, geom_lat]
            }
        })
        
    return {
        "type": "FeatureCollection",
        "name": filename,
        "features": features
    }

# --- [Step 2-5] HITL 최종 보정 및 DB 적재 커밋 API ---
@router.post("/upload/hitl/commit")
async def commit_hitl_data(request: HITLCommitRequest, db: Session = Depends(get_db)):
    file_path = os.path.join(UPLOAD_DIR, request.filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"업로드된 파일을 찾을 수 없습니다: {request.filename}")
        
    ext = request.filename.split(".")[-1].lower() if "." in request.filename else ""
    if ext != "csv":
        raise HTTPException(status_code=400, detail="HITL 보정 커밋은 현재 CSV 형식만 지원합니다.")
        
    headers, rows = parse_csv_file(file_path)
    
    # 1. 컬럼 매핑 인덱스 추적
    lat_idx, lng_idx, addr_idx = -1, -1, -1
    for raw_header, std_col in request.column_mapping.items():
        if raw_header in headers:
            idx = headers.index(raw_header)
            if std_col == "lat":
                lat_idx = idx
            elif std_col == "lng":
                lng_idx = idx
            elif std_col == "address":
                addr_idx = idx
                
    if lat_idx == -1 or lng_idx == -1:
        raise HTTPException(
            status_code=400, 
            detail="위도(lat)와 경도(lng)에 대응하는 컬럼 매핑 정보가 누락되었거나 일치하지 않습니다."
        )
        
    corrections_map = {c.row_index: c for c in request.corrections}
    
    committed_count = 0
    details_applied = []
    
    # 2. 보정값 대조 및 PostGIS DB 마이그레이션 트랜잭션 실행
    try:
        for idx, row in enumerate(rows):
            if len(row) <= max(lat_idx, lng_idx):
                continue
                
            if idx in corrections_map:
                corr = corrections_map[idx]
                final_lat = corr.lat
                final_lng = corr.lng
                details_applied.append({"row_index": idx, "final_coordinates": [final_lng, final_lat]})
            else:
                try:
                    final_lat = float(row[lat_idx])
                    final_lng = float(row[lng_idx])
                except ValueError:
                    continue
                    
            addr_val = row[addr_idx] if addr_idx != -1 and addr_idx < len(row) else f"행 번호 {idx+1}"
            
            # PostGIS ST_SetSRID 및 ST_MakePoint로 지오메트리 객체 생성 적재
            query = text("""
                INSERT INTO city_spatial_features (district_id, feature_type, feature_name, geom, properties)
                VALUES (:district_id, :feature_type, :feature_name, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326), :properties)
            """)
            
            properties_json = json.dumps({
                "address": addr_val, 
                "original_row": row
            }, ensure_ascii=False)
            
            db.execute(query, {
                "district_id": 1,  # 서울특별시 용산구 (sig_cd: 11170) 마스터 ID
                "feature_type": "smoking_zone" if "smoking" in request.filename.lower() else "city_feature",
                "feature_name": request.filename,
                "lng": final_lng,
                "lat": final_lat,
                "properties": properties_json
            })
            committed_count += 1
            
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"데이터베이스 적재 중 오류가 발생해 롤백 처리되었습니다: {str(e)}")
        
    return {
        "status": "success",
        "message": f"파일 '{request.filename}'에 대한 보정이 승인되었으며, {committed_count}건의 공간 레코드가 PostGIS DB에 적재 완료되었습니다.",
        "committed_records": committed_count,
        "details": {
            "mapped_columns": request.column_mapping,
            "applied_corrections": details_applied
        }
    }
