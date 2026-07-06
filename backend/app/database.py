from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

# SQLAlchemy DB 커넥션 풀 설정
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# FastAPI 의존성 주입 패턴에 따른 DB 세션 제네레이터 (PM 개발 철칙 준수)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
