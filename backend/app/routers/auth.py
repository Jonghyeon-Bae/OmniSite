from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import timedelta

import re
from app.database import get_db
from app.utils.auth import (
    verify_password,
    hash_password,
    create_access_token,
    get_current_user,
    get_current_admin
)

def validate_password_strength(password: str) -> None:
    if not password or len(password) < 8:
        raise HTTPException(
            status_code=400,
            detail="비밀번호는 최소 8자리 이상이어야 합니다."
        )
    has_letter = bool(re.search(r"[A-Za-z]", password))
    has_digit = bool(re.search(r"\d", password))
    has_special = bool(re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?]", password))
    
    if not (has_letter and has_digit and has_special):
        raise HTTPException(
            status_code=400,
            detail="비밀번호는 영문, 숫자, 특수문자를 모두 포함하여 8자리 이상이어야 합니다."
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
    
    # 최초 로그인 패스워드 강제 변경 필요 여부 검사
    # 사용자가 'admin'이고 디폴트 비밀번호인 'admin1234'로 로그인한 경우 강제 변경 대상
    require_password_change = False
    if user[1] == "admin" and verify_password("admin1234", user[2]):
        require_password_change = True
        
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "require_password_change": require_password_change,
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
    # 신규 비밀번호 규칙(영문+숫자+특수문자 8자 이상) 검증
    validate_password_strength(req.password)

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

# --- 5. 비밀번호 자가 변경 API ---
class PasswordChangeRequest(BaseModel):
    old_password: str = Field(..., description="기존 비밀번호")
    new_password: str = Field(..., description="새로운 비밀번호")

@router.post("/change-password")
async def change_password(req: PasswordChangeRequest, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    validate_password_strength(req.new_password)
    query = text("SELECT password_hash FROM users WHERE username = :username")
    row = db.execute(query, {"username": current_user["username"]}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
        
    if not verify_password(req.old_password, row[0]):
        raise HTTPException(status_code=400, detail="기존 비밀번호가 일치하지 않습니다.")
        
    new_hash = hash_password(req.new_password)
    update_query = text("UPDATE users SET password_hash = :new_hash WHERE username = :username")
    try:
        db.execute(update_query, {"new_hash": new_hash, "username": current_user["username"]})
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"비밀번호 변경 중 오류가 발생했습니다: {str(e)}")
        
    return {"status": "success", "message": "비밀번호가 성공적으로 변경되었습니다."}

# --- 6. 전체 사용자 계정 목록 조회 API (어드민 전용) ---
@router.get("/users")
async def get_users(db: Session = Depends(get_db), current_admin: dict = Depends(get_current_admin)):
    query = text("SELECT id, username, role, department, district_id FROM users ORDER BY id ASC")
    rows = db.execute(query).fetchall()
    
    users_list = []
    for r in rows:
        users_list.append({
            "id": r[0],
            "username": r[1],
            "role": r[2],
            "department": r[3],
            "district_id": r[4]
        })
    return users_list

# --- 7. 사용자 계정 삭제 API (어드민 전용) ---
@router.delete("/users/{user_id}")
async def delete_user(user_id: int, db: Session = Depends(get_db), current_admin: dict = Depends(get_current_admin)):
    if current_admin["id"] == user_id:
        raise HTTPException(status_code=400, detail="자기 자신의 관리자 계정은 삭제할 수 없습니다.")
        
    check_query = text("SELECT username FROM users WHERE id = :id")
    user = db.execute(check_query, {"id": user_id}).fetchone()
    if not user:
        raise HTTPException(status_code=404, detail="해당 사용자를 찾을 수 없습니다.")
        
    if user[0] == "admin":
        raise HTTPException(status_code=400, detail="시스템 기본 최고 관리자 계정('admin')은 삭제할 수 없습니다.")
        
    delete_query = text("DELETE FROM users WHERE id = :id")
    try:
        db.execute(delete_query, {"id": user_id})
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"사용자 삭제 중 오류가 발생했습니다: {str(e)}")
        
    return {"status": "success", "message": f"계정 '{user[0]}'이 성공적으로 삭제되었습니다."}

# --- 8. 사용자 패스워드 강제 초기화 API (어드민 전용) ---
class PasswordResetRequest(BaseModel):
    new_password: str = Field(..., description="재설정할 신규 비밀번호")

@router.post("/users/{user_id}/reset-password")
async def reset_user_password(user_id: int, req: PasswordResetRequest, db: Session = Depends(get_db), current_admin: dict = Depends(get_current_admin)):
    validate_password_strength(req.new_password)
    check_query = text("SELECT username FROM users WHERE id = :id")
    user = db.execute(check_query, {"id": user_id}).fetchone()
    if not user:
        raise HTTPException(status_code=404, detail="해당 사용자를 찾을 수 없습니다.")
        
    new_hash = hash_password(req.new_password)
    update_query = text("UPDATE users SET password_hash = :new_hash WHERE id = :id")
    try:
        db.execute(update_query, {"new_hash": new_hash, "id": user_id})
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"비밀번호 재설정 중 오류가 발생했습니다: {str(e)}")
        
    return {"status": "success", "message": f"계정 '{user[0]}'의 비밀번호가 성공적으로 초기화되었습니다."}
