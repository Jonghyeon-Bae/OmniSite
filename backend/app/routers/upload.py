import os
import csv
import re
import json
import joblib
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from pypdf import PdfReader
from openai import OpenAI, AsyncOpenAI
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.config import settings
from app.database import get_db
from app.utils.auth import get_current_admin
import pandas as pd
from app.database import engine
import shapefile
from shapely.geometry import shape

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

def get_async_openai_client() -> Optional[AsyncOpenAI]:
    if settings.OPENAI_API_KEY:
        try:
            return AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        except Exception:
            return None
    return None

def get_embedding(text_input: str) -> Optional[List[float]]:
    client = get_openai_client()
    if not client:
        return None
    try:
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=text_input
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"[Embedding Error] {e}")
        return None

def detect_csv_encoding(file_path: str) -> str:
    encodings = ["utf-8", "cp949", "utf-8-sig"]
    for enc in encodings:
        try:
            with open(file_path, "r", encoding=enc) as f:
                reader = csv.reader(f)
                next(reader, None)
                return enc
        except (UnicodeDecodeError, PermissionError):
            continue
    return "utf-8"

# CSV 파일 첫 라인(헤더)만 스트리밍하는 경량 헬퍼
def parse_csv_header(file_path: str) -> List[str]:
    correct_enc = detect_csv_encoding(file_path)
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
        "lat": ["lat", "latitude", "위도", "y", "y좌표", "y_coordinate", "위도좌표", "좌표y"],
        "lng": ["lng", "longitude", "경도", "x", "x좌표", "x_coordinate", "경도좌표", "좌표x"],
        "pnu": ["pnu", "pnu_code", "필지고유번호", "지적코드", "고유번호", "지번코드"],
        "address": ["address", "addr", "주소", "지번", "location", "소재지", "위치", "도로명주소"]
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
    correct_enc = detect_csv_encoding(file_path)
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
        "lat": ["lat", "latitude", "위도", "y", "y좌표", "y_coordinate", "위도좌표", "좌표y"],
        "lng": ["lng", "longitude", "경도", "x", "x좌표", "x_coordinate", "경도좌표", "좌표x"],
        "pnu": ["pnu", "pnu_code", "필지고유번호", "지적코드", "고유번호", "지번코드"],
        "address": ["address", "addr", "주소", "지번", "location", "소재지", "위치", "도로명주소"]
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

# PDF 청킹 및 OpenAI text-embedding-3-small 임베딩을 통한 district_regulations 벡터 테이블 적재 헬퍼
def chunk_and_embed_pdf(file_path: str, filename: str, db: Session, district_id: int = 1):
    text_content = extract_pdf_text(file_path)
    if not text_content:
        return
    
    chunk_size = 1000
    overlap = 200
    chunks = []
    
    start = 0
    while start < len(text_content):
        end = start + chunk_size
        chunks.append(text_content[start:end])
        start += chunk_size - overlap
        
    client = get_openai_client()
    if not client:
        print("[Warning] OpenAI client is not initialized. Skipping embedding for RAG database.")
        return
        
    for idx, chunk in enumerate(chunks):
        try:
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=chunk
            )
            embedding = response.data[0].embedding
            
            query = text("""
                INSERT INTO district_regulations (district_id, regulation_title, clause_number, content, embedding, category)
                VALUES (:district_id, :regulation_title, :clause_number, :content, :embedding, :category)
            """)
            db.execute(query, {
                "district_id": district_id,
                "regulation_title": filename,
                "clause_number": f"청크 {idx+1}",
                "content": chunk,
                "embedding": embedding,
                "category": "health_sanitation"
            })
        except Exception as e:
            print(f"[Error] Failed to embed chunk {idx} of {filename}: {e}")
            
    db.commit()

# 도메인 태그 유사도 기반 중복 방지 및 병합 헬퍼
def get_or_create_merged_tag(domain_tag: str, reasoning: str, db: Session) -> str:
    client = get_openai_client()
    if not client:
        return domain_tag
        
    try:
        embed_res = client.embeddings.create(
            model="text-embedding-3-small",
            input=domain_tag
        )
        tag_embedding = embed_res.data[0].embedding
        
        query = text("""
            SELECT tag_name, 1 - (embedding <=> CAST(:tag_embedding AS vector)) AS similarity 
            FROM registered_domain_tags 
            ORDER BY similarity DESC 
            LIMIT 1
        """)
        result = db.execute(query, {"tag_embedding": tag_embedding}).fetchone()
        
        if result:
            matched_tag, similarity = result
            print(f"[Semantic Tag Merger] Matched: {matched_tag} with similarity {similarity}")
            if similarity >= 0.85:
                print(f"[Semantic Tag Merger] Merged domain tag '{domain_tag}' into representative tag '{matched_tag}'")
                return matched_tag
                
        print(f"[Semantic Tag Merger] Creating new domain tag '{domain_tag}'")
        insert_query = text("""
            INSERT INTO registered_domain_tags (tag_name, tag_description, embedding)
            VALUES (:tag_name, :tag_description, :embedding)
            ON CONFLICT (tag_name) DO NOTHING
        """)
        db.execute(insert_query, {
            "tag_name": domain_tag,
            "tag_description": reasoning[:200] if reasoning else "AI 감리가 도출한 도메인",
            "embedding": tag_embedding
        })
        db.commit()
        return domain_tag
    except Exception as e:
        print(f"[Semantic Tag Merger Error] {e}")
        return domain_tag


# RAG 임베딩 매핑 실패 시 로컬 디렉터리 내 PDF 문서 시맨틱 키워드 매칭 수행용 Fallback 헬퍼
def fallback_pdf_matching(upload_dir: str, csv_keywords: set, pdf_texts: list):
    try:
        pdf_filenames = [f for f in os.listdir(upload_dir) if f.endswith(".pdf")]
        for pdf_filename in pdf_filenames:
            pdf_path = os.path.join(upload_dir, pdf_filename)
            pdf_text = extract_pdf_text(pdf_path)
            
            is_matched = False
            domain_mappings = {
                "smoking_zone": ["금연", "흡연", "담배", "smoking", "tobacco"],
                "ev_charging": ["전기차", "충전", "ev", "battery", "소방", "용수", "소방시설", "소방용수"],
                "yellow_carpet": ["어린이", "보호구역", "초등학교", "안전", "옐로우", "카펫", "스쿨존"],
            }
            clean_pdf = pdf_text.lower()
            clean_pdf_filename = pdf_filename.lower()
            
            for keyword in csv_keywords:
                if keyword in ["정보", "안내", "위치", "현황", "시설", "관리", "서울시", "서울특별시"]:
                    continue
                if keyword.lower() in clean_pdf or keyword.lower() in clean_pdf_filename:
                    is_matched = True
                    break
            
            for domain, keywords in domain_mappings.items():
                csv_has_domain = any(k in " ".join(csv_keywords).lower() for k in keywords)
                pdf_has_domain = any(k in clean_pdf or k in clean_pdf_filename for k in keywords)
                if csv_has_domain and pdf_has_domain:
                    is_matched = True
                    break

            if is_matched:
                pdf_texts.append(f"조례 파일명: {pdf_filename}\n내용:\n{pdf_text[:3000]}")
    except Exception as e:
        pdf_texts.append(f"서버 내 기존 조례 스캔 중 오류: {str(e)}")

# Pydantic 데이터 모델 정의
class AuditRequest(BaseModel):
    filenames: List[str]

class CoordinateCorrection(BaseModel):
    row_index: int
    lat: float
    lng: float

class HITLCommitRequest(BaseModel):
    filename: str
    target_file: Optional[str] = None
    column_mapping: Dict[str, str]
    corrections: List[CoordinateCorrection]
    confirmed_domain: Optional[str] = None
    file_behaviors: Optional[Dict[str, str]] = None
    spatial_restrictions: Optional[Dict[str, float]] = None
    score_modifiers: Optional[List[Dict]] = None

# PM 개발 철칙 2조 준수: 반드시 비동기 API(async def) 적용
# 조례/시행규칙 규정 문서 등록 API
@router.post("/upload/regulation")
async def upload_regulation_files(files: List[UploadFile] = File(...), db: Session = Depends(get_db), current_admin: dict = Depends(get_current_admin)):
    uploaded_info = []

    for file in files:
        filename = file.filename
        try:
            filename = filename.encode('latin-1').decode('utf-8')
        except Exception:
            pass
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

        # PDF일 경우 텍스트를 추출하여 pgvector DB에 적재
        if ext == "pdf":
            try:
                chunk_and_embed_pdf(saved_path, filename, db)
            except Exception as e:
                print(f"[PDF RAG Error] {e}")

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
async def delete_regulation(filename: str, current_admin: dict = Depends(get_current_admin)):
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
        try:
            filename = filename.encode('latin-1').decode('utf-8')
        except Exception:
            pass
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
async def audit_upload_files(request: AuditRequest, db: Session = Depends(get_db)):
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

    # 2. pgvector 기반 RAG 조례 매핑 (pre-filtering: district_id=1, similarity >= 0.40)
    client = get_openai_client()
    rag_applied = False
    if client and len(csv_keywords) > 0:
        query_str = " ".join(list(csv_keywords)[:15])
        try:
            embed_res = client.embeddings.create(
                model="text-embedding-3-small",
                input=query_str
            )
            query_embedding = embed_res.data[0].embedding
            
            rag_query = text("""
                SELECT regulation_title, content, 1 - (embedding <=> CAST(:query_embedding AS vector)) AS similarity
                FROM district_regulations
                WHERE district_id = 1 AND 1 - (embedding <=> CAST(:query_embedding AS vector)) >= 0.40
                ORDER BY similarity DESC
                LIMIT 5
            """)
            rag_results = db.execute(rag_query, {"query_embedding": query_embedding}).fetchall()
            
            if rag_results:
                rag_applied = True
                for row in rag_results:
                    title, content, similarity = row
                    print(f"[pgvector RAG] Matched regulation '{title}' with similarity {similarity:.4f}")
                    pdf_texts.append(f"조례 파일명: {title}\n내용:\n{content}")
        except Exception as e:
            print(f"[pgvector RAG Error] {e}")

    if not rag_applied:
        # Fallback: 로컬 디렉터리 PDF 키워드 매칭
        fallback_pdf_matching(UPLOAD_DIR, csv_keywords, pdf_texts)

    for filename in request.filenames:
        file_path = os.path.join(UPLOAD_DIR, filename)
        if not os.path.exists(file_path):
            csv_results_dict[filename] = {
                "headers": [],
                "detected_mapping": {},
                "schema_errors": [{"column": "FILE", "suggested": filename, "reason": "업로드 파일 실물이 존재하지 않거나 처리 중 유실되었습니다."}],
                "missing_coordinates": [],
                "status": "warning",
                "error_msg": f"분석할 업로드 파일을 찾을 수 없습니다: {filename}"
            }
            csv_headers_list.append(f"파일명: {filename}\n상태: 실물 파일 부재 경고")
            continue
            
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
    
    # Fallback criteria matching helper
    def find_fallback_file(key_keywords):
        for f in request.filenames:
            if f.endswith(".csv") and any(kw in f.lower() for kw in key_keywords):
                return f
        return None

    criteria_global = [
        {"key": "traffic", "label": "대중교통 유동성", "associated_file": find_fallback_file(["버스", "정류소", "지하철", "교통", "station", "bus", "subway", "transit"])},
        {"key": "complaint", "label": "주민 민원 빈도", "associated_file": find_fallback_file(["민원", "complaint"])},
        {"key": "density", "label": "주변 혼잡 밀도", "associated_file": None}
    ]
    spatial_restrictions_global = {}
    file_behaviors_global = {}
    score_modifiers_global = []
    
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
7. criteria: 이번 입지 분석 목적에 매칭되는 가장 연관성 높고 중요한 핵심 의사결정 평가 인자(AHP용 지표) 목록 (수량은 3~8개 사이로 유동적으로 도출하며, 각 인자마다 key, 한글 label, 그리고 이번에 업로드된 CSV 파일 목록 중 해당 인자와 가장 연관성이 높은 파일명을 'associated_file' 필드로 반드시 매칭하십시오. 만약 업로드된 파일 중에 매칭되는 데이터가 없다면 null로 비워두십시오.)
8. spatial_restrictions: 조례 규정에서 발견된 이격거리 규제 사양 (예: 지하철역 주변 10m 혹은 어린이집 경계 30m 등). 특히 학교(school), 어린이집(childcare_center), 금연구역(nosmoking_zone)이 있다면 조례 텍스트의 규정이나 시행령/조례 최소치를 판독해 미터 숫자값 딕셔너리로 반환하십시오. 단, 학교의 경우 법령상 절대 금지되는 최소치(절대보호구역)인 50미터(school: 50.0)를 우선 추출하십시오.
9. file_behaviors: 업로드된 각 CSV 파일이 이번 도메인 분석 목적(inferred_domain_tag) 하에서 법적/행정적 설치 금지 구역에 해당하는지("exclusion"), 아니면 단순 설치 허용/가용/권장 주차장이나 교통 노드 정보 등에 해당하는지("inclusion") 조례(RAG)를 바탕으로 판정하십시오. 파일명을 키로 하고 "exclusion" 또는 "inclusion"을 값으로 하는 객체로 반환하십시오.
10. score_modifiers: 분석용 데이터셋의 컬럼값 또는 조례 규정에서 발견된 입지 선정 시의 특정 토지 지목이나 위치적 이점에 따른 점수 가/감점 사양을 추출하십시오. (예: 지목이 도로 '도' 이면 한전 협의 리스크로 -4.0 감점, 지목이 주차장 '차' 이거나 공원 '공' 이면 연계 편의성으로 +6.0 가점, 또는 편의점 인접 시 +5.0 가점 등). 이 가/감점 룰 리스트를 'score_modifiers' 객체 배열로 반환하십시오.

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
      "label": "인자_한글_라벨 (예: 대중교통 유동성, 전기차 등록밀도, 스쿨존 사고율)",
      "associated_file": "매칭되는 업로드 CSV 파일명 (예: 00. 버스정류소 위치.csv) 또는 null"
    }}
  ],
  "spatial_restrictions": {{
    "school": 50.0,
    "childcare_center": 30.0,
    "nosmoking_zone": 10.0
  }},
  "file_behaviors": {{
    "파일명1.csv": "exclusion",
    "파일명2.csv": "inclusion"
  }},
  "score_modifiers": [
    {{
      "target": "land_use_code",
      "operator": "IN",
      "values": ["도"],
      "points": -4.0,
      "reason": "도로 부지 사용 시 한전 배전 용량 협의 리스크 감점"
    }},
    {{
      "target": "land_use_code",
      "operator": "IN",
      "values": ["차", "공"],
      "points": 6.0,
      "reason": "공영주차장 및 공원 부지 연계 편의성 가점"
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
            reasoning_global = result_json.get("reasoning", reasoning_global)
            opinion_global = result_json.get("opinion", opinion_global)
            rules_matched_global = result_json.get("rules_matched", [])
            criteria_global = result_json.get("criteria", criteria_global)
            spatial_restrictions_global = result_json.get("spatial_restrictions", {})
            file_behaviors_global = result_json.get("file_behaviors", {})
            score_modifiers_global = result_json.get("score_modifiers", [])
            
            # 도메인 태그 유사도 기반 중복 방지 및 병합 엔진 적용
            inferred_domain_tag = get_or_create_merged_tag(inferred_domain_tag, reasoning_global, db)
            
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
                {"key": "traffic", "label": "대중교통 유동성", "associated_file": find_fallback_file(["버스", "정류소", "지하철", "교통", "station", "bus", "subway", "transit"])},
                {"key": "complaint", "label": "불법흡연 민원빈도", "associated_file": find_fallback_file(["민원", "complaint"])},
                {"key": "dumping", "label": "상습 무단투기", "associated_file": find_fallback_file(["무단투기", "dumping", "쓰레기", "trash", "garbage"])},
                {"key": "population", "label": "배후 생활인구", "associated_file": find_fallback_file(["생활인구", "인구", "people", "population"])},
                {"key": "youth", "label": "청소년 비율", "associated_file": find_fallback_file(["연령", "청소년", "연령대", "demographics", "age", "youth"])}
            ]
            spatial_restrictions_global = {
                "transit_station": 10.0,
                "childcare_center": 30.0
            }
            score_modifiers_global = [
                {"target": "land_use_code", "operator": "IN", "values": ["도"], "points": -4.0, "reason": "도로 부지 사용 시 한전 배전 용량 협의 리스크 감점"},
        
                {"target": "land_use_code", "operator": "IN", "values": ["차", "공"], "points": 6.0, "reason": "공영주차장 및 공원 부지 연계 편의성 가점"}
            ]
            # 도메인 태그 유사도 기반 중복 방지 및 병합 엔진 적용 (Fallback)
            inferred_domain_tag = get_or_create_merged_tag(inferred_domain_tag, reasoning_global, db)
            
        elif any(keyword in combined_text for keyword in ["충전", "전기차", "ev", "battery"]):
            inferred_purpose = "전기차 충전소 최적 입지 매핑 및 규제구역 제외 분석"
            inferred_domain_tag = "ev_charging"
            hitl_question = "업로드하신 데이터들은 [전기차 충전 인프라 설치]를 위한 입지 분석이 맞습니까?"
            reasoning_global = "공간 데이터 파일명에서 전기차/충전(ev) 관련 키워드가 감지되어, 친환경 충전 인프라 부지 선정을 위한 분석 목적으로 자동 추론했습니다. (로컬 Fallback 판독)"
            criteria_global = [
                {"key": "ev_density", "label": "전기차 등록 밀도", "associated_file": find_fallback_file(["충전", "전기차", "ev", "battery"])},
                {"key": "grid_capacity", "label": "배후 전력 인프라", "associated_file": find_fallback_file(["전력", "그리드", "변전소", "grid", "capacity"])},
                {"key": "park_distance", "label": "공영주차장 거리", "associated_file": find_fallback_file(["주차장", "park"])},
                {"key": "residence_density", "label": "배후 주거 밀집도", "associated_file": find_fallback_file(["주거", "residence", "아파트", "apartment"])}
            ]
            score_modifiers_global = [
                {"target": "land_use_code", "operator": "IN", "values": ["도"], "points": -6.0, "reason": "도로 부지 사용 시 통행 장애 리스크 감점"},
                {"target": "land_use_code", "operator": "IN", "values": ["차"], "points": 8.0, "reason": "공영주차장 연계 고속 충전 효율성 가점"}
            ]
            # 도메인 태그 유사도 기반 중복 방지 및 병합 엔진 적용 (Fallback)
            inferred_domain_tag = get_or_create_merged_tag(inferred_domain_tag, reasoning_global, db)
            
        elif any(keyword in combined_text for keyword in ["어린이", "보행", "안전", "스쿨", "school"]):
            inferred_purpose = "어린이 보호구역 옐로카펫 및 안심 횡단보도 설치 분석"
            inferred_domain_tag = "yellow_carpet"
            hitl_question = "업로드하신 데이터들은 [어린이 교통 안전 및 옐로카펫 설치]를 위한 입지 분석이 맞습니까?"
            reasoning_global = "공간 데이터 파일명에서 어린이/스쿨구역 관련 키워드가 감지되어, 어린이 교통 보호 및 옐로카펫 설치를 위한 분석 목적으로 자동 추론했습니다. (로컬 Fallback 판독)"
            criteria_global = [
                {"key": "school_zone", "label": "스쿨존 사고율", "associated_file": find_fallback_file(["사고", "school", "보호구역", "스쿨존"])},
                {"key": "traffic_volume", "label": "보행 유동인구", "associated_file": find_fallback_file(["보행", "유동", "유동인구", "traffic", "volume"])},
                {"key": "speed_violations", "label": "속도위반 빈도", "associated_file": find_fallback_file(["위반", "속도", "speed", "violation"])},
                {"key": "youth_ratio", "label": "아동 생활밀도", "associated_file": find_fallback_file(["아동", "청소년", "어린이", "youth", "child"])}
            ]
            score_modifiers_global = []
            # 도메인 태그 유사도 기반 중복 방지 및 병합 엔진 적용 (Fallback)
            inferred_domain_tag = get_or_create_merged_tag(inferred_domain_tag, reasoning_global, db)

        elif any(keyword in combined_text for keyword in ["자전거", "따릉이", "대여소", "bicycle", "bike"]):
            inferred_purpose = "공용자전거 대여소(따릉이) 설치 및 라스트마일 연계 분석"
            inferred_domain_tag = "public_bicycle"
            hitl_question = "업로드하신 데이터들은 [공용자전거 대여소 설치]를 위한 입지 분석이 맞습니까?"
            reasoning_global = "공간 데이터 파일명에서 자전거/대여소(bicycle) 관련 키워드가 감지되어, 공공 대여 자전거 스테이션 부지 선정을 위한 분석 목적으로 자동 추론했습니다. (로컬 Fallback 판독)"
            criteria_global = [
                {"key": "bike_demand", "label": "자전거 대여 수요", "associated_file": find_fallback_file(["수요", "대여", "자전거", "따릉이", "demand", "bike"])},
                {"key": "transit_connection", "label": "대중교통 환승 유동성", "associated_file": find_fallback_file(["지하철", "버스", "정류소", "교통", "transit", "connection", "transfer"])},
                {"key": "bike_path_distance", "label": "기성 자전거도로 인접성", "associated_file": find_fallback_file(["도로", "자전거도로", "path", "route"])},
                {"key": "slope_index", "label": "지형 경사도 평탄화", "associated_file": find_fallback_file(["경사", "평탄", "slope", "elevation"])}
            ]
            score_modifiers_global = []
            # 도메인 태그 유사도 기반 중복 방지 및 병합 엔진 적용 (Fallback)
            inferred_domain_tag = get_or_create_merged_tag(inferred_domain_tag, reasoning_global, db)

    # AI가 누락했거나 Fallback인 경우 파일별 기본 성격 분류 (금지/불가능 단어 감지 시 exclusion)
    for f in request.filenames:
        if f not in file_behaviors_global:
            if any(k in f.lower() for k in ["금지", "불가능", "제한", "위험", "exclusion", "banned", "nosmoking"]):
                file_behaviors_global[f] = "exclusion"
            else:
                file_behaviors_global[f] = "inclusion"

    results = []
    for filename in request.filenames:
        ext = filename.split(".")[-1].lower() if "." in filename else ""
        
        if ext == "csv":
            meta = csv_results_dict.get(filename, {"schema_errors": [], "missing_coordinates": [], "status": "fail"})
            results.append({
                "filename": filename,
                "status": meta["status"],
                "score": 0.65 if meta["status"] in ["warning", "fail"] else 0.95,
                "opinion": meta.get("error_msg", f"공간 데이터 '{filename}' 스키마 및 좌표 무결성 검사 완료. 성격: {file_behaviors_global.get(filename, 'inclusion')}"),
                "schema_errors": meta.get("schema_errors", []),
                "missing_coordinates": meta.get("missing_coordinates", []),
                "column_mapping": meta.get("detected_mapping", {}),
                "headers": meta.get("headers", []),
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

    # --- [ML-to-AHP Slider Feature Fusion] XGBoost 피처 기여도 분석 및 AHP 슬라이더 가중치 초기화 동적 연동 ---
    def get_model_feature_importances(domain_tag: str) -> Dict[str, float]:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        registry_path = os.path.join(base_dir, "models", "registry")
        
        model_file = None
        if os.path.exists(registry_path):
            for file in os.listdir(registry_path):
                if file.endswith(".pkl") and file.startswith(domain_tag):
                    model_file = os.path.join(registry_path, file)
                    break
            if not model_file:
                for file in os.listdir(registry_path):
                    if file.endswith(".pkl") and file.startswith("city_feature"):
                        model_file = os.path.join(registry_path, file)
                        break
                        
        importances = {}
        if model_file and os.path.exists(model_file):
            try:
                pipeline = joblib.load(model_file)
                classifier = pipeline.named_steps.get('classifier')
                preprocessor = pipeline.named_steps.get('preprocessor')
                if classifier and hasattr(classifier, 'feature_importances_'):
                    numeric_features = ['area', 'dist_to_school', 'dist_to_childcare']
                    categorical_features = ['land_use_code', 'ownership_type']
                    
                    try:
                        onehot_cols = preprocessor.named_transformers_['cat'].named_steps['onehot'].get_feature_names_out(categorical_features)
                        feature_names = numeric_features + list(onehot_cols)
                    except Exception:
                        feature_names = numeric_features
                        
                    importances_raw = classifier.feature_importances_
                    for name, imp in zip(feature_names, importances_raw):
                        importances[name] = float(imp)
            except Exception as e:
                print(f"[Feature Importance Extract Fail] {e}")
        return importances

    importances_map = get_model_feature_importances(inferred_domain_tag)
    
    # 5대 지표별 기여도 매핑
    feature_mapping = {
        "traffic": importances_map.get("land_use_code_도", 0.0) + importances_map.get("land_use_code_ö", 0.0) + 0.1,
        "complaint": importances_map.get("dist_to_school", 0.0) * 0.4 + importances_map.get("dist_to_childcare", 0.0) * 0.4,
        "dumping": importances_map.get("land_use_code_대", 0.0) + importances_map.get("land_use_code_잡", 0.0) + 0.1,
        "population": importances_map.get("area", 0.0) + 0.1,
        "youth": importances_map.get("dist_to_school", 0.0) * 0.6 + importances_map.get("dist_to_childcare", 0.0) * 0.6
    }
    
    # 1.0 ~ 9.0 스케일 변환 및 criteria 아이템 바인딩
    for c_item in criteria_global:
        key = c_item.get("key")
        importance_weight = feature_mapping.get(key, 0.1)
        slider_initial = 3.0 + (importance_weight * 12.0)
        c_item["initial_weight"] = round(max(1.0, min(9.0, slider_initial)), 1)

    # [v4.9.34] AI 감리가 조례/법규 텍스트 매핑 분석을 통해 연관성 입증 성공 유무(rag_applied) 기준으로 동적 감지
    has_regulations = False
    if rag_applied is True or (isinstance(rules_matched_global, list) and len(rules_matched_global) > 0):
        has_regulations = True

    return {
        "message": "실물 기반 AI 시맨틱 감리 분석이 완료되었습니다.",
        "inferred_purpose": inferred_purpose,
        "inferred_domain_tag": inferred_domain_tag,
        "hitl_question": hitl_question,
        "reasoning": reasoning_global,
        "opinion": opinion_global,
        "rules_matched": rules_matched_global,
        "criteria": criteria_global,
        "spatial_restrictions": spatial_restrictions_global,
        "file_behaviors": file_behaviors_global,
        "score_modifiers": score_modifiers_global,
        "has_regulations": has_regulations,
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
    headers = [h.strip() for h in headers if h]
    
    # 1. 컬럼 매핑 인덱스 추적 (Key-Value Inversion 방어막 적용)
    lat_idx, lng_idx, addr_idx = -1, -1, -1
    print(f"[HITL Debug] Cleaned headers: {headers}")
    print(f"[HITL Debug] Received mapping: {request.column_mapping}")
    
    for k, v in request.column_mapping.items():
        k_clean = k.strip() if k else ""
        v_clean = v.strip() if v else ""
        
        if k_clean in ["lat", "lng", "address"] and v_clean in headers:
            idx = headers.index(v_clean)
            if k_clean == "lat":
                lat_idx = idx
            elif k_clean == "lng":
                lng_idx = idx
            elif k_clean == "address":
                addr_idx = idx
        elif v_clean in ["lat", "lng", "address"] and k_clean in headers:
            idx = headers.index(k_clean)
            if v_clean == "lat":
                lat_idx = idx
            elif v_clean == "lng":
                lng_idx = idx
            elif v_clean == "address":
                addr_idx = idx
                
    print(f"[HITL Debug] Resolved indices -> lat_idx: {lat_idx}, lng_idx: {lng_idx}, addr_idx: {addr_idx}")
    if lat_idx == -1 or lng_idx == -1:
        raise HTTPException(
            status_code=400, 
            detail=f"위도(lat)와 경도(lng)에 대응하는 컬럼 매핑 정보가 누락되었거나 일치하지 않습니다. (Resolved: lat={lat_idx}, lng={lng_idx}, Headers={headers}, Mapping={request.column_mapping})"
        )
        
    corrections_map = {c.row_index: c for c in request.corrections}
    
    committed_count = 0
    details_applied = []
    
    # 2. 행정동 WKT 폴리곤 데이터 조회 및 Shapely contains 연산기 구성
    try:
        dongs = db.execute(text("SELECT id, ST_AsText(geom) FROM dong_boundaries WHERE district_id = 1")).fetchall()
        from shapely.wkt import loads
        from shapely.geometry import Point
        
        dong_polys = []
        for d_id, wkt in dongs:
            try:
                dong_polys.append((d_id, loads(wkt)))
            except Exception:
                pass
                
        def find_dong_id(lng: float, lat: float) -> int:
            p = Point(lng, lat)
            for d_id, poly in dong_polys:
                if poly.contains(p):
                    return d_id
            return 1  # 기본값
            
        json_records = []
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
            
            row_dict = {headers[i]: row[i] for i in range(min(len(headers), len(row)))}
            zone_behavior = request.file_behaviors.get(request.filename, "inclusion") if request.file_behaviors else "inclusion"
            is_exclusion = (zone_behavior == "exclusion")
            
            properties_dict = {
                "address": addr_val, 
                "data": row_dict,
                "domain": request.confirmed_domain,
                "zone_behavior": zone_behavior,
                "is_exclusion": is_exclusion
            }
            
            dong_id_val = find_dong_id(final_lng, final_lat)
            
            json_records.append({
                "lat": final_lat,
                "lng": final_lng,
                "dong_id": dong_id_val,
                "properties": properties_dict
            })
            
        if json_records:
            json_filename = request.filename.replace(".csv", ".json")
            json_path = os.path.join(UPLOAD_DIR, json_filename)
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(json_records, f, ensure_ascii=False, indent=2)
            committed_count += len(json_records)

        # UPLOAD_DIR 내 다른 모든 CSV 파일들도 자동 커밋 처리 진행
        committed_files = [request.filename]
        other_files = [f for f in os.listdir(UPLOAD_DIR) if f.endswith(".csv") and f != request.filename]
        
        for other_file in other_files:
            other_path = os.path.join(UPLOAD_DIR, other_file)
            try:
                o_headers, o_rows = parse_csv_file(other_path)
                o_mapping, o_errors = analyze_csv_header_only(o_headers)
                
                o_lat_col = o_mapping.get("lat")
                o_lng_col = o_mapping.get("lng")
                o_addr_col = o_mapping.get("address")
                
                if not o_lat_col or not o_lng_col:
                    continue
                    
                o_lat_idx = o_headers.index(o_lat_col)
                o_lng_idx = o_headers.index(o_lng_col)
                o_addr_idx = o_headers.index(o_addr_col) if o_addr_col else -1
                
                o_records = []
                for idx, r in enumerate(o_rows):
                    if len(r) <= max(o_lat_idx, o_lng_idx):
                        continue
                    try:
                        final_lat = float(r[o_lat_idx])
                        final_lng = float(r[o_lng_idx])
                    except ValueError:
                        continue
                        
                    if not (33.0 <= final_lat <= 39.0 and 124.0 <= final_lng <= 132.0):
                        continue
                        
                    addr_val = r[o_addr_idx] if o_addr_idx != -1 and o_addr_idx < len(r) else f"행 번호 {idx+1}"
                    
                    row_dict = {o_headers[i]: r[i] for i in range(min(len(o_headers), len(r)))}
                    other_zone_behavior = "inclusion"
                    if request.file_behaviors and other_file in request.file_behaviors:
                        other_zone_behavior = request.file_behaviors[other_file]
                    else:
                        if any(k in other_file.lower() for k in ["금지", "불가능", "제한", "위험", "exclusion", "banned", "nosmoking"]):
                            other_zone_behavior = "exclusion"
                    other_is_exclusion = (other_zone_behavior == "exclusion")
                    
                    properties_dict = {
                        "address": addr_val,
                        "data": row_dict,
                        "domain": request.confirmed_domain,
                        "zone_behavior": other_zone_behavior,
                        "is_exclusion": other_is_exclusion
                    }
                    
                    dong_id_val = find_dong_id(final_lng, final_lat)
                    
                    o_records.append({
                        "lat": final_lat,
                        "lng": final_lng,
                        "dong_id": dong_id_val,
                        "properties": properties_dict
                    })
                    
                if o_records:
                    o_json_filename = other_file.replace(".csv", ".json")
                    o_json_path = os.path.join(UPLOAD_DIR, o_json_filename)
                    with open(o_json_path, "w", encoding="utf-8") as f:
                        json.dump(o_records, f, ensure_ascii=False, indent=2)
                    committed_count += len(o_records)
                    committed_files.append(other_file)
            except Exception as ex:
                print(f"[Auto Commit Error] Failed to process other file {other_file}: {ex}")
                
        # [v4.4.3] AI RAG/HITL로부터 도출된 이격거리 규격이 존재하는 경우 DB domain_regulation_rules 에 upsert
        spatial_rules = request.spatial_restrictions
        if not spatial_rules:
            # 넘어온 게 없으면 디폴트 규칙값 구성 (school=50m, childcare=30m, nosmoking=10m)
            if request.confirmed_domain == "smoking_zone":
                spatial_rules = {"school": 50.0, "childcare_center": 30.0, "nosmoking_zone": 10.0}
            elif request.confirmed_domain == "ev_charging":
                spatial_rules = {"school": 100.0, "childcare_center": 30.0}
            else:
                spatial_rules = {"school": 50.0, "childcare_center": 30.0, "nosmoking_zone": 10.0}

        if request.confirmed_domain and spatial_rules:
            try:
                upsert_query = text("""
                    INSERT INTO domain_regulation_rules (facility_type, rules_json, rules_metadata, updated_at)
                    VALUES (:facility_type, :rules_json, :rules_metadata, CURRENT_TIMESTAMP)
                    ON CONFLICT (facility_type) 
                    DO UPDATE SET rules_json = EXCLUDED.rules_json, rules_metadata = EXCLUDED.rules_metadata, updated_at = CURRENT_TIMESTAMP
                """)
                db.execute(upsert_query, {
                    "facility_type": request.confirmed_domain,
                    "rules_json": json.dumps(spatial_rules),
                    "rules_metadata": json.dumps(request.score_modifiers if request.score_modifiers else [])
                })
                db.commit()
                print(f"[Regulation Rules Persistent Save] Saved rules & modifiers for '{request.confirmed_domain}': {spatial_rules}")
                
                # [v4.9.31] 사용자가 Step 1에서 업로드한 최신 규제 좌표 목록을 restricted_zones DB 테이블에 1:1 전적 실시간 동기화 (오추천 원천 소멸)
                try:
                    db.execute(text("DELETE FROM restricted_zones WHERE zone_type = :zone_type"), {"zone_type": request.confirmed_domain})
                    db.commit()
                    
                    target_json_filename = request.target_file.replace(".csv", ".json")
                    target_json_path = os.path.join(UPLOAD_DIR, target_json_filename)
                    if os.path.exists(target_json_path):
                        with open(target_json_path, "r", encoding="utf-8") as f_json:
                            records = json.load(f_json)
                            inserted_count = 0
                            for r in records:
                                props = r.get("properties", {})
                                item_domain = props.get("domain")
                                
                                # 제외(is_exclusion) 속성이거나 타겟 도메인 규격에 해당하는 레코드일 때 restricted_zones 에 1:1 실시간 인서트
                                if props.get("is_exclusion") is True or request.confirmed_domain in ["school", "childcare_center", "nosmoking_zone"] or item_domain in ["school", "childcare_center", "nosmoking_zone"]:
                                    # domain_type 확정
                                    dtype = item_domain if item_domain else request.confirmed_domain
                                    db.execute(text("""
                                        INSERT INTO restricted_zones (district_id, zone_type, geom, created_at)
                                        VALUES (1, :zone_type, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326), CURRENT_TIMESTAMP)
                                    """), {
                                        "zone_type": dtype,
                                        "lng": float(r["lng"]),
                                        "lat": float(r["lat"])
                                    })
                                    inserted_count += 1
                            db.commit()
                            print(f"[Restricted Zones Sync] Successfully synchronized {inserted_count} records from upload cache to DB restricted_zones.")
                except Exception as sync_ex:
                    db.rollback()
                    print(f"[Restricted Zones Sync Error] {sync_ex}")
                
                # [v4.9.27] 자동 감리 불가 구역(지하/고가/철도/블랙리스트) 가상 금역 생성기 기동
                try:
                    db.execute(text("DELETE FROM user_exclusion_zones WHERE memo = '[시스템 자동 감리] 물리적 장애물 배제 영역 (지하/고가/철도)'"))
                    auto_gen_query = text("""
                        INSERT INTO user_exclusion_zones (zone_name, geom, memo, created_at)
                        SELECT 
                            '자동 감리 금지 구역' as zone_name,
                            geom,
                            '[시스템 자동 감리] 물리적 장애물 배제 영역 (지하/고가/철도)' as memo,
                            CURRENT_TIMESTAMP as created_at
                        FROM cadastral_lands
                        WHERE district_id = 1
                          AND (
                              land_use_code = '철' OR
                              (land_use_code = '도' AND (
                                  jibun LIKE '%%지하%%' OR 
                                  jibun LIKE '%%고가%%' OR 
                                  jibun LIKE '%%터널%%' OR
                                  jibun LIKE '%%한강로3가 2-14%%'
                              ))
                          )
                        LIMIT 100
                    """)
                    db.execute(auto_gen_query)
                    db.commit()
                    print("[Auto Exclusion Zone Generator] Successfully populated system barrier exclusion zones.")
                except Exception as auto_ex_err:
                    db.rollback()
                    print(f"[Auto Exclusion Zone Generator Error] {auto_ex_err}")
                    
            except Exception as dberr:
                print(f"[Regulation Rules Persistent Save Error] {dberr}")
                
        # [v4.9.21 핫픽스] 0개 예외 및 Step 2 복귀 재보정 커밋을 다회 가능하도록 원본 CSV 물리 삭제 임시 유예
        # for cf in committed_files:
        #     try:
        #         os.remove(os.path.join(UPLOAD_DIR, cf))
        #     except Exception as e:
        #         print(f"[Cleanup Error] Failed to remove committed file {cf}: {e}")
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"공간 데이터 캐시 파일 컴파일 중 오류 발생: {str(e)}")
        
    return {
        "status": "success",
        "message": f"성공적으로 {len(committed_files)}개 공간 데이터셋의 보정이 완료되었으며, 총 {committed_count}건의 공간 레코드가 로컬 캐시(JSON)에 격리 적재되었습니다.",
        "committed_records": committed_count,
        "committed_files": committed_files,
        "details": {
            "mapped_columns": request.column_mapping,
            "applied_corrections": details_applied
        }
    }

# --- [Step 1-0] 캐시 파일 일괄 제거 API ---
@router.post("/upload/clear")
async def clear_uploaded_caches(db: Session = Depends(get_db), current_admin: dict = Depends(get_current_admin)):
    try:
        purged_files = []
        if os.path.exists(UPLOAD_DIR):
            for f in os.listdir(UPLOAD_DIR):
                # .json 및 .csv, .txt 파일들만 타깃으로 청소 (.gitkeep 등 제외)
                if f.endswith((".json", ".csv", ".txt")):
                    file_path = os.path.join(UPLOAD_DIR, f)
                    try:
                        os.remove(file_path)
                        purged_files.append(f)
                    except Exception:
                        pass
        
        # 메모리 캐시 초기화
        from app.routers.spatial import _file_cache
        _file_cache.clear()

        # v4.4.1 사용자 정의 금지구역 테이블 및 v4.4.3 규제 라이브러리 초기화 연동 (Mock 데이터 소거)
        try:
            # [v4.9.27] 가상작도 금지구역 보존을 위해 TRUNCATE user_exclusion_zones 제거
            # db.execute(text("TRUNCATE TABLE user_exclusion_zones RESTART IDENTITY CASCADE"))
            db.execute(text("TRUNCATE TABLE domain_regulation_rules RESTART IDENTITY CASCADE"))
            db.commit()
        except Exception as db_ex:
            db.rollback()
            print(f"[DB Clear Error] user_exclusion_zones/domain_regulation_rules: {db_ex}")
        
        return {
            "status": "success",
            "message": f"성공적으로 {len(purged_files)}개의 임시 공간 데이터/캐시 파일, 메모리 캐시 및 사용자 지정 금역 테이블을 초기화(Clear)했습니다.",
            "purged_files": purged_files
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"임시 캐시 초기화 중 오류 발생: {str(e)}")

# --- [Phase 2] 관리자 전용 원천 공간/행정 데이터 벌크 적재 API ---
class SeedSpatialRequest(BaseModel):
    target_table: str
    if_exists: Optional[str] = "append" # "append" or "replace"

@router.post("/upload/seed-spatial")
async def seed_spatial_data(
    target_table: str,
    if_exists: Optional[str] = "append",
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    # 1. 허용 테이블 화이트리스트 검사 (SQL Injection 예방)
    allowed_tables = [
        "cadastral_lands",
        "civil_complaints",
        "commercial_shops",
        "district_regulations",
        "registered_domain_tags",
        "user_exclusion_zones"
    ]
    if target_table not in allowed_tables:
        raise HTTPException(
            status_code=400,
            detail=f"허용되지 않은 적재 테이블명입니다. 허용군: {allowed_tables}"
        )
        
    filename = file.filename
    try:
        filename = filename.encode('latin-1').decode('utf-8')
    except Exception:
        pass
        
    ext = filename.split(".")[-1].lower() if "." in filename else ""
    if ext != "csv":
        raise HTTPException(
            status_code=400,
            detail="시드 데이터는 오직 CSV 형식만 업로드할 수 있습니다."
        )
        
    temp_path = os.path.join(UPLOAD_DIR, f"temp_seed_{filename}")
    try:
        # 파일 임시 쓰기
        with open(temp_path, "wb") as buffer:
            while chunk := await file.read(1024 * 1024):
                buffer.write(chunk)
                
        # 인코딩 디텍션 후 Pandas 로딩
        correct_enc = detect_csv_encoding(temp_path)
        df = pd.read_csv(temp_path, encoding=correct_enc, errors="replace")
        
        # 2. Pandas to_sql 벌크 적재 진행
        df.to_sql(name=target_table, con=engine, if_exists=if_exists, index=False)
        
        # 3. 위도/경도가 존재할 시 PostGIS geom 공간 지오메트리 빌드 & GIST 인덱싱 트리거
        columns = [c.lower() for c in df.columns]
        lat_candidates = ["lat", "latitude", "위도", "y", "y좌표"]
        lng_candidates = ["lng", "longitude", "경도", "x", "x좌표"]
        
        lat_col = next((c for c in df.columns if c.lower() in lat_candidates), None)
        lng_col = next((c for c in df.columns if c.lower() in lng_candidates), None)
        
        spatial_migrated = False
        if lat_col and lng_col:
            # geom 기하 컬럼 추가, 포인트 형성 및 GIST 인덱스 빌드 (PostGIS 기능 바인딩)
            db.execute(text(f"ALTER TABLE {target_table} ADD COLUMN IF NOT EXISTS geom geometry(Point, 4326);"))
            db.execute(text(f"UPDATE {target_table} SET geom = ST_SetSRID(ST_MakePoint(CAST(\"{lng_col}\" AS double precision), CAST(\"{lat_col}\" AS double precision)), 4326) WHERE geom IS NULL;"))
            db.execute(text(f"CREATE INDEX IF NOT EXISTS idx_{target_table}_geom_gist ON {target_table} USING GIST(geom);"))
            db.commit()
            spatial_migrated = True
            
        return {
            "status": "success",
            "message": f"성공적으로 {len(df)}건의 레코드를 '{target_table}' 테이블에 벌크 적재 완료했습니다.",
            "filename": filename,
            "spatial_geometry_built": spatial_migrated
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"원천 시드 데이터 벌크 적재 중 치명적인 서버 오류가 발생했습니다: {str(e)}"
        )
    finally:
        # 임시 파일 소거
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass

# --- [Phase 2] 관리자 전용 예측 머신러닝 모델(.pkl) 핫 업로드 API ---
@router.post("/upload/model")
async def upload_ml_model(
    domain_tag: str,
    file: UploadFile = File(...),
    current_admin: dict = Depends(get_current_admin)
):
    filename = file.filename
    ext = filename.split(".")[-1].lower()
    if ext != "pkl":
        raise HTTPException(
            status_code=400,
            detail="오직 머신러닝 예측 모델 파일(.pkl) 형식만 업로드할 수 있습니다."
        )
        
    from app.routers.spatial import registry_path, model_registry
    os.makedirs(registry_path, exist_ok=True)
    
    # {domain_tag}_v_latest.pkl 로 강제 타겟팅하여 명명
    save_name = f"{domain_tag}_v_latest.pkl"
    save_path = os.path.join(registry_path, save_name)
    
    # 기존 파일 삭제 처리
    if os.path.exists(save_path):
        try:
            os.remove(save_path)
        except Exception:
            pass
            
    try:
        with open(save_path, "wb") as buffer:
            while chunk := await file.read(1024 * 1024):
                buffer.write(chunk)
                
        # 레지스트리 핫 로딩 트리거
        model_registry.load_models()
        
        return {
            "status": "success",
            "message": f"성공적으로 {domain_tag} 도메인의 머신러닝 모델(.pkl) 업로드 및 실시간 핫 바인딩을 완료했습니다."
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"모델 업로드 또는 적재 중 치명적 런타임 장해가 발생했습니다: {str(e)}"
        )

# --- [Phase 3] 관리자 전용 공간정보 Shapefile 벌크 적재 API ---
@router.post("/upload/seed-shapefile")
async def seed_shapefile(
    target_table: str = "city_spatial_features",
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    temp_dir = os.path.join(UPLOAD_DIR, "temp_shp")
    os.makedirs(temp_dir, exist_ok=True)
    
    saved_paths = {}
    base_name = None
    
    for file in files:
        filename = file.filename
        ext = filename.split(".")[-1].lower()
        if ext not in ["shp", "dbf", "shx", "prj"]:
            continue
            
        cur_base = ".".join(filename.split(".")[:-1])
        if base_name is None:
            base_name = cur_base
        
        save_path = os.path.join(temp_dir, filename)
        with open(save_path, "wb") as buffer:
            while chunk := await file.read(1024 * 1024):
                buffer.write(chunk)
        saved_paths[ext] = save_path
        
    if "shp" not in saved_paths or "dbf" not in saved_paths or "shx" not in saved_paths:
        # 임시 디렉토리 정리
        import shutil
        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass
        raise HTTPException(
            status_code=400,
            detail="Shapefile 적재를 위해선 .shp, .dbf, .shx 파일셋이 모두 필요합니다."
        )
        
    shp_file_path = saved_paths["shp"]
    
    try:
        sf = shapefile.Reader(shp_file_path, encoding="cp949")
        records = sf.records()
        shapes = sf.shapes()
        
        if not shapes:
            raise HTTPException(status_code=400, detail="Shapefile 내에 공간 데이터가 존재하지 않습니다.")
            
        first_shape = shapes[0]
        xmin = first_shape.bbox[0]
        
        src_srid = 4326
        if 120.0 <= xmin <= 132.0:
            src_srid = 4326
        elif 150000.0 <= xmin <= 250000.0:
            src_srid = 5186
        elif 800000.0 <= xmin <= 1100000.0:
            src_srid = 5179
            
        print(f"[Auto-SRID] Detected coordinate scale xmin={xmin}, assigning SRID={src_srid}")
        
        fields = [f[0] for f in sf.fields[1:]]
        success_count = 0
        
        for i, shp in enumerate(shapes):
            rec = records[i]
            geom_obj = shape(shp)
            wkt = geom_obj.wkt
            
            properties = {}
            for idx, field_name in enumerate(fields):
                val = rec[idx]
                if isinstance(val, bytes):
                    try:
                        val = val.decode("cp949", errors="replace")
                    except Exception:
                        val = str(val)
                properties[field_name] = val
                
            if target_table == "cadastral_lands":
                pnu = properties.get("PNU") or properties.get("pnu") or f"TEMP_{i}"
                jibun = properties.get("JIBUN") or properties.get("jibun") or ""
                land_use = properties.get("LDC") or properties.get("ldc") or "대"
                ownership = "국유지" if properties.get("buysable") == "TRUE" or properties.get("OWNER") == "국" else "사유지"
                
                insert_query = text("""
                    INSERT INTO cadastral_lands (district_id, dong_id, pnu, jibun, land_use_code, ownership_type, geom)
                    VALUES (
                        1, 
                        COALESCE((SELECT id FROM municipal_dongs WHERE ST_Contains(geom, ST_Centroid(ST_Transform(ST_SetSRID(ST_GeomFromText(:wkt), :src_srid), 4326))) LIMIT 1), 1),
                        :pnu, 
                        :jibun, 
                        :land_use, 
                        :ownership, 
                        ST_Multi(ST_Transform(ST_SetSRID(ST_GeomFromText(:wkt), :src_srid), 4326))
                    )
                """)
                db.execute(insert_query, {
                    "wkt": wkt,
                    "src_srid": src_srid,
                    "pnu": pnu,
                    "jibun": jibun,
                    "land_use": land_use,
                    "ownership": ownership
                })
            elif target_table == "restricted_zones":
                zone_name = properties.get("NAME") or properties.get("name") or "제한구역"
                address = properties.get("ADDR") or properties.get("address") or ""
                zone_type = properties.get("ZONE_TYPE") or properties.get("zone_type") or "nosmoking_zone"
                area = float(properties.get("RADIUS") or properties.get("radius") or properties.get("area") or 10.0)
                
                insert_query = text("""
                    INSERT INTO restricted_zones (district_id, dong_id, zone_name, address, geom, zone_type, area)
                    VALUES (
                        1,
                        COALESCE((SELECT id FROM municipal_dongs WHERE ST_Contains(geom, ST_Centroid(ST_Transform(ST_SetSRID(ST_GeomFromText(:wkt), :src_srid), 4326))) LIMIT 1), 1),
                        :zone_name,
                        :address,
                        ST_Transform(ST_SetSRID(ST_GeomFromText(:wkt), :src_srid), 4326),
                        :zone_type,
                        :area
                    )
                """)
                db.execute(insert_query, {
                    "wkt": wkt,
                    "src_srid": src_srid,
                    "zone_name": zone_name,
                    "address": address,
                    "zone_type": zone_type,
                    "area": area
                })
            else:
                feature_name = properties.get("NAME") or properties.get("name") or base_name or "uploaded_feature"
                feature_type = properties.get("TYPE") or properties.get("type") or target_table
                
                insert_query = text("""
                    INSERT INTO city_spatial_features (feature_type, feature_name, geom, properties)
                    VALUES (
                        :feature_type, 
                        :feature_name, 
                        ST_Transform(ST_SetSRID(ST_GeomFromText(:wkt), :src_srid), 4326), 
                        :properties
                    )
                """)
                db.execute(insert_query, {
                    "feature_type": feature_type,
                    "feature_name": feature_name,
                    "wkt": wkt,
                    "src_srid": src_srid,
                    "properties": json.dumps(properties, ensure_ascii=False)
                })
            success_count += 1
            
        db.commit()
        return {
            "status": "success",
            "message": f"Shapefile의 {success_count}개 공간 객체를 '{target_table}' 테이블에 자동 변환 적재 성공했습니다. (감지된 원본 SRID: {src_srid})"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Shapefile 적재 중 에러가 발생했습니다: {str(e)}"
        )
    finally:
        import shutil
        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass

# --- [Phase 4] 관리자 전용 원클릭 초기 구동 설정 (Cold Start / Multi-Region Initializer) API ---
@router.post("/upload/init-coldstart")
@router.post("/upload/seed-spatial")
async def init_coldstart(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    import zipfile
    import shutil
    import re
    from collections import defaultdict
    
    # 1. 임시 디렉토리 생성
    temp_dir = os.path.join(UPLOAD_DIR, "temp_coldstart")
    if os.path.exists(temp_dir):
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass
    os.makedirs(temp_dir, exist_ok=True)
    
    zip_path = os.path.join(temp_dir, file.filename)
    try:
        # ZIP 저장
        with open(zip_path, "wb") as buffer:
            while chunk := await file.read(1024 * 1024):
                buffer.write(chunk)
                
        # ZIP 압축 해제
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
            
        # 모든 파일 리스트 재귀 검색
        all_extracted_files = []
        for root, dirs, files_list in os.walk(temp_dir):
            for f in files_list:
                all_extracted_files.append(os.path.join(root, f))
                
        # 확장자별 분류 및 파일 그룹화
        shp_groups = {}
        csv_files = []
        
        for fp in all_extracted_files:
            if fp.endswith(".zip"):
                continue
            base, ext = os.path.splitext(fp)
            ext = ext[1:].lower()
            if ext in ["shp", "dbf", "shx", "prj"]:
                if base not in shp_groups:
                    shp_groups[base] = {}
                shp_groups[base][ext] = fp
            elif ext == "csv":
                csv_files.append(fp)
                
        # 2. 마스터 파일 판독
        sig_shp_base = None
        emd_shp_base = None
        cad_shp_base = None
        mapping_csv_path = None
        property_csv_path = None
        
        for base in shp_groups.keys():
            base_lower = os.path.basename(base).lower()
            g = shp_groups[base]
            if not ("shp" in g and "dbf" in g and "shx" in g):
                continue
            if "sig" in base_lower or "시군구" in base_lower or "district" in base_lower:
                sig_shp_base = base
            elif "emd" in base_lower or "읍면동" in base_lower or "dong" in base_lower:
                emd_shp_base = base
            elif "lsmd" in base_lower or "지적" in base_lower or "land" in base_lower:
                cad_shp_base = base
                
        for cp in csv_files:
            cp_lower = os.path.basename(cp).lower()
            if "매핑" in cp_lower or "연계" in cp_lower or "dong_mapping" in cp_lower or "법정동" in cp_lower:
                mapping_csv_path = cp
            elif "국유" in cp_lower or "부동산" in cp_lower or "property" in cp_lower:
                property_csv_path = cp
                
        print(f"[Coldstart Discovery] sig={sig_shp_base}, emd={emd_shp_base}, cad={cad_shp_base}, mapping={mapping_csv_path}, property={property_csv_path}")
        
        if not emd_shp_base or not mapping_csv_path or not cad_shp_base:
            raise HTTPException(
                status_code=400,
                detail="초기 구동을 위해서는 읍면동 경계 SHP, 법정동 연계 CSV, 지적도 SHP 파일셋이 zip 압축 파일에 필수로 포함되어야 합니다."
            )
            
        # 3. 데이터베이스 정비 (TRUNCATE)
        db.execute(text("TRUNCATE TABLE transit_passengers, transit_stations, civil_complaints, illegal_dumping_zones, population_stats, age_demographics, cadastral_lands, restricted_zones, dong_boundaries CASCADE;"))
        db.commit()
        
        # --- STEP 1. Districts (시군구) 식별 및 인서트 ---
        district_id = 1
        district_name = "전체구역"
        sig_cd = "99999"
        
        # 지적도 파일명에서 지자체 코드 파싱 유도
        cad_filename = os.path.basename(cad_shp_base)
        sig_code_match = re.search(r"LSMD_CONT_LDREG_(\d{5})", cad_filename)
        if sig_code_match:
            sig_cd = sig_code_match.group(1)
            
        if sig_shp_base:
            sf_sig = shapefile.Reader(shp_groups[sig_shp_base]["shp"], encoding="cp949")
            sig_recs = sf_sig.records()
            sig_fields = [f[0] for f in sf_sig.fields[1:]]
            
            for rec in sig_recs:
                props = {sig_fields[j]: rec[j] for j in range(len(sig_fields))}
                for k, v in props.items():
                    if isinstance(v, bytes):
                        props[k] = v.decode("cp949", errors="replace")
                
                cd_val = props.get("SIG_CD") or props.get("sig_cd")
                nm_val = props.get("SIG_KOR_NM") or props.get("sig_kor_nm") or props.get("SIG_ENG_NM")
                if cd_val and (sig_cd == "99999" or cd_val == sig_cd):
                    sig_cd = str(cd_val)
                    district_name = str(nm_val)
                    break
            
            if district_name == "전체구역" and len(sig_recs) > 0:
                first_props = {sig_fields[j]: sig_recs[0][j] for j in range(len(sig_fields))}
                sig_cd = str(first_props.get("SIG_CD") or "11170")
                district_name = str(first_props.get("SIG_KOR_NM") or first_props.get("sig_kor_nm") or "용산구")
        else:
            known_sig = {
                "11170": "용산구", "11110": "종로구", "11140": "중구", "11200": "성동구", 
                "11215": "광진구", "11230": "동대문구", "11260": "중랑구", "11290": "성북구", 
                "11305": "강북구", "11320": "도봉구", "11350": "노원구", "11380": "은평구", 
                "11410": "서대문구", "11440": "마포구", "11470": "양천구", "11500": "강서구", 
                "11530": "구로구", "11545": "금천구", "11560": "영등포구", "11590": "동작구", 
                "11620": "관악구", "11650": "서초구", "11680": "강남구", "11710": "송파구", 
                "11740": "강동구"
            }
            district_name = known_sig.get(sig_cd, "신규 자치구")
            
        print(f"[Coldstart Districts] Resolved District: name={district_name}, sig_cd={sig_cd}")
        
        district_id = db.execute(text("""
            INSERT INTO districts (id, district_name, sig_cd)
            VALUES (1, :name, :sig_cd)
            ON CONFLICT (sig_cd) DO UPDATE SET district_name = EXCLUDED.district_name
            RETURNING id;
        """), {"name": district_name, "sig_cd": sig_cd}).scalar()
        
        # --- STEP 2. 법정동-행정동 연계매핑 CSV 로드 ---
        correct_enc = detect_csv_encoding(mapping_csv_path)
        mapping_df = pd.read_csv(mapping_csv_path, encoding=correct_enc, errors="replace")
        mapping_df.columns = [c.strip().lower() for c in mapping_df.columns]
        
        adm_code_col = next((c for c in mapping_df.columns if "행정동코드" in c or "adm_cd" in c or "adm_code" in c), mapping_df.columns[0])
        adm_name_col = next((c for c in mapping_df.columns if "행정동명" in c or "adm_nm" in c or "adm_name" in c), mapping_df.columns[1])
        leg_code_col = next((c for c in mapping_df.columns if "법정동코드" in c or "leg_cd" in c or "leg_code" in c), mapping_df.columns[2])
        leg_name_col = next((c for c in mapping_df.columns if "법정동명" in c or "leg_nm" in c or "leg_name" in c), mapping_df.columns[3])
        
        adm_to_leg = defaultdict(list)
        unique_leg_dongs = {}
        for _, row in mapping_df.iterrows():
            adm_val = str(row[adm_code_col])[:8]
            leg_val = str(row[leg_code_col])
            leg_name = str(row[leg_name_col])
            
            unique_leg_dongs[leg_val] = leg_name
            if adm_val not in adm_to_leg:
                adm_to_leg[adm_val] = []
            if leg_val not in adm_to_leg[adm_val]:
                adm_to_leg[adm_val].append(leg_val)
                
        # --- STEP 3. Dong Boundaries (읍면동) Shapefile 적재 ---
        sf_emd = shapefile.Reader(shp_groups[emd_shp_base]["shp"], encoding="cp949")
        emd_recs = sf_emd.records()
        emd_shapes = sf_emd.shapes()
        emd_fields = [f[0] for f in sf_emd.fields[1:]]
        
        emd_xmin = emd_shapes[0].bbox[0]
        emd_srid = 5179
        if 120.0 <= emd_xmin <= 132.0:
            emd_srid = 4326
        elif 150000.0 <= emd_xmin <= 250000.0:
            emd_srid = 5186
            
        dong_db_map = {}
        dong_centroids = {}
        dong_count = 0
        for idx, shp in enumerate(emd_shapes):
            rec = emd_recs[idx]
            props = {emd_fields[j]: rec[j] for j in range(len(emd_fields))}
            for k, v in props.items():
                if isinstance(v, bytes):
                    props[k] = v.decode("cp949", errors="replace")
                    
            emd_cd = str(props.get("EMD_CD") or props.get("emd_cd") or "")
            if emd_cd.startswith(sig_cd):
                leg_code = emd_cd + "00"
                name = props.get("EMD_KOR_NM") or props.get("emd_kor_nm") or props.get("EMD_ENG_NM")
                
                geom = shape(shp)
                wkt = geom.wkt
                
                db_id = db.execute(text("""
                    INSERT INTO dong_boundaries (district_id, dong_code, dong_name, geom)
                    VALUES (:district_id, :dong_code, :dong_name, ST_Multi(ST_Transform(ST_GeomFromText(:wkt, :srid), 4326)))
                    RETURNING id
                """), {
                    "district_id": district_id,
                    "dong_code": leg_code,
                    "dong_name": name,
                    "wkt": wkt,
                    "srid": emd_srid
                }).scalar()
                
                dong_db_map[leg_code] = db_id
                c_pt = geom.centroid
                c_res = db.execute(text("""
                    SELECT ST_X(ST_Transform(ST_SetSRID(ST_MakePoint(:x, :y), :srid), 4326)) AS lng,
                           ST_Y(ST_Transform(ST_SetSRID(ST_MakePoint(:x, :y), :srid), 4326)) AS lat
                """), {"x": c_pt.x, "y": c_pt.y, "srid": emd_srid}).fetchone()
                dong_centroids[db_id] = (c_res[0], c_res[1])
                dong_count += 1
                
        print(f"[Coldstart Dong] Seeded {dong_count} 법정동 경계.")
        
        # --- STEP 4. 국유부동산 CSV 캐싱 ---
        property_set = set()
        if property_csv_path:
            prop_enc = detect_csv_encoding(property_csv_path)
            prop_df = pd.read_csv(property_csv_path, encoding=prop_enc, errors="replace")
            prop_df.columns = [c.strip().lower() for c in prop_df.columns]
            
            pnu_col = next((c for c in prop_df.columns if "pnu" in c or "필지코드" in c or "지적코드" in c), None)
            jibun_col = next((c for c in prop_df.columns if "지번" in c or "jibun" in c or "소재지" in c), None)
            
            for _, row in prop_df.iterrows():
                if pnu_col:
                    pnu_val = str(row[pnu_col]).strip()
                    if pnu_val:
                        property_set.add(pnu_val)
                elif jibun_col:
                    jibun_val = str(row[jibun_col]).strip()
                    if jibun_val:
                        property_set.add(jibun_val)
        
        # --- STEP 5. 연속지적도(LSMD) Shapefile 적재 ---
        sf_cad = shapefile.Reader(shp_groups[cad_shp_base]["shp"], encoding="cp949")
        cad_recs = sf_cad.records()
        cad_shapes = sf_cad.shapes()
        cad_fields = [f[0] for f in sf_cad.fields[1:]]
        
        cad_xmin = cad_shapes[0].bbox[0]
        cad_srid = 5179
        if 120.0 <= cad_xmin <= 132.0:
            cad_srid = 4326
        elif 150000.0 <= cad_xmin <= 250000.0:
            cad_srid = 5186
            
        def get_dong_id_for_geom(wkt, srid):
            res = db.execute(text("""
                SELECT id FROM dong_boundaries 
                WHERE ST_Contains(geom, ST_Centroid(ST_Transform(ST_SetSRID(ST_GeomFromText(:wkt), :srid), 4326))) 
                LIMIT 1
            """), {"wkt": wkt, "srid": srid}).fetchone()
            if res:
                return res[0]
            fallback_res = db.execute(text("SELECT id FROM dong_boundaries LIMIT 1")).fetchone()
            return fallback_res[0] if fallback_res else 1

        # 지적 필지 데이터셋 수집용 리스트
        cad_params = []
        cad_count = 0
        for idx, shp in enumerate(cad_shapes):
            rec = cad_recs[idx]
            props = {cad_fields[j]: rec[j] for j in range(len(cad_fields))}
            for k, v in props.items():
                if isinstance(v, bytes):
                    props[k] = v.decode("cp949", errors="replace")
                    
            pnu_raw = props.get("PNU") or props.get("pnu") or f"PNU_{idx}"
            if isinstance(pnu_raw, float):
                pnu = str(int(pnu_raw))
            elif isinstance(pnu_raw, str):
                pnu_str = pnu_raw.strip()
                if "E+" in pnu_str.upper() or "E-" in pnu_str.upper() or "." in pnu_str:
                    try:
                        pnu = str(int(float(pnu_str)))
                    except Exception:
                        pnu = pnu_str
                else:
                    pnu = pnu_str
            else:
                pnu = str(pnu_raw).strip()
                
            jibun = props.get("JIBUN") or props.get("jibun") or ""
            land_use = props.get("LDC") or props.get("ldc") or "대"
            
            is_national = pnu in property_set or any(x in jibun for x in property_set) or props.get("buysable") == "TRUE" or props.get("OWNER") == "국"
            ownership = "국유지" if is_national else "사유지"
            
            geom = shape(shp)
            wkt = geom.wkt
            
            # 동기식 get_dong_id_for_geom 쿼리를 루프 내부에서 제거하고 기본값(1) 매핑하여 성능 병목 파괴
            dong_id = 1
            
            cad_params.append({
                "district_id": district_id,
                "dong_id": dong_id,
                "pnu": pnu,
                "jibun": jibun,
                "land_use_code": land_use,
                "ownership_type": ownership,
                "wkt": wkt,
                "srid": cad_srid
            })
            cad_count += 1

        # 1. 일괄 벌크 인서트 수행 (Round-trip 1회 수렴)
        if cad_params:
            insert_query = text("""
                INSERT INTO cadastral_lands (district_id, dong_id, pnu, jibun, land_use_code, ownership_type, geom)
                VALUES (:district_id, :dong_id, :pnu, :jibun, :land_use_code, :ownership_type, ST_Multi(ST_Transform(ST_SetSRID(ST_GeomFromText(:wkt, :srid), 4326))))
            """)
            db.execute(insert_query, cad_params)
            db.commit()

        # 2. 단 1방의 PostGIS Spatial Join UPDATE 쿼리로 0.5초만에 전체 법정동 ID 정밀 일치 갱신
        print(f"[Coldstart Optimization] Running Spatial Join Update for {cad_count} parcels...")
        update_query = text("""
            UPDATE cadastral_lands c
            SET dong_id = d.id
            FROM dong_boundaries d
            WHERE ST_Contains(d.geom, ST_Centroid(c.geom))
            AND c.district_id = :district_id;
        """)
        db.execute(update_query, {"district_id": district_id})
        db.commit()
        
        return {
            "status": "success",
            "message": f"성공적으로 [{district_name}] 공간정보 인프라 콜드스타트 설정을 끝마쳤습니다. (행정동 {dong_count}개, 지적 필지 {cad_count}개 생성 완료)",
            "district": district_name,
            "sig_cd": sig_cd,
            "dongs_seeded": dong_count,
            "parcels_seeded": cad_count
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"초기구동설정 적재 중 치명적 오류가 발생했습니다: {str(e)}"
        )
    finally:
        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass


# --- Helper to save list of uploaded files for shapefiles ---
def save_uploaded_files(files: List[UploadFile], temp_dir: str) -> Dict[str, Dict[str, str]]:
    import shutil
    shp_groups = {}
    for f in files:
        filename = f.filename
        try:
            filename = filename.encode('latin-1').decode('utf-8')
        except Exception:
            pass
        
        save_path = os.path.join(temp_dir, filename)
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(f.file, buffer)
            
        base, ext = os.path.splitext(save_path)
        ext = ext[1:].lower()
        if ext in ["shp", "dbf", "shx", "prj"]:
            if base not in shp_groups:
                shp_groups[base] = {}
            shp_groups[base][ext] = save_path
    return shp_groups


# --- [Phase 4-1] 4단계 위저드형 단계별 공간정보 적재 API ---

@router.post("/upload/seed-spatial-step1")
async def seed_spatial_step1(
    sig_files: List[UploadFile] = File(default=[]),
    emd_files: List[UploadFile] = File(default=[]),
    mapping_csv: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    import shutil
    import tempfile
    from collections import defaultdict
    
    # 1. 임시 디렉토리 생성
    temp_dir = tempfile.mkdtemp(prefix="coldstart_step1_", dir=UPLOAD_DIR)
    
    try:
        # 데이터베이스 정비 (TRUNCATE) - 뼈대를 세우기 위해 기존 테이블을 CASCADE 옵션으로 일괄 초기화
        db.execute(text("TRUNCATE TABLE transit_passengers, transit_stations, civil_complaints, illegal_dumping_zones, population_stats, age_demographics, cadastral_lands, restricted_zones, dong_boundaries, districts CASCADE;"))
        db.commit()
        
        # CSV 임시 저장 및 매핑 파싱
        csv_filename = mapping_csv.filename
        try:
            csv_filename = csv_filename.encode('latin-1').decode('utf-8')
        except Exception:
            pass
        csv_path = os.path.join(temp_dir, csv_filename)
        with open(csv_path, "wb") as buffer:
            shutil.copyfileobj(mapping_csv.file, buffer)
            
        correct_enc = detect_csv_encoding(csv_path)
        mapping_df = pd.read_csv(csv_path, encoding=correct_enc, errors="replace")
        mapping_df.columns = [c.strip().lower() for c in mapping_df.columns]
        
        adm_code_col = next((c for c in mapping_df.columns if "행정동코드" in c or "adm_cd" in c or "adm_code" in c), mapping_df.columns[0])
        adm_name_col = next((c for c in mapping_df.columns if "행정동명" in c or "adm_nm" in c or "adm_name" in c), mapping_df.columns[1])
        leg_code_col = next((c for c in mapping_df.columns if "법정동코드" in c or "leg_cd" in c or "leg_code" in c), mapping_df.columns[2])
        leg_name_col = next((c for c in mapping_df.columns if "법정동명" in c or "leg_nm" in c or "leg_name" in c), mapping_df.columns[3])
        
        adm_to_leg = defaultdict(list)
        unique_leg_dongs = {}
        for _, row in mapping_df.iterrows():
            adm_val = str(row[adm_code_col])[:8]
            leg_val = str(row[leg_code_col])
            leg_name = str(row[leg_name_col])
            unique_leg_dongs[leg_val] = leg_name
            if adm_val not in adm_to_leg:
                adm_to_leg[adm_val] = []
            if leg_val not in adm_to_leg[adm_val]:
                adm_to_leg[adm_val].append(leg_val)
                
        # SIG 파일 처리
        sig_shp_base = None
        if sig_files:
            sig_groups = save_uploaded_files(sig_files, temp_dir)
            for base, g in sig_groups.items():
                if "shp" in g and "dbf" in g and "shx" in g:
                    sig_shp_base = base
                    break
                    
        # EMD 파일 처리
        emd_shp_base = None
        if emd_files:
            emd_groups = save_uploaded_files(emd_files, temp_dir)
            for base, g in emd_groups.items():
                if "shp" in g and "dbf" in g and "shx" in g:
                    emd_shp_base = base
                    break
                    
        if not emd_shp_base:
            raise HTTPException(status_code=400, detail="읍면동 경계 SHP 파일셋(.shp, .dbf, .shx)이 존재하지 않습니다.")
            
        # 2. Districts (시군구) 식별 및 인서트
        district_name = "전체구역"
        sig_cd = "99999"
        
        # EMD 파일명에서 자치구 코드 유추 시도
        emd_filename = os.path.basename(emd_shp_base)
        sig_code_match = re.search(r"emd_(\d{5})|EMD_(\d{5})", emd_filename)
        if sig_code_match:
            sig_cd = sig_code_match.group(1) or sig_code_match.group(2)
            
        if sig_shp_base:
            sf_sig = shapefile.Reader(sig_shp_base, encoding="cp949")
            sig_recs = sf_sig.records()
            sig_fields = [f[0] for f in sf_sig.fields[1:]]
            for rec in sig_recs:
                props = {sig_fields[j]: rec[j] for j in range(len(sig_fields))}
                for k, v in props.items():
                    if isinstance(v, bytes):
                        props[k] = v.decode("cp949", errors="replace")
                cd_val = props.get("SIG_CD") or props.get("sig_cd")
                nm_val = props.get("SIG_KOR_NM") or props.get("sig_kor_nm") or props.get("SIG_ENG_NM")
                if cd_val:
                    sig_cd = str(cd_val)
                    district_name = str(nm_val)
                    break
        else:
            known_sig = {
                "11170": "용산구", "11110": "종로구", "11140": "중구", "11200": "성동구", 
                "11215": "광진구", "11230": "동대문구", "11260": "중랑구", "11290": "성북구", 
                "11305": "강북구", "11320": "도봉구", "11350": "노원구", "11380": "은평구", 
                "11410": "서대문구", "11440": "마포구", "11470": "양천구", "11500": "강서구", 
                "11530": "구로구", "11545": "금천구", "11560": "영등포구", "11590": "동작구", 
                "11620": "관악구", "11650": "서초구", "11680": "강남구", "11710": "송파구", 
                "11740": "강동구"
            }
            if sig_cd == "99999":
                sig_cd = "11170" # 기본값 용산구
            district_name = known_sig.get(sig_cd, "신규 자치구")
            
        district_id = db.execute(text("""
            INSERT INTO districts (id, district_name, sig_cd)
            VALUES (1, :name, :sig_cd)
            ON CONFLICT (sig_cd) DO UPDATE SET district_name = EXCLUDED.district_name
            RETURNING id;
        """), {"name": district_name, "sig_cd": sig_cd}).scalar()
        
        # 3. Dong Boundaries (읍면동) Shapefile 적재
        sf_emd = shapefile.Reader(emd_shp_base, encoding="cp949")
        emd_recs = sf_emd.records()
        emd_shapes = sf_emd.shapes()
        emd_fields = [f[0] for f in sf_emd.fields[1:]]
        
        emd_xmin = emd_shapes[0].bbox[0]
        emd_srid = 5179
        if 120.0 <= emd_xmin <= 132.0:
            emd_srid = 4326
        elif 150000.0 <= emd_xmin <= 250000.0:
            emd_srid = 5186
            
        dong_count = 0
        for idx, shp in enumerate(emd_shapes):
            rec = emd_recs[idx]
            props = {emd_fields[j]: rec[j] for j in range(len(emd_fields))}
            for k, v in props.items():
                if isinstance(v, bytes):
                    props[k] = v.decode("cp949", errors="replace")
                    
            emd_cd = str(props.get("EMD_CD") or props.get("emd_cd") or "")
            if emd_cd.startswith(sig_cd):
                leg_code = emd_cd + "00"
                name = props.get("EMD_KOR_NM") or props.get("emd_kor_nm") or props.get("EMD_ENG_NM")
                geom = shape(shp)
                wkt = geom.wkt
                
                db.execute(text("""
                    INSERT INTO dong_boundaries (district_id, dong_code, dong_name, geom)
                    VALUES (:district_id, :dong_code, :dong_name, ST_Multi(ST_Transform(ST_GeomFromText(:wkt, :srid), 4326)))
                    ON CONFLICT (dong_code) DO NOTHING
                """), {
                    "district_id": district_id,
                    "dong_code": leg_code,
                    "dong_name": name,
                    "wkt": wkt,
                    "srid": emd_srid
                })
                dong_count += 1
                
        db.commit()
        return {
            "status": "success",
            "message": f"1단계 행정 구역 및 공간 프레임이 구축되었습니다. (구역명: {district_name}, 행정동 {dong_count}개 생성 완료)",
            "district_name": district_name,
            "sig_cd": sig_cd,
            "dongs_count": dong_count
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"1단계 적재 중 에러가 발생했습니다: {str(e)}")
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


@router.post("/upload/seed-spatial-step2")
async def seed_spatial_step2(
    cad_files: List[UploadFile] = File(...),
    property_csv: Optional[UploadFile] = File(default=None),
    building_csv: Optional[UploadFile] = File(default=None),
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    import shutil
    import tempfile
    
    # 1. 임시 디렉토리 생성
    temp_dir = tempfile.mkdtemp(prefix="coldstart_step2_", dir=UPLOAD_DIR)
    
    try:
        # 국유부동산 정보 로드
        property_set = set()
        if property_csv:
            csv_filename = property_csv.filename
            try:
                csv_filename = csv_filename.encode('latin-1').decode('utf-8')
            except Exception:
                pass
            csv_path = os.path.join(temp_dir, csv_filename)
            with open(csv_path, "wb") as buffer:
                shutil.copyfileobj(property_csv.file, buffer)
                
            prop_enc = detect_csv_encoding(csv_path)
            prop_df = pd.read_csv(csv_path, encoding=prop_enc, errors="replace")
            prop_df.columns = [c.strip().lower() for c in prop_df.columns]
            
            pnu_col = next((c for c in prop_df.columns if "pnu" in c or "필지코드" in c or "지적코드" in c), None)
            jibun_col = next((c for c in prop_df.columns if "지번" in c or "jibun" in c or "소재지" in c), None)
            
            for _, row in prop_df.iterrows():
                if pnu_col:
                    pnu_val = str(row[pnu_col]).strip()
                    if pnu_val:
                        property_set.add(pnu_val)
                elif jibun_col:
                    jibun_val = str(row[jibun_col]).strip()
                    if jibun_val:
                        property_set.add(jibun_val)
                        
        # 지적도 SHP 세트 저장
        cad_groups = save_uploaded_files(cad_files, temp_dir)
        cad_shp_base = None
        for base, g in cad_groups.items():
            if "shp" in g and "dbf" in g and "shx" in g:
                cad_shp_base = base
                break
                
        if not cad_shp_base:
            raise HTTPException(status_code=400, detail="지적도 SHP 파일셋(.shp, .dbf, .shx)이 존재하지 않습니다.")
            
        sf_cad = shapefile.Reader(cad_shp_base, encoding="cp949")
        cad_recs = sf_cad.records()
        cad_shapes = sf_cad.shapes()
        cad_fields = [f[0] for f in sf_cad.fields[1:]]
        
        cad_xmin = cad_shapes[0].bbox[0]
        cad_srid = 5179
        if 120.0 <= cad_xmin <= 132.0:
            cad_srid = 4326
        elif 150000.0 <= cad_xmin <= 250000.0:
            cad_srid = 5186
            
        # 읍면동 바운더리 Contains 헬퍼
        def get_dong_id_for_geom(wkt, srid):
            res = db.execute(text("""
                SELECT id FROM dong_boundaries 
                WHERE ST_Contains(geom, ST_Centroid(ST_Transform(ST_SetSRID(ST_GeomFromText(:wkt), :srid), 4326))) 
                LIMIT 1
            """), {"wkt": wkt, "srid": srid}).fetchone()
            if res:
                return res[0]
            fallback_res = db.execute(text("SELECT id FROM dong_boundaries LIMIT 1")).fetchone()
            return fallback_res[0] if fallback_res else 1
            
        district_res = db.execute(text("SELECT id FROM districts LIMIT 1")).fetchone()
        district_id = district_res[0] if district_res else 1
        
        cad_count = 0
        for idx, shp in enumerate(cad_shapes):
            rec = cad_recs[idx]
            props = {cad_fields[j]: rec[j] for j in range(len(cad_fields))}
            for k, v in props.items():
                if isinstance(v, bytes):
                    props[k] = v.decode("cp949", errors="replace")
                    
            pnu_raw = props.get("PNU") or props.get("pnu") or f"PNU_{idx}"
            if isinstance(pnu_raw, float):
                pnu = str(int(pnu_raw))
            elif isinstance(pnu_raw, str):
                pnu_str = pnu_raw.strip()
                if "E+" in pnu_str.upper() or "E-" in pnu_str.upper() or "." in pnu_str:
                    try:
                        pnu = str(int(float(pnu_str)))
                    except Exception:
                        pnu = pnu_str
                else:
                    pnu = pnu_str
            else:
                pnu = str(pnu_raw).strip()
                
            jibun = props.get("JIBUN") or props.get("jibun") or ""
            land_use = props.get("LDC") or props.get("ldc") or "대"
            
            is_national = pnu in property_set or any(x in jibun for x in property_set) or props.get("buysable") == "TRUE" or props.get("OWNER") == "국"
            ownership = "국유지" if is_national else "사유지"
            
            geom = shape(shp)
            wkt = geom.wkt
            dong_id = get_dong_id_for_geom(wkt, cad_srid)
            
            db.execute(text("""
                INSERT INTO cadastral_lands (district_id, dong_id, pnu, jibun, land_use_code, ownership_type, geom)
                VALUES (:district_id, :dong_id, :pnu, :jibun, :land_use_code, :ownership_type, ST_Multi(ST_Transform(ST_SetSRID(ST_GeomFromText(:wkt, :srid), 4326))))
            """), {
                "district_id": district_id,
                "dong_id": dong_id,
                "pnu": pnu,
                "jibun": jibun,
                "land_use_code": land_use,
                "ownership_type": ownership,
                "wkt": wkt,
                "srid": cad_srid
            })
            cad_count += 1
            
        # --- 건축물대장 표제부 적재 (building_csv 가 들어온 경우) ---
        building_count = 0
        if building_csv:
            db.execute(text("TRUNCATE TABLE building_ledgers CASCADE;"))
            
            building_filename = building_csv.filename
            try:
                building_filename = building_filename.encode('latin-1').decode('utf-8')
            except Exception:
                pass
            building_path = os.path.join(temp_dir, building_filename)
            with open(building_path, "wb") as buffer:
                shutil.copyfileobj(building_csv.file, buffer)
                
            build_enc = detect_csv_encoding(building_path)
            build_df = pd.read_csv(building_path, encoding=build_enc, errors="replace", on_bad_lines='skip')
            build_df.columns = [c.strip() for c in build_df.columns]
            
            def make_pnu_local(r):
                try:
                    sig = str(int(r['시군구코드'])).zfill(5)
                    dong = str(int(r['법정동코드'])).zfill(5)
                    gb = str(r.get('대지구분코드', '1')).strip()
                    if not gb or gb == 'nan' or gb == '0':
                        gb = '1'
                    gb = gb[0]
                    bon = str(int(r['본번'])).zfill(4)
                    bu = str(int(r['부번'])).zfill(4)
                    return sig + dong + gb + bon + bu
                except Exception:
                    return None
                    
            for _, r_row in build_df.iterrows():
                pnu_val = make_pnu_local(r_row)
                if not pnu_val:
                    continue
                    
                def safe_float(val):
                    try:
                        return float(val) if not pd.isna(val) else 0.0
                    except Exception:
                        return 0.0
                        
                def safe_int(val):
                    try:
                        return int(val) if not pd.isna(val) else 0
                    except Exception:
                        return 0
                        
                db.execute(text("""
                    INSERT INTO building_ledgers (pnu, building_name, main_use_name, structure_name, total_area, ground_floors, underground_floors)
                    VALUES (:pnu, :building_name, :main_use_name, :structure_name, :total_area, :ground_floors, :underground_floors)
                """), {
                    "pnu": pnu_val,
                    "building_name": str(r_row.get('건물명', r_row.get('대지위치', ''))).strip(),
                    "main_use_name": str(r_row.get('주용도코드명', '미지정')).strip(),
                    "structure_name": str(r_row.get('구조코드명', '미지정')).strip(),
                    "total_area": safe_float(r_row.get('연면적')),
                    "ground_floors": safe_int(r_row.get('지상층수')),
                    "underground_floors": safe_int(r_row.get('지하층수'))
                })
                building_count += 1

        db.commit()
        return {
            "status": "success",
            "message": f"2단계 연속지적도 및 토지 소유권 정보가 적재되었습니다. (지적 필지 {cad_count}개, 건축물 표제부 {building_count}개 생성 완료)",
            "parcels_count": cad_count,
            "buildings_count": building_count
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"2단계 적재 중 에러가 발생했습니다: {str(e)}")
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


@router.post("/upload/seed-spatial-step3")
async def seed_spatial_step3(
    file_type: str,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    import shutil
    import tempfile
    
    # 1. 임시 디렉토리 생성
    temp_dir = tempfile.mkdtemp(prefix="coldstart_step3_", dir=UPLOAD_DIR)
    
    try:
        district_res = db.execute(text("SELECT id FROM districts LIMIT 1")).fetchone()
        district_id = district_res[0] if district_res else 1
        
        success_files = []
        rows_inserted = 0
        
        for file in files:
            filename = file.filename
            try:
                filename = filename.encode('latin-1').decode('utf-8')
            except Exception:
                pass
                
            file_path = os.path.join(temp_dir, filename)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
                
            if file_type == "restricted_zones":
                headers, rows = parse_csv_file(file_path)
                mapping, errors = analyze_csv_header_only(headers)
                
                lat_col = mapping.get("lat")
                lng_col = mapping.get("lng")
                addr_col = mapping.get("address")
                name_col = next((h for h in headers if "명" in h or "이름" in h or "name" in h or "구역" in h), headers[0])
                
                if not lat_col or not lng_col:
                    continue # 위경도 없는 파일은 패스
                    
                lat_idx = headers.index(lat_col)
                lng_idx = headers.index(lng_col)
                addr_idx = headers.index(addr_col) if addr_col else -1
                name_idx = headers.index(name_col) if name_col else -1
                
                zone_type = "smoking_zone" if "흡연" in filename or "smoking" in filename.lower() else "nosmoking_zone"
                
                for r in rows:
                    if len(r) <= max(lat_idx, lng_idx):
                        continue
                    try:
                        lat_val = float(r[lat_idx])
                        lng_val = float(r[lng_idx])
                        if lat_val == 0 or lng_val == 0:
                            continue
                        name_val = r[name_idx] if name_idx != -1 else "정화구역"
                        addr_val = r[addr_idx] if addr_idx != -1 else ""
                        
                        # 공간 조인으로 읍면동 ID 조회
                        dong_res = db.execute(text("""
                            SELECT id FROM dong_boundaries 
                            WHERE ST_Contains(geom, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)) 
                            LIMIT 1
                        """), {"lng": lng_val, "lat": lat_val}).fetchone()
                        dong_id = dong_res[0] if dong_res else None
                        
                        db.execute(text("""
                            INSERT INTO restricted_zones (district_id, dong_id, zone_name, address, geom, zone_type)
                            VALUES (:district_id, :dong_id, :zone_name, :address, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326), :zone_type)
                        """), {
                            "district_id": district_id,
                            "dong_id": dong_id,
                            "zone_name": name_val,
                            "address": addr_val,
                            "lng": lng_val,
                            "lat": lat_val,
                            "zone_type": zone_type
                        })
                        rows_inserted += 1
                    except Exception:
                        continue
                        
            elif file_type == "transit_stations":
                headers, rows = parse_csv_file(file_path)
                
                station_no_col = next((h for h in headers if "번호" in h or "no" in h.lower() or "id" in h.lower() or "코드" in h), headers[0])
                station_name_col = next((h for h in headers if "명" in h or "이름" in h or "name" in h.lower()), headers[1])
                lat_col = next((h for h in headers if "위도" in h or "y" in h.lower() or "lat" in h.lower()), None)
                lng_col = next((h for h in headers if "경도" in h or "x" in h.lower() or "lng" in h.lower() or "lon" in h.lower()), None)
                
                if not lat_col or not lng_col:
                    continue
                    
                no_idx = headers.index(station_no_col)
                name_idx = headers.index(station_name_col)
                lat_idx = headers.index(lat_col)
                lng_idx = headers.index(lng_col)
                
                transit_type = "bus" if "버스" in filename or "bus" in filename.lower() else "subway"
                
                for r in rows:
                    if len(r) <= max(lat_idx, lng_idx, no_idx, name_idx):
                        continue
                    try:
                        lat_val = float(r[lat_idx])
                        lng_val = float(r[lng_idx])
                        if lat_val == 0 or lng_val == 0:
                            continue
                        no_val = str(r[no_idx]).strip()
                        name_val = str(r[name_idx]).strip()
                        
                        dong_res = db.execute(text("""
                            SELECT id FROM dong_boundaries 
                            WHERE ST_Contains(geom, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)) 
                            LIMIT 1
                        """), {"lng": lng_val, "lat": lat_val}).fetchone()
                        dong_id = dong_res[0] if dong_res else None
                        
                        db.execute(text("""
                            INSERT INTO transit_stations (district_id, dong_id, station_no, station_name, transit_type, geom)
                            VALUES (:district_id, :dong_id, :station_no, :station_name, :transit_type, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326))
                            ON CONFLICT (station_no) DO UPDATE SET station_name = EXCLUDED.station_name
                        """), {
                            "district_id": district_id,
                            "dong_id": dong_id,
                            "station_no": no_val,
                            "station_name": name_val,
                            "transit_type": transit_type,
                            "lng": lng_val,
                            "lat": lat_val
                        })
                        rows_inserted += 1
                    except Exception:
                        continue
                        
            elif file_type == "transit_passengers":
                headers, rows = parse_csv_file(file_path)
                
                ym_col = next((h for h in headers if "년월" in h or "ym" in h.lower() or "일자" in h), headers[0])
                station_no_col = next((h for h in headers if "번호" in h or "역ID" in h or "노선" in h or "id" in h.lower() or "코드" in h), headers[1])
                board_col = next((h for h in headers if "승차" in h or "탑승" in h or "boarding" in h.lower()), None)
                alight_col = next((h for h in headers if "하차" in h or "alighting" in h.lower()), None)
                
                ym_idx = headers.index(ym_col)
                no_idx = headers.index(station_no_col)
                board_idx = headers.index(board_col) if board_col else -1
                alight_idx = headers.index(alight_col) if alight_col else -1
                
                # transit_stations 매핑 로드 캐싱
                station_no_map = {}
                stat_res = db.execute(text("SELECT id, station_no FROM transit_stations")).fetchall()
                for s_id, s_no in stat_res:
                    station_no_map[s_no] = s_id
                    
                for r in rows:
                    if len(r) <= max(ym_idx, no_idx):
                        continue
                    try:
                        ym_val = str(r[ym_idx]).replace("-", "").strip()[:6]
                        no_val = str(r[no_idx]).strip()
                        station_id = station_no_map.get(no_val)
                        if not station_id:
                            continue
                            
                        b_cnt = int(float(r[board_idx])) if board_idx != -1 else 0
                        a_cnt = int(float(r[alight_idx])) if alight_idx != -1 else 0
                        tot = b_cnt + a_cnt
                        
                        db.execute(text("""
                            INSERT INTO transit_passengers (station_id, analysis_ym, boarding_count, alighting_count, total_volume)
                            VALUES (:station_id, :analysis_ym, :boarding_count, :alighting_count, :total_volume)
                        """), {
                            "station_id": station_id,
                            "analysis_ym": ym_val,
                            "boarding_count": b_cnt,
                            "alighting_count": a_cnt,
                            "total_volume": tot
                        })
                        rows_inserted += 1
                    except Exception:
                        continue
                        
            elif file_type == "population_stats":
                headers, rows = parse_csv_file(file_path)
                
                dong_code_col = next((h for h in headers if "동코드" in h or "dong_code" in h.lower() or "dong_cd" in h.lower() or "행정동" in h), headers[0])
                pop_col = next((h for h in headers if "인구" in h or "생활인구" in h or "pop" in h.lower()), headers[-1])
                
                dong_idx = headers.index(dong_code_col)
                pop_idx = headers.index(pop_col)
                
                # dong_boundaries 매핑 로드 캐싱
                dong_code_map = {}
                dong_res = db.execute(text("SELECT id, dong_code FROM dong_boundaries")).fetchall()
                for d_id, d_cd in dong_res:
                    dong_code_map[d_cd[:8]] = d_id # 앞 8자리 기준 조인
                    
                for r in rows:
                    if len(r) <= max(dong_idx, pop_idx):
                        continue
                    try:
                        raw_dong = str(r[dong_idx]).strip()
                        dong_id = dong_code_map.get(raw_dong[:8])
                        if not dong_id:
                            continue
                        pop_val = float(r[pop_idx])
                        
                        # day_type, time_type 임의 기본값 부여
                        day_type = "weekday"
                        time_type = "avg"
                        
                        db.execute(text("""
                            INSERT INTO population_stats (dong_id, day_type, time_type, avg_population)
                            VALUES (:dong_id, :day_type, :time_type, :avg_population)
                        """), {
                            "dong_id": dong_id,
                            "day_type": day_type,
                            "time_type": time_type,
                            "avg_population": pop_val
                        })
                        rows_inserted += 1
                    except Exception:
                        continue
                        
            success_files.append(filename)
            
        db.commit()
        return {
            "status": "success",
            "message": f"3단계 [{file_type}] 지리지표 묶음 적재 완료! (총 {len(success_files)}개 파일, {rows_inserted}개 행 삽입 성공)",
            "inserted_rows": rows_inserted
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"3단계 지리지표 적재 중 에러: {str(e)}")
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


@router.post("/upload/seed-spatial-step4")
async def seed_spatial_step4(
    regulation_file: Optional[UploadFile] = File(default=None),
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    import shutil
    import tempfile
    
    temp_dir = tempfile.mkdtemp(prefix="coldstart_step4_", dir=UPLOAD_DIR)
    try:
        district_res = db.execute(text("SELECT id FROM districts LIMIT 1")).fetchone()
        district_id = district_res[0] if district_res else 1
        
        if regulation_file:
            filename = regulation_file.filename
            try:
                filename = filename.encode('latin-1').decode('utf-8')
            except Exception:
                pass
                
            file_path = os.path.join(temp_dir, filename)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(regulation_file.file, buffer)
                
            # PDF 임베딩 기동
            chunk_and_embed_pdf(file_path, filename, db, district_id)
            
        # 시스템 구동 상태 최종 커밋
        db.commit()
        
        return {
            "status": "success",
            "message": "스마트시티 입지 설정 및 GIS 뼈대 최종 완성! 이제 추천과 모의 심의 시뮬레이션을 개시할 수 있습니다."
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"4단계 최종 활성화 중 에러: {str(e)}")
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
