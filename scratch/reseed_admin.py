import bcrypt
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql+psycopg://Admin:admin1234@localhost:5432/postgres"
engine = create_engine(DATABASE_URL)

pwd_bytes = "admin1234".encode('utf-8')
salt = bcrypt.gensalt()
hashed = bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')

with engine.connect() as conn:
    conn.execute(text("""
        INSERT INTO users (username, password_hash, role, department, district_id)
        VALUES ('admin', :pwd_hash, 'admin', '스마트도시과', 1)
        ON CONFLICT (username) DO UPDATE SET password_hash = :pwd_hash
    """), {"pwd_hash": hashed})
    conn.commit()
    print("Admin password reset successfully.")
