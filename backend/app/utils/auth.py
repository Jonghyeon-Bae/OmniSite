import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.config import settings
from app.database import get_db

# OAuth2PasswordBearer를 통해 HTTP Authorization Bearer 토큰 획득 설정
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

# --- 1. Bcrypt Raw 패스워드 암호화 및 검증 ---
def hash_password(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    pwd_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    try:
        return bcrypt.checkpw(pwd_bytes, hashed_bytes)
    except Exception:
        return False

# --- 2. JWT Access Token 발급 ---
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

# --- 3. 현재 로그인된 유저 검증 의존성 (Depends) ---
async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> Dict[str, Any]:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="사용자 인증 토큰이 유효하지 않거나 만료되었습니다.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # JWT 디코딩
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # DB에서 해당 사용자 쿼리
    query = text("SELECT id, username, role, department, district_id FROM users WHERE username = :username")
    user_row = db.execute(query, {"username": username}).fetchone()
    
    if user_row is None:
        raise credentials_exception
        
    return {
        "id": user_row[0],
        "username": user_row[1],
        "role": user_row[2],
        "department": user_row[3],
        "district_id": user_row[4]
    }

# --- 4. 어드민(Admin) 권한 제한 의존성 (Depends) ---
async def get_current_admin(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="본 기능은 시스템 관리자(Admin) 권한이 요구되는 작업입니다."
        )
    return current_user
