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


def init_system_settings(db):
    from sqlalchemy import text
    try:
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS system_settings (
                key VARCHAR(100) PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        db.commit()
        
        row = db.execute(text("SELECT value FROM system_settings WHERE key = 'MASTER_SECURITY_KEY'")).fetchone()
        if not row:
            db.execute(text("INSERT INTO system_settings (key, value) VALUES ('MASTER_SECURITY_KEY', 'OMNISITE-MASTER-2026')"))
            db.commit()
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        print(f"[DB Init Error] system_settings init failed: {e}")

def get_system_setting(db, key: str, default_val: str = "") -> str:
    from sqlalchemy import text
    try:
        init_system_settings(db)
        row = db.execute(text("SELECT value FROM system_settings WHERE key = :k"), {"k": key}).fetchone()
        return row[0] if (row and row[0]) else default_val
    except Exception:
        return default_val

def set_system_setting(db, key: str, value: str):
    from sqlalchemy import text
    try:
        init_system_settings(db)
        db.execute(text("""
            INSERT INTO system_settings (key, value, updated_at)
            VALUES (:k, :v, CURRENT_TIMESTAMP)
            ON CONFLICT (key) DO UPDATE SET value = :v, updated_at = CURRENT_TIMESTAMP
        """), {"k": key, "v": value})
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        print(f"[System Settings Error] Failed to set {key}: {e}")
        return False
