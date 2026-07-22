import os
import sys
from sqlalchemy import text
import bcrypt

# 로컬 임포트를 위한 sys.path 보정 (backend 폴더를 PYTHONPATH에 추가)
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_root = os.path.dirname(os.path.dirname(current_dir)) # c:/.../backend
sys.path.append(backend_root)

from app.database import engine

def hash_password(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode('utf-8')

def run_migration():
    create_users_table_query = """
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(50) UNIQUE NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        role VARCHAR(20) DEFAULT 'user',
        department VARCHAR(100),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    # 1. users 테이블 신설 DDL 실행
    with engine.begin() as conn:
        conn.execute(text(create_users_table_query))
        print("[Migration] users table checked/created successfully.")
        
        # 2. 기존 시드 계정이 존재하지 않는지 체크 후 적재
        check_user_query = text("SELECT COUNT(*) FROM users WHERE username = :username")
        
        # admin 계정 시딩
        admin_exists = conn.execute(check_user_query, {"username": "admin"}).scalar()
        if not admin_exists:
            hashed_admin_pwd = hash_password("admin1234")
            insert_admin_query = text("""
                INSERT INTO users (username, password_hash, role, department)
                VALUES (:username, :password_hash, :role, :department)
            """)
            conn.execute(insert_admin_query, {
                "username": "admin",
                "password_hash": hashed_admin_pwd,
                "role": "admin",
                "department": "도시행정정보과"
            })
            print("[Migration] Default admin seed user created.")
            
        # officer 계정 시딩
        officer_exists = conn.execute(check_user_query, {"username": "officer"}).scalar()
        if not officer_exists:
            hashed_officer_pwd = hash_password("officer1234")
            insert_officer_query = text("""
                INSERT INTO users (username, password_hash, role, department)
                VALUES (:username, :password_hash, :role, :department)
            """)
            conn.execute(insert_officer_query, {
                "username": "officer",
                "password_hash": hashed_officer_pwd,
                "role": "user",
                "department": "스마트도시과"
            })
            print("[Migration] Default officer seed user created.")

if __name__ == "__main__":
    run_migration()
