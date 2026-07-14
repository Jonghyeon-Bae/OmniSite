from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import timedelta

from app.database import get_db
from app.utils.auth import (
    verify_password,
    hash_password,
    create_access_token,
    get_current_user,
    get_current_admin
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# --- 1. DTO 규격 정의 ---
class UserLoginRequest(BaseModel):
    username: str = Field(..., description="사용자 아이디")
    password: str = Field(..., description="비밀번호")

class UserRegisterRequest(BaseModel):
    username: str = Field(..., description="사용자 아이디")
    password: str = Field(..., description="비밀번호")
    role: str = Field("user", description="권한 (admin / user)")
    department: str = Field("스마트도시과", description="소속 부서")
    district_id: int = Field(1, description="자치구 구역 ID (기본값 1)")

# --- 2. 로그인 API ---
@router.post("/login")
async def login(req: UserLoginRequest, db: Session = Depends(get_db)):
    # DB에서 아이디 쿼리
    query = text("SELECT id, username, password_hash, role, department, district_id FROM users WHERE username = :username")
    user = db.execute(query, {"username": req.username}).fetchone()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="가입되지 않은 아이디이거나 비밀번호가 일치하지 않습니다."
        )
    
    # 비밀번호 검증
    if not verify_password(req.password, user[2]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="가입되지 않은 아이디이거나 비밀번호가 일치하지 않습니다."
        )
        
    # JWT Access Token 토큰 발급 (username을 sub 클레임으로 주입)
    access_token = create_access_token(data={"sub": user[1]})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "username": user[1],
            "role": user[3],
            "department": user[4],
            "district_id": user[5]
        }
    }

# --- 3. 회원가입 API (관리자 가드 걸어둠: 어드민만 신규 가입 등록 가능) ---
@router.post("/register")
async def register(req: UserRegisterRequest, db: Session = Depends(get_db), current_admin: dict = Depends(get_current_admin)):
    # 기존 유저네임 중복 조사
    check_query = text("SELECT COUNT(*) FROM users WHERE username = :username")
    exists = db.execute(check_query, {"username": req.username}).scalar()
    if exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 존재하는 아이디입니다."
        )
        
    # 비밀번호 단방향 bcrypt 해싱
    hashed_pwd = hash_password(req.password)
    
    insert_query = text("""
        INSERT INTO users (username, password_hash, role, department, district_id)
        VALUES (:username, :password_hash, :role, :department, :district_id)
        RETURNING id, username, role, department, district_id
    """)
    
    try:
        with db.begin_nested(): # 트랜잭션 세이브포인트 유연 통제
            new_user = db.execute(insert_query, {
                "username": req.username,
                "password_hash": hashed_pwd,
                "role": req.role,
                "department": req.department,
                "district_id": req.district_id
            }).fetchone()
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"회원 가입 처리 중 데이터베이스 오류가 발생했습니다: {str(e)}"
        )
        
    return {
        "message": "신규 사용자 등록 성공",
        "user": {
            "id": new_user[0],
            "username": new_user[1],
            "role": new_user[2],
            "department": new_user[3],
            "district_id": new_user[4]
        }
    }

# --- 4. 프로필 정보 획득 API ---
@router.get("/me")
async def read_users_me(current_user: dict = Depends(get_current_user)):
    return current_user
