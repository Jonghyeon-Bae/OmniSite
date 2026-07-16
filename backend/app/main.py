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

app = FastAPI(
    title="OmniSite SDSS API Backend",
    description="지능형 다목적 스마트시티 입지 선정 및 공공갈등 예측 플랫폼 API",
    version="1.0.0-solo-build"
)

# 라우터 등록
app.include_router(auth_router)
app.include_router(upload_router)
app.include_router(ahp_router)
app.include_router(spatial_router)
app.include_router(model_router)

# Next.js 연동을 위한 CORS 미들웨어 개설 (CORS_ORIGINS 환경변수 파싱 적용)
cors_origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
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
