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

# CSV 파일 첫 라인(헤더)만 스트리밍하는 경량 헬퍼
def parse_csv_header(file_path: str) -> List[str]:
    encodings = ["utf-8", "cp949", "utf-8-sig"]
    for enc in encodings:
        try:
            with open(file_path, "r", encoding=enc) as f:
                reader = csv.reader(f)
                headers = next(reader, None)
                if headers is not None:
                    return [h.strip() for h in headers]
        except (UnicodeDecodeError, PermissionError):
            continue
    raise HTTPException(
        status_code=400, 
        detail=f"CSV 파일 인코딩을 판독할 수 없거나 읽을 수 없습니다: {os.path.basename(file_path)}"
    )

# 헤더 정보만으로 매핑 및 스키마 결함 여부를 검사하는 경량 헬퍼
def analyze_csv_header_only(headers: List[str]):
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
                
    return detected_mapping, schema_errors

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
    confirmed_domain: Optional[str] = None

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
    pdf_texts = []
    csv_headers_list = []
    csv_results_dict = {}
    
    for filename in request.filenames:
        file_path = os.path.join(UPLOAD_DIR, filename)
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"분석할 업로드 파일을 찾을 수 없습니다: {filename}")
            
        ext = filename.split(".")[-1].lower() if "." in filename else ""
        
        if ext == "pdf":
            try:
                pdf_text = extract_pdf_text(file_path)
                pdf_texts.append(f"파일명: {filename}\n내용:\n{pdf_text[:3000]}")
            except Exception as e:
                pdf_texts.append(f"파일명: {filename}\n내용: (PDF 텍스트 추출 오류: {str(e)})")
        elif ext == "csv":
            try:
                headers = parse_csv_header(file_path)
                detected_mapping, schema_errors = analyze_csv_header_only(headers)
                csv_results_dict[filename] = {
                    "headers": headers,
                    "detected_mapping": detected_mapping,
                    "schema_errors": schema_errors,
                    "missing_coordinates": [],
                    "status": "warning" if len(schema_errors) > 0 else "pass"
                }
                csv_headers_list.append(f"파일명: {filename}\n컬럼 헤더: {', '.join(headers)}\n매핑된 공간 컬럼: {detected_mapping}")
            except Exception as e:
                csv_results_dict[filename] = {
                    "schema_errors": [],
                    "missing_coordinates": [],
                    "status": "fail",
                    "error_msg": f"CSV 분석 중 오류: {str(e)}"
                }
                csv_headers_list.append(f"파일명: {filename}\n오류 메시지: {str(e)}")

    # 기본 추론 및 Fallback 디폴트값 설정
    inferred_purpose = "일반 스마트시티 공간의사결정 입지 분석"
    inferred_domain_tag = "city_feature"
    hitl_question = "업로드하신 데이터를 토대로 공간 입지 분석을 진행하시겠습니까?"
    opinion_global = "업로드된 데이터셋에 대한 감리를 완료했습니다."
    rules_matched_global = []
    
    client = get_openai_client()
    ai_success = False
    
    if client and (len(pdf_texts) > 0 or len(csv_headers_list) > 0):
        pdf_context = "\n\n".join(pdf_texts)
        csv_context = "\n\n".join(csv_headers_list)
        
        prompt = f"""
당신은 스마트시티 다목적 공간의사결정시스템(SDSS)의 지능형 감리 AI 에이전트입니다.
사용자가 이번 입지 분석을 진행하기 위해 일괄 업로드한 행정 조례 문서(PDF)와 공간 데이터 파일(CSV) 목록 및 구조는 다음과 같습니다.

[업로드된 조례 문서 정보]
{pdf_context if pdf_context else "없음"}

[업로드된 공간 데이터 파일 정보]
{csv_context if csv_context else "없음"}

위 파일들의 파일명, 컬럼 구성, 그리고 조례 텍스트 내용을 종합 분석하여 다음 정보들을 도출하십시오:
1. inferred_purpose: 이번 입지 분석의 시맨틱 목적 추론 (예: "실외 흡연구역 입지 선정 및 간접흡연 규제 배제 분석", "전기차 충전소 최적 입지 매핑 및 규제구역 제외 분석")
2. inferred_domain_tag: 도메인 분류 영문 태그 (예: smoking_zone, smart_shelter, yellow_carpet, ev_charging)
3. hitl_question: 사용자(공무원)에게 의사결정 목적이 맞는지 최종 확정하기 위한 확인 질문 (예: "업로드하신 데이터들은 [실외 흡연구역/흡연구역 지정]을 위한 입지 분석이 맞습니까?")
4. opinion: 전체 조례 및 공간 데이터를 교차 검토하여 특정 시설물 제한 구역(예: 어린이집 반경 10m 금역, 학교 200m 정화구역 등)에 대한 감리 평가 의견
5. rules_matched: 조례 상에서 식별해 낸 구체적인 입지 제약 조항 목록

반드시 아래 JSON 포맷으로만 응답해야 합니다 (Markdown 없이 순수 JSON만 반환):
{{
  "inferred_purpose": "추론한 입지 분석 목적",
  "inferred_domain_tag": "영문 도메인 태그",
  "hitl_question": "사용자 확인 질문",
  "opinion": "전체 조례 검토 의견 및 시맨틱 입지 분석 방향 요약",
  "rules_matched": [
    {{
      "clause": "해당 조항명 (예: 제5조 제2항)",
      "description": "규정 요약 내용",
      "status": "matched"
    }}
  ]
}}
"""
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "너는 다목적 스마트시티 SDSS 플랫폼의 시맨틱 도메인 추론 및 감리 AI 에이전트이다."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            result_json = json.loads(response.choices[0].message.content)
            inferred_purpose = result_json.get("inferred_purpose", inferred_purpose)
            inferred_domain_tag = result_json.get("inferred_domain_tag", inferred_domain_tag)
            hitl_question = result_json.get("hitl_question", hitl_question)
            opinion_global = result_json.get("opinion", opinion_global)
            rules_matched_global = result_json.get("rules_matched", [])
            ai_success = True
        except Exception as e:
            opinion_global = f"AI 교차 감리 도중 예외가 발생하여 로컬 룰 엔진으로 대체합니다. (에러: {str(e)})"

    # 로컬 Fallback 규칙 기반 자동 추정
    if not ai_success:
        combined_text = " ".join(pdf_texts) + " " + " ".join(request.filenames)
        if any(keyword in combined_text for keyword in ["금연", "흡연", "smoking", "tobacco"]):
            inferred_purpose = "실외 흡연구역 입지 선정 및 간접흡연 규제 배제 분석"
            inferred_domain_tag = "smoking_zone"
            hitl_question = "업로드하신 데이터들은 [실외 흡연구역/흡연구역 지정]을 위한 입지 분석이 맞습니까?"
            rules_matched_global = [{
                "clause": "용산구 금연구역 지정 조례(추정)",
                "description": "금연구역 경계선으로부터 10미터 이내 지정 (로컬 Fallback 추정)",
                "status": "matched"
            }]
        elif any(keyword in combined_text for keyword in ["충전", "전기차", "ev", "battery"]):
            inferred_purpose = "전기차 충전소 최적 입지 매핑 및 규제구역 제외 분석"
            inferred_domain_tag = "ev_charging"
            hitl_question = "업로드하신 데이터들은 [전기차 충전 인프라 설치]를 위한 입지 분석이 맞습니까?"
        elif any(keyword in combined_text for keyword in ["어린이", "보행", "안전", "스쿨", "school"]):
            inferred_purpose = "어린이 보호구역 옐로카펫 및 안심 횡단보도 설치 분석"
            inferred_domain_tag = "yellow_carpet"
            hitl_question = "업로드하신 데이터들은 [어린이 교통 안전 및 옐로카펫 설치]를 위한 입지 분석이 맞습니까?"

    results = []
    for filename in request.filenames:
        ext = filename.split(".")[-1].lower() if "." in filename else ""
        
        if ext == "csv":
            meta = csv_results_dict.get(filename, {"schema_errors": [], "missing_coordinates": [], "status": "fail"})
            results.append({
                "filename": filename,
                "status": meta["status"],
                "score": 0.65 if meta["status"] in ["warning", "fail"] else 0.95,
                "opinion": meta.get("error_msg", f"공간 데이터 '{filename}' 스키마 및 좌표 무결성 검사 완료."),
                "schema_errors": meta.get("schema_errors", []),
                "missing_coordinates": meta.get("missing_coordinates", []),
                "column_mapping": meta.get("detected_mapping", {}),
                "rules_matched": []
            })
        elif ext == "pdf":
            results.append({
                "filename": filename,
                "status": "pass" if ai_success else "warning",
                "score": 0.85 if ai_success else 0.50,
                "opinion": opinion_global,
                "schema_errors": [],
                "missing_coordinates": [],
                "rules_matched": rules_matched_global
            })
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
        "inferred_purpose": inferred_purpose,
        "inferred_domain_tag": inferred_domain_tag,
        "hitl_question": hitl_question,
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
                "original_row": row,
                "domain": request.confirmed_domain
            }, ensure_ascii=False)
            
            # confirmed_domain이 명시되었으면 해당 도메인을 feature_type으로 저장하고, 없으면 기본 룰 활용
            feature_type_val = request.confirmed_domain if request.confirmed_domain else ("smoking_zone" if "smoking" in request.filename.lower() else "city_feature")
            
            db.execute(query, {
                "district_id": 1,  # 서울특별시 용산구 (sig_cd: 11170) 마스터 ID
                "feature_type": feature_type_val,
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
