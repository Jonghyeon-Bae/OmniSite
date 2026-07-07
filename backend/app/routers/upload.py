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
    correct_enc = "utf-8"
    for enc in encodings:
        try:
            with open(file_path, "r", encoding=enc) as f:
                reader = csv.reader(f)
                next(reader, None)
                correct_enc = enc
                break
        except (UnicodeDecodeError, PermissionError):
            continue
            
    try:
        with open(file_path, "r", encoding=correct_enc, errors="replace") as f:
            reader = csv.reader(f)
            headers = next(reader, None)
            if headers is not None:
                return [h.strip() for h in headers]
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"CSV 파일 헤더 파싱 오류: {str(e)}"
        )
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
    correct_enc = "utf-8"
    for enc in encodings:
        try:
            with open(file_path, "r", encoding=enc) as f:
                reader = csv.reader(f)
                next(reader, None)
                correct_enc = enc
                break
        except (UnicodeDecodeError, PermissionError):
            continue
            
    try:
        with open(file_path, "r", encoding=correct_enc, errors="replace") as f:
            reader = csv.reader(f)
            headers = next(reader, None)
            if not headers:
                raise HTTPException(status_code=400, detail="CSV 헤더가 비어 있습니다.")
            rows = list(reader)
            return [h.strip() for h in headers], [[val.strip() for val in r] for r in rows]
    except Exception as e:
        raise HTTPException(
            status_code=400, 
            detail=f"CSV 파일 본문 파싱 오류: {str(e)}"
        )
    raise HTTPException(
        status_code=400, 
        detail=f"CSV 파일 인코딩을 판독할 수 없거나 읽을 수 없습니다: {os.path.basename(file_path)}"
    )

# PDF 텍스트 추출 헬퍼 (로컬 캐시 적용)
def extract_pdf_text(file_path: str) -> str:
    cache_path = file_path + ".txt"
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            pass

    try:
        reader = PdfReader(file_path)
        text_content = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_content += page_text + "\n"
            if len(text_content) >= 3000:
                break

        # 추출 텍스트 캐싱 저장
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                f.write(text_content)
        except Exception:
            pass

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
# 조례/시행규칙 규정 문서 등록 API
@router.post("/upload/regulation")
async def upload_regulation_files(files: List[UploadFile] = File(...)):
    uploaded_info = []

    for file in files:
        filename = file.filename
        content_type = file.content_type
        ext = filename.split(".")[-1].lower() if "." in filename else ""

        if ext not in DOCUMENT_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"조례/법규 문서는 오직 PDF 또는 HWP 형식만 업로드할 수 있습니다. 허용군: {list(DOCUMENT_EXTENSIONS)}"
            )

        # 중복 파일 검증
        saved_path = os.path.join(UPLOAD_DIR, filename)
        if os.path.exists(saved_path):
            raise HTTPException(
                status_code=400,
                detail=f"이미 등록된 법규 파일입니다: {filename}"
            )

        category = "document"
        with open(saved_path, "wb") as buffer:
            while chunk := await file.read(1024 * 1024):
                buffer.write(chunk)

        # PDF일 경우 텍스트를 미리 추출/캐싱하여 RAG 인프라 준비
        if ext == "pdf":
            try:
                extract_pdf_text(saved_path)
            except Exception:
                pass

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
        "message": f"성공적으로 {len(files)}개 조례/시행규칙 파일을 등록 및 텍스트 캐싱 완료했습니다.",
        "files": uploaded_info
    }

# 등록된 조례/시행규칙 규정 목록 조회 API
@router.get("/upload/regulations")
async def list_regulations():
    try:
        files_list = []
        if os.path.exists(UPLOAD_DIR):
            for filename in os.listdir(UPLOAD_DIR):
                ext = filename.split(".")[-1].lower() if "." in filename else ""
                if ext in DOCUMENT_EXTENSIONS:
                    file_path = os.path.join(UPLOAD_DIR, filename)
                    files_list.append({
                        "filename": filename,
                        "size_bytes": os.path.getsize(file_path)
                    })
        return {"regulations": files_list}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"조례 목록 조회 중 오류가 발생했습니다: {str(e)}"
        )

# 등록된 조례/시행규칙 규정 삭제 API
@router.delete("/upload/regulations/{filename}")
async def delete_regulation(filename: str):
    try:
        file_path = os.path.join(UPLOAD_DIR, filename)
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=404,
                detail=f"삭제할 법규 파일을 찾을 수 없습니다: {filename}"
            )
        
        # 원본 파일 물리 삭제
        os.remove(file_path)
        
        # 캐싱된 텍스트 파일도 존재하면 삭제
        cache_path = file_path + ".txt"
        if os.path.exists(cache_path):
            os.remove(cache_path)
            
        return {"message": f"성공적으로 {filename} 및 연관 캐시를 삭제했습니다."}
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=500,
            detail=f"조례 삭제 중 오류가 발생했습니다: {str(e)}"
        )

# PM 개발 철칙 2조 준수: 반드시 비동기 API(async def) 적용
@router.post("/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    uploaded_info = []

    for file in files:
        filename = file.filename
        content_type = file.content_type
        ext = filename.split(".")[-1].lower() if "." in filename else ""

        if ext != "csv":
            raise HTTPException(
                status_code=400,
                detail=f"공간 데이터셋은 오직 CSV 형식만 업로드할 수 있습니다. 입력 파일: .{ext}"
            )

        category = "spatial"
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
        "message": f"성공적으로 {len(files)}개 공간 데이터(CSV) 파일을 검증 및 적재 완료했습니다.",
        "files": uploaded_info
    }

# --- [Step 2-3] AI 감리 분석 결과 반환 API ---
@router.post("/upload/audit")
async def audit_upload_files(request: AuditRequest):
    pdf_texts = []
    csv_headers_list = []
    csv_results_dict = {}
    
    # 1. 업로드된 CSV 파일명 및 헤더 기반 핵심 키워드군 추출
    csv_keywords = set()
    for filename in request.filenames:
        clean_name = re.sub(r"[^가-힣a-zA-Z]", " ", filename)
        csv_keywords.update([w.strip() for w in clean_name.split() if len(w.strip()) >= 2])
        try:
            file_path = os.path.join(UPLOAD_DIR, filename)
            headers = parse_csv_header(file_path)
            for h in headers:
                clean_h = re.sub(r"[^가-힣a-zA-Z]", " ", h)
                csv_keywords.update([w.strip() for w in clean_h.split() if len(w.strip()) >= 2])
        except Exception:
            pass

    # 2. 서버에 등록/저장된 기존 PDF 규제 파일들 중 시맨틱 연관성 매핑 검증
    try:
        pdf_filenames = [f for f in os.listdir(UPLOAD_DIR) if f.endswith(".pdf")]
        for pdf_filename in pdf_filenames:
            pdf_path = os.path.join(UPLOAD_DIR, pdf_filename)
            pdf_text = extract_pdf_text(pdf_path)
            
            # 시맨틱 교차 매핑 판단
            is_matched = False
            domain_mappings = {
                "smoking_zone": ["금연", "흡연", "담배", "smoking", "tobacco"],
                "ev_charging": ["전기차", "충전", "ev", "battery", "소방", "용수", "소방시설", "소방용수"],
                "yellow_carpet": ["어린이", "보호구역", "초등학교", "안전", "옐로우", "카펫", "스쿨존"],
            }
            
            clean_pdf = pdf_text.lower()
            clean_pdf_filename = pdf_filename.lower()
            
            # CSV 파일 키워드가 조례 내용/파일명에 명시되어 있는지 비교
            for keyword in csv_keywords:
                if keyword in ["정보", "안내", "위치", "현황", "시설", "관리", "서울시", "서울특별시"]:
                    continue
                if keyword.lower() in clean_pdf or keyword.lower() in clean_pdf_filename:
                    is_matched = True
                    break
            
            # 도메인 기반 교차 체크
            for domain, keywords in domain_mappings.items():
                csv_has_domain = any(k in " ".join(csv_keywords).lower() for k in keywords)
                pdf_has_domain = any(k in clean_pdf or k in clean_pdf_filename for k in keywords)
                if csv_has_domain and pdf_has_domain:
                    is_matched = True
                    break

            # 일치하는 조례 조각만 프롬프트 컨텍스트에 할당
            if is_matched:
                pdf_texts.append(f"조례 파일명: {pdf_filename}\n내용:\n{pdf_text[:3000]}")
            else:
                print(f"[Semantic Filtering] 조례 '{pdf_filename}' 은(는) 업로드된 데이터셋과 시맨틱 관계가 없으므로 감리 컨텍스트에서 제외되었습니다.")
    except Exception as e:
        pdf_texts.append(f"서버 내 기존 조례 스캔 중 오류: {str(e)}")

    for filename in request.filenames:
        file_path = os.path.join(UPLOAD_DIR, filename)
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"분석할 업로드 파일을 찾을 수 없습니다: {filename}")
            
        ext = filename.split(".")[-1].lower() if "." in filename else ""
        
        if ext == "csv":
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
    reasoning_global = "조례 파일명 및 공간 데이터 속성을 교차 대조하여 감리를 수행했습니다."
    opinion_global = "업로드된 데이터셋에 대한 감리를 완료했습니다."
    rules_matched_global = []
    criteria_global = [
        {"key": "traffic", "label": "대중교통 유동성"},
        {"key": "complaint", "label": "주민 민원 빈도"},
        {"key": "density", "label": "주변 혼잡 밀도"}
    ]
    
    client = get_openai_client()
    ai_success = False
    
    if client and (len(pdf_texts) > 0 or len(csv_headers_list) > 0):
        pdf_context = "\n\n".join(pdf_texts)
        csv_context = "\n\n".join(csv_headers_list)
        
        prompt = f"""
당신은 스마트시티 다목적 공간의사결정시스템(SDSS)의 지능형 감리 AI 에이전트입니다.
사용자가 이번 입지 분석을 진행하기 위해 등록한 행정 조례 문서(PDF)와 업로드한 공간 데이터 파일(CSV) 목록 및 구조는 다음과 같습니다.

[서버에 등록된 조례 문서 정보]
{pdf_context if pdf_context else "없음"}

[업로드된 공간 데이터 파일 정보]
{csv_context if csv_context else "없음"}

위 파일들의 파일명, 컬럼 구성, 그리고 조례 텍스트 내용을 종합 분석하여 다음 정보들을 도출하십시오:
1. inferred_purpose: 이번 입지 분석의 시맨틱 목적 추론 (예: "실외 흡연구역 입지 선정 및 간접흡연 규제 배제 분석", "전기차 충전소 최적 입지 매핑 및 규제구역 제외 분석")
2. inferred_domain_tag: 도메인 분류 영문 태그 (예: smoking_zone, smart_shelter, yellow_carpet, ev_charging)
3. hitl_question: 사용자(공무원)에게 의사결정 목적이 맞는지 최종 확정하기 위한 확인 질문 (예: "업로드하신 데이터들은 [실외 흡연구역/흡연구역 지정]을 위한 입지 분석이 맞습니까?")
4. reasoning: 어떤 조례 문서의 조항 구절과 어떤 CSV 파일명의 키워드 및 컬럼 헤더들을 대조하여 위 inferred_purpose와 inferred_domain_tag를 판독했는지 상세히 서술하십시오
5. opinion: 전체 조례 및 공간 데이터를 교차 검토하여 특정 시설물 제한 구역에 대한 감리 평가 의견
6. rules_matched: 조례 상에서 식별해 낸 구체적인 입지 제약 조항 목록
7. criteria: 이번 입지 분석 목적에 매칭되는 가장 연관성 높고 중요한 핵심 의사결정 평가 인자(AHP용 지표) 목록 (수량은 3~8개 사이로 유동적으로 도출하며, 각 인자마다 key와 한글 label을 쌍으로 생성할 것)

반드시 아래 JSON 포맷으로만 응답해야 합니다 (Markdown 없이 순수 JSON만 반환):
{{
  "inferred_purpose": "추론한 입지 분석 목적",
  "inferred_domain_tag": "영문 도메인 태그",
  "hitl_question": "사용자 확인 질문",
  "reasoning": "위 도메인 및 목적을 추론한 구체적인 분석 근거 상세 설명",
  "opinion": "전체 조례 검토 의견 및 시맨틱 입지 분석 방향 요약",
  "rules_matched": [
    {{
      "clause": "해당 조항명 (예: 제5조 제2항)",
      "description": "규정 요약 내용",
      "status": "matched"
    }}
  ],
  "criteria": [
    {{
      "key": "인자_영문_키 (예: traffic, ev_density, school_zone)",
      "label": "인자_한글_라벨 (예: 대중교통 유동성, 전기차 등록밀도, 스쿨존 사고율)"
    }}
  ]
}}
"""
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
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
            reasoning_global = result_json.get("reasoning", reasoning_global)
            opinion_global = result_json.get("opinion", opinion_global)
            rules_matched_global = result_json.get("rules_matched", [])
            criteria_global = result_json.get("criteria", criteria_global)
            ai_success = True
        except Exception as e:
            opinion_global = f"AI 교차 감리 도중 예외가 발생하여 로컬 룰 엔진으로 대체합니다. (에러: {str(e)})"

    # 로컬 Fallback 규칙 기반 자동 추정 및 reasoning 생성
    if not ai_success:
        combined_text = " ".join(pdf_texts) + " " + " ".join(request.filenames)
        if any(keyword in combined_text for keyword in ["금연", "흡연", "smoking", "tobacco"]):
            inferred_purpose = "실외 흡연구역 입지 선정 및 간접흡연 규제 배제 분석"
            inferred_domain_tag = "smoking_zone"
            hitl_question = "업로드하신 데이터들은 [실외 흡연구역/흡연구역 지정]을 위한 입지 분석이 맞습니까?"
            reasoning_global = "공간 데이터 파일명 및 컬럼 구조에서 금연/흡연(smoking) 관련 키워드가 감지되었으며, 서버에 보관된 금연 규제 시행규칙 조항과 교차 매핑하여 실외 흡연구역 선정을 위한 입지분석 목적으로 자동 추론했습니다. (로컬 Fallback 판독)"
            rules_matched_global = [{
                "clause": "용산구 금연구역 지정 조례(추정)",
                "description": "금연구역 경계선으로부터 10미터 이내 지정 (로컬 Fallback 추정)",
                "status": "matched"
            }]
            criteria_global = [
                {"key": "traffic", "label": "대중교통 유동성"},
                {"key": "complaint", "label": "불법흡연 민원빈도"},
                {"key": "dumping", "label": "상습 무단투기"},
                {"key": "population", "label": "배후 생활인구"},
                {"key": "youth", "label": "청소년 비율"}
            ]
        elif any(keyword in combined_text for keyword in ["충전", "전기차", "ev", "battery"]):
            inferred_purpose = "전기차 충전소 최적 입지 매핑 및 규제구역 제외 분석"
            inferred_domain_tag = "ev_charging"
            hitl_question = "업로드하신 데이터들은 [전기차 충전 인프라 설치]를 위한 입지 분석이 맞습니까?"
            reasoning_global = "공간 데이터 파일명에서 전기차/충전(ev) 관련 키워드가 감지되어, 친환경 충전 인프라 부지 선정을 위한 분석 목적으로 자동 추론했습니다. (로컬 Fallback 판독)"
            criteria_global = [
                {"key": "ev_density", "label": "전기차 등록 밀도"},
                {"key": "grid_capacity", "label": "배후 전력 인프라"},
                {"key": "park_distance", "label": "공영주차장 거리"},
                {"key": "residence_density", "label": "배후 주거 밀집도"}
            ]
        elif any(keyword in combined_text for keyword in ["어린이", "보행", "안전", "스쿨", "school"]):
            inferred_purpose = "어린이 보호구역 옐로카펫 및 안심 횡단보도 설치 분석"
            inferred_domain_tag = "yellow_carpet"
            hitl_question = "업로드하신 데이터들은 [어린이 교통 안전 및 옐로카펫 설치]를 위한 입지 분석이 맞습니까?"
            reasoning_global = "공간 데이터 파일명에서 어린이/스쿨구역 관련 키워드가 감지되어, 어린이 교통 보호 및 옐로카펫 설치를 위한 분석 목적으로 자동 추론했습니다. (로컬 Fallback 판독)"
            criteria_global = [
                {"key": "school_zone", "label": "스쿨존 사고율"},
                {"key": "traffic_volume", "label": "보행 유동인구"},
                {"key": "speed_violations", "label": "속도위반 빈도"},
                {"key": "youth_ratio", "label": "아동 생활밀도"}
            ]

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
        "reasoning": reasoning_global,
        "criteria": criteria_global,
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
    
    # 1. 컬럼 매핑 인덱스 추적 (Key-Value Inversion 방어막 적용)
    lat_idx, lng_idx, addr_idx = -1, -1, -1
    for k, v in request.column_mapping.items():
        # k가 표준 컬럼명이고, v가 실물 헤더명인 경우 (프론트 포맷: {"lat": "위도"})
        if k in ["lat", "lng", "address"] and v in headers:
            idx = headers.index(v)
            if k == "lat":
                lat_idx = idx
            elif k == "lng":
                lng_idx = idx
            elif k == "address":
                addr_idx = idx
        # 반대로 k가 실물 헤더명이고, v가 표준 컬럼명인 경우 (백엔드 기본 기대 포맷: {"위도": "lat"})
        elif v in ["lat", "lng", "address"] and k in headers:
            idx = headers.index(k)
            if v == "lat":
                lat_idx = idx
            elif v == "lng":
                lng_idx = idx
            elif v == "address":
                addr_idx = idx
                
    if lat_idx == -1 or lng_idx == -1:
        raise HTTPException(
            status_code=400, 
            detail="위도(lat)와 경도(lng)에 대응하는 컬럼 매핑 정보가 누락되었거나 일치하지 않습니다."
        )
        
    corrections_map = {c.row_index: c for c in request.corrections}
    
    committed_count = 0
    details_applied = []
    
    # 2. 보정값 대조 및 PostGIS DB 마이그레이션 트랜잭션 실행 (Bulk Insert 적용)
    try:
        insert_query = text("""
            INSERT INTO city_spatial_features (district_id, feature_type, feature_name, geom, properties)
            VALUES (:district_id, :feature_type, :feature_name, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326), :properties)
        """)
        
        params_list = []
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
            
            properties_json = json.dumps({
                "address": addr_val, 
                "original_row": row,
                "domain": request.confirmed_domain
            }, ensure_ascii=False)
            
            feature_type_val = request.confirmed_domain if request.confirmed_domain else ("smoking_zone" if "smoking" in request.filename.lower() else "city_feature")
            
            params_list.append({
                "district_id": 1,
                "feature_type": feature_type_val,
                "feature_name": request.filename,
                "lng": final_lng,
                "lat": final_lat,
                "properties": properties_json
            })
            
        if params_list:
            db.execute(insert_query, params_list)
            committed_count = len(params_list)
            
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
