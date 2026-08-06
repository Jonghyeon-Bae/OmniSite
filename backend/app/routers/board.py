# -*- coding: utf-8 -*-
import os
import urllib.parse
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from datetime import datetime

from app.database import get_db

router = APIRouter(prefix="/api/v1/board", tags=["board"])

ATTACHMENT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "raw", "board_attachments")
os.makedirs(ATTACHMENT_DIR, exist_ok=True)

# --- 1. DTO Schemas ---
class NoticeCreateRequest(BaseModel):
    title: str = Field(..., description="공지사항 제목")
    content: str = Field(..., description="공지사항 본문")
    is_pinned: bool = Field(False, description="상단 고정 여부")
    attachment_name: Optional[str] = Field(None, description="첨부파일명")
    attachment_url: Optional[str] = Field(None, description="첨부파일 다운로드 URL")

class NoticeUpdateRequest(BaseModel):
    title: str = Field(..., description="공지사항 제목")
    content: str = Field(..., description="공지사항 본문")
    is_pinned: bool = Field(False, description="상단 고정 여부")
    attachment_name: Optional[str] = Field(None, description="첨부파일명")
    attachment_url: Optional[str] = Field(None, description="첨부파일 다운로드 URL")

class PostCreateRequest(BaseModel):
    title: str = Field(..., description="게시글 제목")
    content: str = Field(..., description="게시글 본문")
    author_name: str = Field("스마트도시과 공무원", description="작성자 성명/직책")
    department: str = Field("스마트도시과", description="작성 부서")
    attachment_name: Optional[str] = Field(None, description="첨부파일명")
    attachment_url: Optional[str] = Field(None, description="첨부파일 다운로드 URL")

class FaqCreateRequest(BaseModel):
    category: str = Field(..., description="FAQ 범주 카테고리")
    question: str = Field(..., description="FAQ 질문 제목")
    answer: str = Field(..., description="FAQ 답변 및 가이드라인")

class FaqUpdateRequest(BaseModel):
    category: str = Field(..., description="FAQ 범주 카테고리")
    question: str = Field(..., description="FAQ 질문 제목")
    answer: str = Field(..., description="FAQ 답변 및 가이드라인")

# --- 2. DB Table Auto-Initialization & Seeding ---
def ensure_board_tables(db: Session):
    try:
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS system_notices (
                id SERIAL PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                content TEXT NOT NULL,
                is_pinned BOOLEAN DEFAULT FALSE,
                author VARCHAR(100) DEFAULT '시스템 관리자',
                attachment_name VARCHAR(255),
                attachment_url VARCHAR(500),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        db.execute(text("ALTER TABLE system_notices ADD COLUMN IF NOT EXISTS attachment_name VARCHAR(255);"))
        db.execute(text("ALTER TABLE system_notices ADD COLUMN IF NOT EXISTS attachment_url VARCHAR(500);"))
        
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS community_posts (
                id SERIAL PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                content TEXT NOT NULL,
                author_name VARCHAR(100) NOT NULL,
                department VARCHAR(100) NOT NULL,
                views_count INT DEFAULT 0,
                attachment_name VARCHAR(255),
                attachment_url VARCHAR(500),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        db.execute(text("ALTER TABLE community_posts ADD COLUMN IF NOT EXISTS attachment_name VARCHAR(255);"))
        db.execute(text("ALTER TABLE community_posts ADD COLUMN IF NOT EXISTS attachment_url VARCHAR(500);"))

        db.execute(text("""
            CREATE TABLE IF NOT EXISTS system_faqs (
                id SERIAL PRIMARY KEY,
                category VARCHAR(100) NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[Board Table Init Warning] {e}")

# --- 3. Initial Seed Data ---
INITIAL_FAQS = [
    {
        "category": "📄 데이터 업로드 & 감리",
        "question": "[Step 1] 우리 구의 공간 CSV 데이터 업로드 시 필수 입력 컬럼과 주의사항은 무엇인가요?",
        "answer": "CSV 파일에는 반드시 위도(lat), 경도(lng), 지번 주소(jibun) 또는 PNU 코드가 포함되어야 합니다. 파일 선택 후 'AI 데이터 감리 기동' 버튼을 누르면 AI가 컬럼 파싱, 위경도 좌표 유효성, 중복 레코드 및 결측치를 100% 자동 검증하고 정정해 줍니다."
    },
    {
        "category": "📄 데이터 업로드 & 감리",
        "question": "[Step 1] AI 데이터 감리 중 오류 알림이 뜨면 어떻게 조치해야 하나요?",
        "answer": "좌표가 대한민국 영역을 벗어나거나 필수 컬럼명이 비어있는 경우 감리 경고가 뜹니다. 알림 창에 표시된 오류 행 번호를 확인하신 후, CSV 파일의 컬럼명을 'lat', 'lng', 'jibun'으로 맞춰 재업로드하시면 정상 감리 완료(Pass) 판정을 받으실 수 있습니다."
    },
    {
        "category": "🗺️ AHP & 공간 추천",
        "question": "[Step 2] 3D 지도 상에서 마커 위치를 보정하거나 임시 금지구역(Exclusion Zone)을 그리는 법은 무엇인가요?",
        "answer": "좌측 지도 화면에서 3D 필지 핀포인트 마커를 마우스로 직접 끌어(Drag & Drop) 원하는 입지로 위치를 정밀 보정할 수 있습니다. 또한 화면 좌측 상단의 '임시 금지구역 작도' 버튼을 클릭한 후 지도 위에 다각형(Polygon)을 렌더링하면 해당 구역이 자동 제척됩니다."
    },
    {
        "category": "🗺️ AHP & 공간 추천",
        "question": "[Step 2] 마커를 드래그했더니 '법정 금연구역 버퍼 침범' 알림과 함께 원래 위치로 되돌아가는 이유는 무엇인가요?",
        "answer": "OmniSite는 공공 규제 회피의 무결성을 보장하기 위해 '마커 드래그 스로틀링 & 이격거리 침범 자동 위치 롤백 엔진'이 상시 가동 중입니다. 학교나 어린이집 등 법정 금지 버퍼(10m~200m) 내부로 마커를 이동시킬 경우 안전을 위해 롤백됩니다."
    },
    {
        "category": "🗺️ AHP & 공간 추천",
        "question": "[Step 3] AHP 가중치 쌍대비교 입력 시 '일관성 비율(C.R. > 0.1) 모순' 경고가 뜰 때 가중치 수정 방법은 무엇인가요?",
        "answer": "AHP 가중치 슬라이더를 조절할 때 지표 간 상대적 중요도 설정에 논리적 모순이 발생하면 C.R. 경고가 인출됩니다. 화면에 제시되는 추천 조율 비율 가이드를 참고하여 슬라이더를 부드럽게 조정하시면 C.R. <= 0.1 검증이 통과되어 가중치가 락(Lock) 승인됩니다."
    },
    {
        "category": "🗺️ AHP & 공간 추천",
        "question": "[Step 4] 우측 입지 추천 결과 카드에서 AHP 입지 수용성과 XGBoost 주민 갈등도(CSS) 게이지는 어떻게 해석하나요?",
        "answer": "파란색 'AHP 입지 수용성 게이지'는 유동인구 및 편의성 지표에 따른 정량적 적격성을 의미하며, 주황색 'XGBoost 주민 갈등도 게이지(CSS)'는 민원 발생 위험도를 나타냅니다. 두 점수가 종합 연산된 'Closed-Loop 적격도(ISI)' 점수가 가장 높은 필지가 최종 Top 1 부지입니다."
    },
    {
        "category": "🗺️ AHP & 공간 추천",
        "question": "[Step 4] 추천 사유 카드에 '⚠️ [골목길 선형 필지 경고]' 태그가 떴을 때 행정 현장 점검 포인트는 무엇인가요?",
        "answer": "해당 필지의 지적 폭이 좁은 좁고 긴 골목형 지형(폭 < 2.5m)임을 백엔드 GIS가 자동 감지한 것입니다. 흡연부스나 시설물 설치 시 보행자 통행 장애 및 최소 보도폭(1.2m) 확보 여부를 현장에서 사전 점검하셔야 합니다."
    },
    {
        "category": "🗺️ AHP & 공간 추천",
        "question": "[Step 4] 추천지 카드 내 '🗺️ 로드뷰 보기' 버튼은 어떻게 활용하나요?",
        "answer": "해당 필지의 '🗺️ 로드뷰 보기' 버튼을 누르면 카카오맵 실시간 로드뷰 창이 새 탭으로 즉시 열려, 현장에 직접 방문하지 않고도 보도 폭, 도로 점용 상태 및 주변 상가 환경을 로드뷰 이미지로 즉각 확인하실 수 있습니다."
    },
    {
        "question": "자치구별/시설물별 법정 이격거리 규제 반경(10m~200m) 기준을 직접 변경하거나 설정하는 방법은 무엇인가요?",
        "answer": "상단 네비게이션 우측의 '⚙️ 관리자 콘솔 (Admin Console)' 메뉴로 진입하시면, 자치구별 조례 이격거리 가이드라인(학교 50m, 어린이집 10m 등) 및 시설물별 규제 반경 수치를 직접 수정 및 적용하실 수 있습니다. 기타 시스템 관련 문의는 지자체 전산망 지원 핫라인을 통해 접수하실 수 있습니다."
    }
]

# --- 4. Endpoints ---

@router.post("/upload-attachment")
async def upload_board_attachment(file: UploadFile = File(...)):
    """게시글/공지사항 문서 및 이미지 첨부파일 업로드 API"""
    try:
        import shutil
        clean_filename = os.path.basename(file.filename)
        save_path = os.path.join(ATTACHMENT_DIR, clean_filename)
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        encoded_name = urllib.parse.quote(clean_filename)
        file_url = f"/api/v1/board/attachments/{encoded_name}"
        return {
            "status": "success",
            "attachment_name": clean_filename,
            "attachment_url": file_url,
            "message": f"첨부파일 '{clean_filename}'이 성공적으로 업로드되었습니다."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"첨부파일 저장 처리 실패: {str(e)}")

@router.get("/attachments/{filename}")
async def get_board_attachment(filename: str):
    """게시글/공지사항 첨부파일 다운로드 API"""
    decoded_name = urllib.parse.unquote(filename)
    file_path = os.path.join(ATTACHMENT_DIR, decoded_name)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="해당 첨부파일을 서버에서 찾을 수 없습니다.")
    return FileResponse(file_path, filename=decoded_name)

@router.get("/notices")
async def get_notices(db: Session = Depends(get_db)):
    ensure_board_tables(db)
    
    try:
        rows = db.execute(text("SELECT id, title, content, is_pinned, author, created_at, attachment_name, attachment_url FROM system_notices ORDER BY is_pinned DESC, id DESC")).fetchall()
    except Exception:
        db.rollback()
        rows = []
    
    if not rows:
        try:
            db.execute(text("""
                INSERT INTO system_notices (title, content, is_pinned, author)
                VALUES 
                ('[공지] OmniSite SDSS v1.5.0-ZeroBias 시스템 릴리즈 안내', '스마트시티 공공 입지분석 지원 플랫폼 OmniSite SDSS v1.5.0 프로덕션 버전이 가동되었습니다. 100%% 무편향 멀티 도메인 수술 및 교량/터널 배제 공간 연산이 탑재되어 있습니다.', true, '시스템 관리자'),
                ('[안내] 2026년 5월 용산구 최신 유동인구 및 상가 업소 데이터셋 반영 완료', '용산구 관내 6,524개 지적 필지, 6,509개 상가, 338개 버스정류장, 76개 지하철 역사 및 월별 승하차 통계 데이터셋이 데이터베이스에 정밀 갱신되었습니다.', false, '시스템 관리자'),
                ('[안내] 공문서 규격 PDF 결재 보고서 동적 발행 기능 연동 안내', '분석 완료 후 우측 상단 결재란과 구청장 발신 명의가 도출되는 A4 PDF 공문서를 다운로드하여 관공서 내부 결재용으로 즉시 사용하실 수 있습니다.', false, '시스템 관리자')
            """))
            db.commit()
            rows = db.execute(text("SELECT id, title, content, is_pinned, author, created_at FROM system_notices ORDER BY is_pinned DESC, id DESC")).fetchall()
        except Exception as e:
            db.rollback()
            print(f"[Notice Seed Error] {e}")

    return [
        {
            "id": r[0],
            "title": r[1],
            "content": r[2],
            "is_pinned": r[3],
            "author": r[4],
            "created_at": r[5].strftime("%Y-%m-%d %H:%M") if r[5] else "",
            "attachment_name": r[6] if len(r) > 6 else None,
            "attachment_url": r[7] if len(r) > 7 else None
        }
        for r in rows
    ]

@router.post("/notices")
async def create_notice(req: NoticeCreateRequest, db: Session = Depends(get_db)):
    ensure_board_tables(db)
    db.execute(text("""
        INSERT INTO system_notices (title, content, is_pinned, author, attachment_name, attachment_url)
        VALUES (:title, :content, :is_pinned, '시스템 최고 관리자', :attachment_name, :attachment_url)
    """), {
        "title": req.title, 
        "content": req.content, 
        "is_pinned": req.is_pinned,
        "attachment_name": req.attachment_name,
        "attachment_url": req.attachment_url
    })
    db.commit()
    try:
        from app.routers.spatial import save_pipeline_log
        save_pipeline_log(db, 'BOARD', '[NOTICE_CREATE]', {'title': req.title, 'is_pinned': req.is_pinned})
    except Exception as log_err:
        print(f"[Notice Log Error] {log_err}")
    return {"message": "공지사항이 성공적으로 등록되었습니다."}

@router.put("/notices/{notice_id}")
async def update_notice(notice_id: int, req: NoticeUpdateRequest, db: Session = Depends(get_db)):
    ensure_board_tables(db)
    result = db.execute(text("""
        UPDATE system_notices 
        SET title = :title, content = :content, is_pinned = :is_pinned, attachment_name = :attachment_name, attachment_url = :attachment_url 
        WHERE id = :id
    """), {
        "title": req.title, 
        "content": req.content, 
        "is_pinned": req.is_pinned, 
        "attachment_name": req.attachment_name,
        "attachment_url": req.attachment_url,
        "id": notice_id
    })
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="해당 공지사항을 찾을 수 없습니다.")
    try:
        from app.routers.spatial import save_pipeline_log
        save_pipeline_log(db, 'BOARD', '[NOTICE_UPDATE]', {'notice_id': notice_id, 'title': req.title})
    except Exception as log_err:
        print(f"[Notice Log Error] {log_err}")
    return {"message": "공지사항이 수정되었습니다."}

@router.delete("/notices/{notice_id}")
async def delete_notice(notice_id: int, db: Session = Depends(get_db)):
    ensure_board_tables(db)
    result = db.execute(text("DELETE FROM system_notices WHERE id = :id"), {"id": notice_id})
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="해당 공지사항을 찾을 수 없습니다.")
    try:
        from app.routers.spatial import save_pipeline_log
        save_pipeline_log(db, 'BOARD', '[NOTICE_DELETE]', {'notice_id': notice_id})
    except Exception as log_err:
        print(f"[Notice Log Error] {log_err}")
    return {"message": "공지사항이 삭제되었습니다."}

@router.get("/community")
async def get_community_posts(db: Session = Depends(get_db)):
    ensure_board_tables(db)
    try:
        rows = db.execute(text("SELECT id, title, content, author_name, department, views_count, created_at, attachment_name, attachment_url FROM community_posts ORDER BY id DESC")).fetchall()
    except Exception:
        db.rollback()
        rows = []
    
    if not rows:
        try:
            db.execute(text("""
                INSERT INTO community_posts (title, content, author_name, department)
                VALUES 
                ('이촌동 한강공원 인근 스마트 쉼터 입지 검토 요청의 건', '이촌동 주민센터 담당입니다. 한강공원 접근로 부근 스마트 쉼터 설치에 관한 유동인구 및 금연구역 차집합 분석 의견 공유 부탁드립니다.', '김주무관', '스마트도시과'),
                ('용산역 광장 전기차 급속 충전소 부지 주민갈등도(CSS) 평가 교론', '용산역 광장 전면 국유지 필지에 전기차 충전소 탑재 시 인근 상가 번영회와의 NIMBY 갈등 지수 검토 내역입니다.', '박팀장', '기후환경과'),
                ('어린이집 30m 법정 이격거리 버퍼 산정 시 PostGIS GIST 인덱스 적용 후기', '신규 조례 등록 시 어린이집 이격거리가 30m로 자동 교정되어 공간 쿼리 탐색 속도가 비약적으로 향상되었습니다.', '이주무관', '도시계획과')
            """))
            db.commit()
            rows = db.execute(text("SELECT id, title, content, author_name, department, views_count, created_at, attachment_name, attachment_url FROM community_posts ORDER BY id DESC")).fetchall()
        except Exception as e:
            db.rollback()
            print(f"[Community Seed Error] {e}")

    return [
        {
            "id": r[0],
            "title": r[1],
            "content": r[2],
            "author_name": r[3],
            "department": r[4],
            "views_count": r[5],
            "created_at": r[6].strftime("%Y-%m-%d %H:%M") if r[6] else "",
            "attachment_name": r[7] if len(r) > 7 else None,
            "attachment_url": r[8] if len(r) > 8 else None
        }
        for r in rows
    ]

@router.post("/community")
async def create_community_post(req: PostCreateRequest, db: Session = Depends(get_db)):
    ensure_board_tables(db)
    db.execute(text("""
        INSERT INTO community_posts (title, content, author_name, department, attachment_name, attachment_url)
        VALUES (:title, :content, :author_name, :department, :attachment_name, :attachment_url)
    """), {
        "title": req.title,
        "content": req.content,
        "author_name": req.author_name,
        "department": req.department,
        "attachment_name": req.attachment_name,
        "attachment_url": req.attachment_url
    })
    db.commit()
    try:
        from app.routers.spatial import save_pipeline_log
        save_pipeline_log(db, 'BOARD', '[COMMUNITY_POST_CREATE]', {'title': req.title, 'author': req.author_name, 'department': req.department})
    except Exception as log_err:
        print(f"[Community Log Error] {log_err}")
    return {"message": "자유게시판 게시글이 성공적으로 등록되었습니다."}

@router.delete("/community/{post_id}")
async def delete_community_post(post_id: int, db: Session = Depends(get_db)):
    ensure_board_tables(db)
    result = db.execute(text("DELETE FROM community_posts WHERE id = :id"), {"id": post_id})
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="해당 게시글을 찾을 수 없습니다.")
    try:
        from app.routers.spatial import save_pipeline_log
        save_pipeline_log(db, 'BOARD', '[COMMUNITY_POST_DELETE]', {'post_id': post_id})
    except Exception as log_err:
        print(f"[Community Log Error] {log_err}")
    return {"message": "게시글이 삭제되었습니다."}

# --- FAQ DB Table CRUD Endpoints ---
@router.get("/faqs")
async def get_faqs(db: Session = Depends(get_db)):
    ensure_board_tables(db)
    try:
        rows = db.execute(text("SELECT id, category, question, answer, created_at FROM system_faqs ORDER BY id ASC")).fetchall()
    except Exception:
        db.rollback()
        rows = []
    
    if not rows:
        try:
            for item in INITIAL_FAQS:
                db.execute(text("""
                    INSERT INTO system_faqs (category, question, answer)
                    VALUES (:category, :question, :answer)
                """), item)
            db.commit()
            rows = db.execute(text("SELECT id, category, question, answer, created_at FROM system_faqs ORDER BY id ASC")).fetchall()
        except Exception as e:
            db.rollback()
            print(f"[FAQ Seed Error] {e}")

    return [
        {
            "id": r[0],
            "category": r[1],
            "question": r[2],
            "answer": r[3],
            "created_at": r[4].strftime("%Y-%m-%d %H:%M") if r[4] else ""
        }
        for r in rows
    ]

@router.post("/faqs")
async def create_faq(req: FaqCreateRequest, db: Session = Depends(get_db)):
    ensure_board_tables(db)
    db.execute(text("""
        INSERT INTO system_faqs (category, question, answer)
        VALUES (:category, :question, :answer)
    """), {"category": req.category, "question": req.question, "answer": req.answer})
    db.commit()
    return {"message": "신규 FAQ 지식 항목이 성공적으로 등록되었습니다."}

@router.put("/faqs/{faq_id}")
async def update_faq(faq_id: int, req: FaqUpdateRequest, db: Session = Depends(get_db)):
    ensure_board_tables(db)
    result = db.execute(text("""
        UPDATE system_faqs 
        SET category = :category, question = :question, answer = :answer 
        WHERE id = :id
    """), {"category": req.category, "question": req.question, "answer": req.answer, "id": faq_id})
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="해당 FAQ 항목을 찾을 수 없습니다.")
    return {"message": "FAQ 지식 항목이 수정되었습니다."}

@router.delete("/faqs/{faq_id}")
async def delete_faq(faq_id: int, db: Session = Depends(get_db)):
    ensure_board_tables(db)
    result = db.execute(text("DELETE FROM system_faqs WHERE id = :id"), {"id": faq_id})
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="해당 FAQ 항목을 찾을 수 없습니다.")
    return {"message": "FAQ 지식 항목이 삭제되었습니다."}
