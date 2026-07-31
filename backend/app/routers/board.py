# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from datetime import datetime

from app.database import get_db

router = APIRouter(prefix="/api/v1/board", tags=["board"])

# --- 1. DTO Schemas ---
class NoticeCreateRequest(BaseModel):
    title: str = Field(..., description="공지사항 제목")
    content: str = Field(..., description="공지사항 본문")
    is_pinned: bool = Field(False, description="상단 고정 여부")

class NoticeUpdateRequest(BaseModel):
    title: str = Field(..., description="공지사항 제목")
    content: str = Field(..., description="공지사항 본문")
    is_pinned: bool = Field(False, description="상단 고정 여부")

class PostCreateRequest(BaseModel):
    title: str = Field(..., description="게시글 제목")
    content: str = Field(..., description="게시글 본문")
    author_name: str = Field("스마트도시과 공무원", description="작성자 성명/직책")
    department: str = Field("스마트도시과", description="작성 부서")

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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS community_posts (
                id SERIAL PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                content TEXT NOT NULL,
                author_name VARCHAR(100) NOT NULL,
                department VARCHAR(100) NOT NULL,
                views_count INT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))

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
        "category": "⚖️ AI 심의 & 보고서",
        "question": "[Step 5/6] 3자 AI 모의 심의 토론(Debate Simulator) 기동 및 진행 흐름 관찰 방법은 무엇인가요?",
        "answer": "Step 4 추천 카드 하단의 'Step 6. 의사결정 갈등 심의 이동' 버튼을 클릭한 후 토론 시작을 누르면, 찬성자(입지 찬성), 반대자(주민 민원), 중재자(행정관) 3자 LLM이 실시간 SSE 스트리밍으로 심의 토론을 진행하며 실시간 토론록이 작성됩니다."
    },
    {
        "category": "⚖️ AI 심의 & 보고서",
        "question": "[Step 6] 최종 행정 의결서(PDF / DOCX) 인출 및 관인 날인 적용 방법은 무엇인가요?",
        "answer": "모의 심의 토론이 완료되면 팝업 하단에 '📄 행정 심의 의결서 인출 (PDF/DOCX)' 버튼이 활성화됩니다. 클릭 시 AHP 점수, CSS 갈등도, 토론 요약 및 지자체 관인이 날인된 표준 행정 의결서 양식이 전자 문서로 즉시 다운로드됩니다."
    },
    {
        "category": "📜 RAG 조례 & 이력",
        "question": "[RAG 조례 관리] 우리 구의 신규 금연 조례 PDF 파일을 RAG 지식베이스에 올리는 방법은 무엇인가요?",
        "answer": "상단 메뉴의 'RAG 조례 관리' 버튼을 누른 후, 파일 선택 창에서 지자체 조례 PDF/HWP 파일을 올려주시면 됩니다. 백엔드 pgvector가 1초 만에 1,536차원 벡터 공간으로 전환하여 지식베이스에 자동 적재합니다."
    },
    {
        "category": "📜 RAG 조례 & 이력",
        "question": "[RAG 조례 관리] 조례 PDF를 올린 후 개정 전후 조항 차이(Diff)를 확인하는 법은 무엇인가요?",
        "answer": "RAG 조례 관리 모달의 등록된 파일 목록에서 각 조례 항목 우측의 '⚖️ 개정 이력' 버튼을 1클릭하시면, pgvector가 감지한 신규 신설, 수정 개정, 삭제 폐지 조항 변동 요약을 프리뷰 카드로 바로 확인하실 수 있습니다."
    },
    {
        "category": "📜 RAG 조례 & 이력",
        "question": "[이력 대시보드] 과거에 우리 부서에서 분석했던 입지 심의 이력을 조회하는 방법은 무엇인가요?",
        "answer": "상단 네비게이션의 '이력 대시보드 (Analytics)' 메뉴로 이동하시면, 그동안 수행했던 입지 분석 날짜, 도메인, Top 1 지번, AHP 점수 및 SHA-256 검증 상태가 목록으로 정렬되어 1클릭 조회가 가능합니다."
    },
    {
        "category": "📜 RAG 조례 & 이력",
        "question": "[이력 대시보드] 분석 이력 목록에서 '🔍 심의 이력 상세 보기' 버튼을 누르면 무엇을 볼 수 있나요?",
        "answer": "과거 수행된 입지 분석의 세부 AHP 가중치, 후보지별 ISI 수용성 점수, 진행된 3자 AI 모의 토론록 전문 및 당시 편찬된 행정 의결서를 언제든지 재열람 및 다운로드하실 수 있습니다."
    },
    {
        "category": "📜 RAG 조례 & 이력",
        "question": "[이력 대시보드] 준공 후 사후 실증 공문서(PDF)를 등록하여 RAG OCR 감리를 받는 방법은 무엇인가요?",
        "answer": "이력 대시보드의 '사후 실증 공문 적재' 세션에서 실제 준공 고시 공문 PDF를 업로드하시면, RAG OCR 파이프라인이 실측 수치를 자동 추출하여 규제 부합률(%)을 감리하고 적격 시 지식베이스에 자동 축적합니다."
    },
    {
        "category": "🗺️ AHP & 공간 추천",
        "question": "공유킥보드 거치대나 전기차 충전소 등 다른 인프라 도메인을 선택하여 분석하는 방법은 무엇인가요?",
        "answer": "좌측 공간 제어 패널 상단의 '시설물 도메인 선택' 드롭다운에서 흡연부스, 공유이동수단 거치대, 전기차 충전소, 안심 옐로카펫 중 원하는 인프라를 선택하시면 해당 시설물 전용 지표 및 규제 반경이 자동 스왑 적용됩니다."
    },
    {
        "category": "🗺️ AHP & 공간 추천",
        "question": "후보지 상세 카드의 공시지가 및 면적 수치는 어디서 연동되어 가져오는 것인가요?",
        "answer": "국토교통부 지적도(Cadastral Lands) 및 부동산 공시지가 표준 PostgreSQL PostGIS 지오메트리 데이터베이스에서 해당 필지의 PNU 코드를 기반으로 실시간 100% 동적 인출되는 행정 데이터입니다."
    },
    {
        "category": "📄 데이터 업로드 & 감리",
        "question": "행정망 보안 로그아웃 처리 및 비밀번호 변경은 어디서 수행하나요?",
        "answer": "상단 네비게이션 우측의 프로필 아이콘을 클릭하시면 '비밀번호 변경' 및 '안전 로그아웃' 메뉴가 인출됩니다. 보안 정책에 따라 60분 간 조작이 없을 경우 보안 세션이 자동 만료됩니다."
    },
    {
        "category": "⚖️ AI 심의 & 보고서",
        "question": "SHA-256 감사 해시 체인(Hash Chain) 검증 마크는 어디서 확인할 수 있나요?",
        "answer": "입지 분석이 완료되면 우측 패널 하단 및 다운로드받으신 행정 의결서 문서 하단에 SHA-256 단방향 암호화 해시 코드(예: 8f9a2b...)가 위변조 방지 인증 인장으로 표출됩니다."
    },
    {
        "category": "🗺️ AHP & 공간 추천",
        "question": "자치구별/시설물별 법정 이격거리 규제 반경(10m~200m) 기준을 직접 변경하거나 설정하는 방법은 무엇인가요?",
        "answer": "상단 네비게이션 우측의 '⚙️ 관리자 콘솔 (Admin Console)' 메뉴로 진입하시면, 자치구별 조례 이격거리 가이드라인(학교 50m, 어린이집 10m 등) 및 시설물별 규제 반경 수치를 직접 수정 및 적용하실 수 있습니다. 기타 시스템 관련 문의는 지자체 전산망 지원 핫라인을 통해 접수하실 수 있습니다."
    }
]

# --- 4. Endpoints ---

@router.get("/notices")
async def get_notices(db: Session = Depends(get_db)):
    ensure_board_tables(db)
    
    try:
        rows = db.execute(text("SELECT id, title, content, is_pinned, author, created_at FROM system_notices ORDER BY is_pinned DESC, id DESC")).fetchall()
    except Exception:
        db.rollback()
        rows = []
    
    if not rows:
        try:
            db.execute(text("""
                INSERT INTO system_notices (title, content, is_pinned, author)
                VALUES 
                ('[공지] OmniSite SDSS v1.5.0-ZeroBias 시스템 릴리즈 안내', '스마트시티 공공 입지분석 지원 플랫폼 OmniSite SDSS v1.5.0 프로덕션 버전이 가동되었습니다. 100% 무편향 멀티 도메인 수술 및 교량/터널 배제 공간 연산이 탑재되어 있습니다.', true),
                ('[안내] 2026년 5월 용산구 최신 유동인구 및 상가 업소 데이터셋 반영 완료', '용산구 관내 6,524개 지적 필지, 6,509개 상가, 338개 버스정류장, 76개 지하철 역사 및 월별 승하차 통계 데이터셋이 데이터베이스에 정밀 갱신되었습니다.', false),
                ('[안내] 공문서 규격 PDF 결재 보고서 동적 발행 기능 연동 안내', '분석 완료 후 우측 상단 결재란과 구청장 발신 명의가 도출되는 A4 PDF 공문서를 다운로드하여 관공서 내부 결재용으로 즉시 사용하실 수 있습니다.', false)
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
            "created_at": r[5].strftime("%Y-%m-%d %H:%M") if r[5] else ""
        }
        for r in rows
    ]

@router.post("/notices")
async def create_notice(req: NoticeCreateRequest, db: Session = Depends(get_db)):
    ensure_board_tables(db)
    db.execute(text("""
        INSERT INTO system_notices (title, content, is_pinned, author)
        VALUES (:title, :content, :is_pinned, '시스템 최고 관리자')
    """), {"title": req.title, "content": req.content, "is_pinned": req.is_pinned})
    db.commit()
    return {"message": "공지사항이 성공적으로 등록되었습니다."}

@router.put("/notices/{notice_id}")
async def update_notice(notice_id: int, req: NoticeUpdateRequest, db: Session = Depends(get_db)):
    ensure_board_tables(db)
    result = db.execute(text("""
        UPDATE system_notices 
        SET title = :title, content = :content, is_pinned = :is_pinned 
        WHERE id = :id
    """), {"title": req.title, "content": req.content, "is_pinned": req.is_pinned, "id": notice_id})
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="해당 공지사항을 찾을 수 없습니다.")
    return {"message": "공지사항이 수정되었습니다."}

@router.delete("/notices/{notice_id}")
async def delete_notice(notice_id: int, db: Session = Depends(get_db)):
    ensure_board_tables(db)
    result = db.execute(text("DELETE FROM system_notices WHERE id = :id"), {"id": notice_id})
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="해당 공지사항을 찾을 수 없습니다.")
    return {"message": "공지사항이 삭제되었습니다."}

@router.get("/community")
async def get_community_posts(db: Session = Depends(get_db)):
    ensure_board_tables(db)
    try:
        rows = db.execute(text("SELECT id, title, content, author_name, department, views_count, created_at FROM community_posts ORDER BY id DESC")).fetchall()
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
            rows = db.execute(text("SELECT id, title, content, author_name, department, views_count, created_at FROM community_posts ORDER BY id DESC")).fetchall()
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
            "created_at": r[6].strftime("%Y-%m-%d %H:%M") if r[6] else ""
        }
        for r in rows
    ]

@router.post("/community")
async def create_community_post(req: PostCreateRequest, db: Session = Depends(get_db)):
    ensure_board_tables(db)
    db.execute(text("""
        INSERT INTO community_posts (title, content, author_name, department)
        VALUES (:title, :content, :author_name, :department)
    """), {
        "title": req.title,
        "content": req.content,
        "author_name": req.author_name,
        "department": req.department
    })
    db.commit()
    return {"message": "자유게시판 게시글이 성공적으로 등록되었습니다."}

@router.delete("/community/{post_id}")
async def delete_community_post(post_id: int, db: Session = Depends(get_db)):
    ensure_board_tables(db)
    result = db.execute(text("DELETE FROM community_posts WHERE id = :id"), {"id": post_id})
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="해당 게시글을 찾을 수 없습니다.")
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
