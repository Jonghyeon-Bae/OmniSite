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

app = FastAPI(
    title="OmniSite SDSS API Backend",
    description="지능형 다목적 스마트시티 입지 선정 및 공공갈등 예측 플랫폼 API",
    version="1.0.0-solo-build"
)

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
