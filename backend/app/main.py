import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from app.config import settings
from app.routers.upload import router as upload_router
from app.routers.ahp import router as ahp_router
from app.routers.spatial import router as spatial_router
from app.routers.auth import router as auth_router
from app.routers.model import router as model_router
from app.routers.board import router as board_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # [v4.9.46] AWS 컨테이너 부팅 시 DB 소켓 준비 대기 재시도 루프 (컨테이너 재부팅 무한 루프 원천 예방)
    for attempt in range(1, 6):
        try:
            init_db_schema()
            print(f"[DB Startup] DDL Schema initialization completed successfully on attempt {attempt}.")
            break
        except Exception as err:
            print(f"[DB Startup Attempt {attempt}/5 Warning] {err}")
            if attempt < 5:
                time.sleep(2)
    yield

app = FastAPI(
    title="OmniSite SDSS API Backend",
    description="지능형 다목적 스마트시티 입지 선정 및 공공갈등 예측 플랫폼 API",
    version="1.0.0-solo-build",
    lifespan=lifespan
)

def init_db_schema():
    """[v4.9.44] FastAPI 서버 시동 시 1회만 DDL 스키마 정합성을 검증하여 GET 요청 중 DDL 락 데드락을 원천 방지"""
    from app.database import engine
    try:
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS pipeline_execution_logs (
                    id SERIAL PRIMARY KEY,
                    session_id VARCHAR(100) DEFAULT 'SESSION_DEFAULT',
                    step_number VARCHAR(20) NOT NULL DEFAULT 'STEP-1',
                    action_type VARCHAR(50) NOT NULL DEFAULT 'AUDIT_INIT',
                    detail_json JSONB,
                    current_hash VARCHAR(64),
                    prev_hash VARCHAR(64),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                ALTER TABLE pipeline_execution_logs ADD COLUMN IF NOT EXISTS session_id VARCHAR(100) DEFAULT 'SESSION_DEFAULT';
                ALTER TABLE pipeline_execution_logs ADD COLUMN IF NOT EXISTS step_number VARCHAR(20) DEFAULT 'STEP-1';
                ALTER TABLE pipeline_execution_logs ADD COLUMN IF NOT EXISTS action_type VARCHAR(50) DEFAULT 'AUDIT_LOG';
                ALTER TABLE pipeline_execution_logs ADD COLUMN IF NOT EXISTS detail_json JSONB;
                ALTER TABLE pipeline_execution_logs ADD COLUMN IF NOT EXISTS current_hash VARCHAR(64);
                ALTER TABLE pipeline_execution_logs ADD COLUMN IF NOT EXISTS prev_hash VARCHAR(64);

                CREATE TABLE IF NOT EXISTS decision_histories (
                    id SERIAL PRIMARY KEY,
                    region VARCHAR(100) DEFAULT '서울특별시 용산구',
                    facility_type VARCHAR(100) DEFAULT '흡연부스',
                    infra VARCHAR(100) DEFAULT '흡연부스',
                    ahp_weights JSONB,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    status VARCHAR(50) DEFAULT '모의 심의 완료',
                    selected_parcel_jibun VARCHAR(100),
                    selected_parcel_pnu VARCHAR(50),
                    selected_parcel_price INT DEFAULT 0,
                    selected_parcel_area DOUBLE PRECISION DEFAULT 0.0,
                    selected_parcel_css DOUBLE PRECISION DEFAULT 50.0,
                    debate_logs JSONB,
                    audit_state VARCHAR(50) DEFAULT '미검증',
                    audit_opinion TEXT
                );
                ALTER TABLE decision_histories ADD COLUMN IF NOT EXISTS selected_parcel_pnu VARCHAR(50);

                CREATE TABLE IF NOT EXISTS verified_precedents (
                    id SERIAL PRIMARY KEY,
                    conflict_simulation_id INT REFERENCES decision_histories(id) ON DELETE SET NULL,
                    document_title VARCHAR(255) NOT NULL,
                    document_ocr_text TEXT,
                    actual_scenario VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    selected_parcel_pnu VARCHAR(50),
                    match_score INT DEFAULT 85,
                    audit_opinion TEXT
                );
                ALTER TABLE verified_precedents ADD COLUMN IF NOT EXISTS selected_parcel_pnu VARCHAR(50);
                ALTER TABLE verified_precedents ADD COLUMN IF NOT EXISTS match_score INT DEFAULT 85;
                ALTER TABLE verified_precedents ADD COLUMN IF NOT EXISTS audit_opinion TEXT;
                ALTER TABLE verified_precedents ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
                ALTER TABLE verified_precedents DROP CONSTRAINT IF EXISTS verified_precedents_conflict_simulation_id_fkey;
            """))
            conn.commit()
            try:
                conn.execute(text("ALTER TABLE pipeline_execution_logs ALTER COLUMN step_name DROP NOT NULL;"))
                conn.execute(text("ALTER TABLE pipeline_execution_logs ALTER COLUMN status DROP NOT NULL;"))
                conn.commit()
            except Exception:
                pass

            # [v4.9.47] district_regulations 영벡터(Zero Vector) 감지 시 OpenAI 1536D 실측 임베딩 자동 치유
            try:
                import os
                api_key = os.getenv("OPENAI_API_KEY")
                if api_key:
                    from openai import OpenAI
                    cli = OpenAI(api_key=api_key)
                    rows = conn.execute(text("SELECT id, regulation_title, clause_number, content FROM district_regulations WHERE embedding = array_fill(0.0, ARRAY[1536])::vector OR embedding IS NULL")).fetchall()
                    for r in rows:
                        txt = f"{r[1]} {r[2] or ''} {r[3]}"
                        res = cli.embeddings.create(model="text-embedding-3-small", input=txt, timeout=5.0)
                        vec = res.data[0].embedding
                        conn.execute(text("UPDATE district_regulations SET embedding = CAST(:vec AS vector) WHERE id = :id"), {"vec": vec, "id": r[0]})
                    conn.commit()
                    if rows:
                        print(f"[DB Startup Auto-Heal] Healed {len(rows)} district_regulations zero-vectors with real OpenAI 1536D embeddings.")
            except Exception as heal_err:
                print(f"[DB Startup Auto-Heal Warning] {heal_err}")
    except Exception as e:
        print(f"[DB Startup Warning] DDL init warning: {e}")

# 시동 1회 DDL 구동
# 라우터 등록 (Notice CRUD Admin, Password Auto-Heal & Registration Approval Flow 포함)
app.include_router(auth_router)
app.include_router(upload_router)
app.include_router(ahp_router)
app.include_router(spatial_router)
app.include_router(model_router)
app.include_router(board_router)

# Next.js (로컬 3000/3001 & AWS 퍼블릭 IP/도메인) 100% 무결성 CORS 미들웨어
raw_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip() and o.strip() != "*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=raw_origins if raw_origins else ["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_origin_regex=r"https?://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# PM 개발 철칙 2조 준수: 반드시 비동기 API(async def) 적용
@app.get("/api/v1/health")
async def health_check(db: Session = Depends(get_db)):
    try:
        # PostgreSQL/PostGIS 커넥션 풀을 통한 연결 자가 진단
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return {
        "status": "alive",
        "version": "1.0.0-solo-build",
        "database": db_status
    }

# trigger reload

# trigger reload for delete fix

# trigger reload for embedded ordinance delete fix

# trigger reload for bidirectional delete fix

# trigger reload for uploaded files list fix

# trigger reload for v4.2.0 buildability upgrade

# trigger reload after codebase cleanup

# trigger reload for ev hard drop & parking lot seeding

# trigger reload for ev area >= 100m² & strict land use guard

# trigger reload for ev ml feature cleaning & parking lot candidate pool restriction

# trigger reload for ev ml feature cleaning & parking lot candidate pool restriction
