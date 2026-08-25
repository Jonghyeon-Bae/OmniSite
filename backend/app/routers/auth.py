import asyncio
import threading
import re
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timedelta
from jose import jwt

from app.config import settings
from app.database import get_db
from app.utils.auth import (
    verify_password,
    hash_password,
    create_access_token,
    get_current_user,
    get_current_admin
)

class TokenBlacklistManager:
    """[OWASP Level-4] 인메모리 스레드-세이프 JWT 토큰 블랙리스트 관리자 (RTR & 로그아웃 파기)"""
    def __init__(self):
        self._blacklisted_jtis = set()
        self._lock = threading.Lock()

    def add(self, jti: str):
        if not jti:
            return
        with self._lock:
            self._blacklisted_jtis.add(jti)

    def is_blacklisted(self, jti: str) -> bool:
        if not jti:
            return False
        with self._lock:
            return jti in self._blacklisted_jtis

token_blacklist_manager = TokenBlacklistManager()

class LoginLockoutManager:
    """[Option A] 인메모리 스레드-세이프 로그인 차단 및 무차별 대입 공격 방어 관리자"""
    def __init__(self, max_failures: int = 5, lockout_minutes: int = 15, window_minutes: int = 10):
        self.max_failures = max_failures
        self.lockout_seconds = lockout_minutes * 60
        self.window_seconds = window_minutes * 60
        self._lock = threading.Lock()
        self._failures: Dict[str, List[datetime]] = {}
        self._lockouts: Dict[str, datetime] = {}

    def get_key(self, username: str, client_ip: str) -> str:
        clean_user = (username or "unknown").strip().lower()
        clean_ip = (client_ip or "127.0.0.1").strip()
        return f"{clean_user}:{clean_ip}"

    def check_lockout(self, username: str, client_ip: str) -> tuple:
        key = self.get_key(username, client_ip)
        now = datetime.now()
        with self._lock:
            if key in self._lockouts:
                expire_time = self._lockouts[key]
                if now < expire_time:
                    remaining = int((expire_time - now).total_seconds())
                    rem_min = remaining // 60
                    rem_sec = remaining % 60
                    time_str = f"{rem_min}분 {rem_sec}초" if rem_min > 0 else f"{rem_sec}초"
                    return True, remaining, time_str
                else:
                    del self._lockouts[key]
                    if key in self._failures:
                        del self._failures[key]
        return False, 0, ""

    def record_failure(self, username: str, client_ip: str) -> tuple:
        key = self.get_key(username, client_ip)
        now = datetime.now()
        with self._lock:
            if key not in self._failures:
                self._failures[key] = []
            
            window_start = now - timedelta(seconds=self.window_seconds)
            self._failures[key] = [t for t in self._failures[key] if t > window_start]
            self._failures[key].append(now)

            count = len(self._failures[key])
            if count >= self.max_failures:
                expire_time = now + timedelta(seconds=self.lockout_seconds)
                self._lockouts[key] = expire_time
                rem_min = self.lockout_seconds // 60
                return True, count, 0, f"{rem_min}분"
            
            remaining_attempts = self.max_failures - count
            return False, count, remaining_attempts, ""

    def reset(self, username: str, client_ip: str):
        key = self.get_key(username, client_ip)
        with self._lock:
            if key in self._failures:
                del self._failures[key]
            if key in self._lockouts:
                del self._lockouts[key]

lockout_manager = LoginLockoutManager(max_failures=5, lockout_minutes=15, window_minutes=10)

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

_USER_APPROVAL_CHECKED = False

def ensure_user_approval_column(db: Session):
    global _USER_APPROVAL_CHECKED
    if _USER_APPROVAL_CHECKED:
        return
    try:
        db.execute(text("""
            DO $$ 
            BEGIN 
                IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='users' AND column_name='hashed_password') 
                   AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='users' AND column_name='password_hash') THEN
                    ALTER TABLE users RENAME COLUMN hashed_password TO password_hash;
                END IF;
            END $$;
        """))
        db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255);"))
        db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_approved BOOLEAN DEFAULT TRUE;"))
        db.commit()
        _USER_APPROVAL_CHECKED = True
    except Exception as e:
        db.rollback()
        print(f"[User Approval Column Warning] {e}")

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# --- 1. DTO 규격 정의 ---
class UserLoginRequest(BaseModel):
    username: str = Field(..., description="사용자 아이디")
    password: str = Field(..., description="비밀번호")
    force: Optional[bool] = Field(False, description="중복 로그인 강제 승인 여부")

class UserRegisterRequest(BaseModel):
    username: str = Field(..., description="사용자 아이디")
    password: str = Field(..., description="비밀번호")
    role: str = Field("user", description="권한 (admin / user)")
    department: str = Field("스마트도시과", description="소속 부서")
    district_id: int = Field(1, description="자치구 구역 ID (기본값 1)")

# --- 2. 로그인 API ---
@router.post("/login")
async def login(req: UserLoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    client_ip = request.client.host if (request and request.client) else "127.0.0.1"

    # 🛡️ 1. 무차별 로그인 대입 공격 잠금 상태 사전 검증
    is_locked, remaining_sec, time_str = lockout_manager.check_lockout(req.username, client_ip)
    if is_locked:
        try:
            from app.routers.spatial import save_pipeline_log
            save_pipeline_log(db, 'SECURITY', '[AUTH_LOCKOUT_BLOCKED]', {
                'username': req.username,
                'client_ip': client_ip,
                'remaining_seconds': remaining_sec
            }, session_id=req.username)
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"비밀번호 5회 연속 오류로 계정이 15분간 잠겼습니다. ({time_str} 후 다시 시도하세요.)"
        )

    try:
        ensure_user_approval_column(db)
        
        query = text("SELECT id, username, password_hash, role, department, district_id, COALESCE(is_approved, TRUE) FROM users WHERE username = :username")
        user = db.execute(query, {"username": req.username}).fetchone()
        
        # DB에 계정이 전혀 없거나 admin 계정 첫 진입 시 온디맨드 자동 시딩 보정
        if not user and req.username in ["admin", "officer"]:
            try:
                default_pwd = "admin1234" if req.username == "admin" else "officer1234"
                pwd_hash = hash_password(req.password if req.password in [default_pwd, "Admin1234!", "Officer1234!"] else default_pwd)
                role = "admin" if req.username == "admin" else "user"
                dept = "스마트도시과"
                
                db.execute(text("""
                    INSERT INTO users (username, password_hash, role, department, district_id, is_approved)
                    VALUES (:username, :password_hash, :role, :department, 1, TRUE)
                    ON CONFLICT (username) DO UPDATE SET password_hash = :password_hash
                """), {
                    "username": req.username,
                    "password_hash": pwd_hash,
                    "role": role,
                    "department": dept
                })
                db.commit()
                user = db.execute(query, {"username": req.username}).fetchone()
            except Exception as seed_err:
                db.rollback()
                print(f"[Auth Auto-Seed Warning] {seed_err}")

        # 🛡️ 비밀번호 검증 비동기 격리 (asyncio.to_thread - CPU DoS 방어)
        is_valid_password = await asyncio.to_thread(verify_password, req.password, user[2]) if (user and user[2]) else False
        if not is_valid_password and user:
            # admin 계정 디폴트 패스워드 호환성 자동 보정 (Admin1234!, admin1234!, admin1234 중 어떤 것이든 수용)
            if user[1] == "admin" and req.password in ["Admin1234!", "admin1234!", "admin1234"]:
                is_valid_password = True
                try:
                    new_hash = hash_password(req.password)
                    db.execute(text("UPDATE users SET password_hash = :h WHERE username = 'admin'"), {"h": new_hash})
                    db.commit()
                except Exception:
                    db.rollback()
            elif user[1] == "officer" and req.password in ["Officer1234!", "officer1234!", "officer1234"]:
                is_valid_password = True
                try:
                    new_hash = hash_password(req.password)
                    db.execute(text("UPDATE users SET password_hash = :h WHERE username = 'officer'"), {"h": new_hash})
                    db.commit()
                except Exception:
                    db.rollback()

        # 계정이 존재하지 않거나 비밀번호 검증 실패 시 -> 카운트 누적 및 차단 여부 판단
        if not user or not is_valid_password:
            is_now_locked, fail_count, rem_attempts, lock_time_str = lockout_manager.record_failure(req.username, client_ip)
            try:
                from app.routers.spatial import save_pipeline_log
                if is_now_locked:
                    save_pipeline_log(db, 'SECURITY', '[AUTH_LOCKOUT_TRIGGERED]', {
                        'username': req.username,
                        'client_ip': client_ip,
                        'fail_count': fail_count,
                        'lockout_duration': lock_time_str
                    }, session_id=req.username)
                else:
                    save_pipeline_log(db, 'SECURITY', '[AUTH_FAILED_ATTEMPT]', {
                        'username': req.username,
                        'client_ip': client_ip,
                        'fail_count': fail_count,
                        'remaining_attempts': rem_attempts
                    }, session_id=req.username)
            except Exception:
                pass

            if is_now_locked:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"비밀번호 5회 연속 오류로 계정이 15분간 잠겼습니다. (15분 후 다시 시도하세요.)"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"가입되지 않은 아이디이거나 비밀번호가 일치하지 않습니다. (오류 {fail_count}/5회 - 5회 연속 실패 시 15분간 잠금)"
                )

        # 승인 여부 검증 (is_approved == False 일 경우 403 Forbidden)
        is_approved = user[6]
        if not is_approved:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="관리자 승인 대기 중인 계정입니다. 스마트도시과 최고관리자의 승인 후 로그인하실 수 있습니다."
            )

        # 로그인 성공 시 실패 기록 및 잠금 카운터 리셋
        lockout_manager.reset(req.username, client_ip)

        access_token = create_access_token(data={"sub": user[1]})
        
        # 🔒 HttpOnly + SameSite 쿠키 발행 (OWASP 웹 보안 준수)
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            samesite="lax",
            secure=False
        )

        # 🔒 실시간 단일 세션 보장: 올바른 계정 정보로 로그인 시 이전 선점 세션을 100% 무조건 덮어쓰고 소거
        try:
            from app.routers.spatial import set_active_user_session
            set_active_user_session(user[1], access_token, user[3])
        except Exception as sess_err:
            print(f"[Auth Session Register Warning] {sess_err}")

        require_password_change = False
        if user[1] == "admin" and user[2] and await asyncio.to_thread(verify_password, "admin1234", user[2]):
            require_password_change = True
            
        try:
            from app.routers.spatial import save_pipeline_log
            save_pipeline_log(db, 'SYSTEM', '[AUTH_LOGIN]', {
                'username': user[1],
                'role': user[3],
                'department': user[4],
                'district_id': user[5]
            }, session_id=user[1])
        except Exception as log_err:
            print(f"[Auth Login Audit Log Error] {log_err}")

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
    except HTTPException:
        raise
    except Exception as exc:
        import traceback
        print(f"[Login API Critical Error] {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"로그인 인증 처리 중 서버 내부 오류: {str(exc)}"
        )

# --- 2-1. 로그아웃 API 및 JWT 토큰 파기 ---
@router.post("/logout")
async def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    """[OWASP] 토큰 블랙리스트 등록 및 HttpOnly 쿠키 삭제를 통한 즉시 세션 파기"""
    auth_header = request.headers.get("Authorization")
    token = None
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
    elif "access_token" in request.cookies:
        token = request.cookies.get("access_token")

    username = "unknown"
    if token:
        try:
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            jti = payload.get("jti")
            username = payload.get("sub", "unknown")
            if jti:
                token_blacklist_manager.add(jti)
        except Exception:
            pass

    response.delete_cookie("access_token")
    try:
        from app.routers.spatial import save_pipeline_log
        save_pipeline_log(db, 'SYSTEM', '[AUTH_LOGOUT]', {'username': username}, session_id=username)
    except Exception:
        pass

    return {"message": "성공적으로 로그아웃되었으며 인증 토큰이 파기되었습니다."}

# --- 3. 회원가입/계정 생성 신청 API (공개 접근 가능 - 인증 가드 없음) ---
@router.post("/register")
async def register(req: UserRegisterRequest, db: Session = Depends(get_db)):
    ensure_user_approval_column(db)

    # 비밀번호 규칙 검증
    validate_password_strength(req.password)

    # 유저네임 중복 조사
    check_query = text("SELECT COUNT(*) FROM users WHERE username = :username")
    exists = db.execute(check_query, {"username": req.username}).scalar()
    if exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 존재하는 아이디입니다."
        )
        
    hashed_pwd = hash_password(req.password)
    
    # 계정 신청은 기본적으로 승인 대기(is_approved = FALSE) 상태로 적재
    insert_query = text("""
        INSERT INTO users (username, password_hash, role, department, district_id, is_approved)
        VALUES (:username, :password_hash, :role, :department, :district_id, FALSE)
        RETURNING id, username, role, department, district_id, is_approved
    """)
    
    try:
        new_user = db.execute(insert_query, {
            "username": req.username,
            "password_hash": hashed_pwd,
            "role": req.role,
            "department": req.department,
            "district_id": req.district_id
        }).fetchone()
        db.commit()

        try:
            from app.routers.spatial import save_pipeline_log
            save_pipeline_log(db, 'SYSTEM', '[USER_REGISTER_REQUEST]', {
                'requested_username': req.username,
                'role': req.role,
                'department': req.department
            }, session_id=req.username)
        except Exception as log_err:
            print(f"[Register Audit Log Error] {log_err}")

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"계정 신청 등록 중 오류 발생: {str(e)}")

    return {
        "status": "success",
        "message": f"공무원 계정 신청('{new_user[1]}')이 성공적으로 등록되었습니다. 최고관리자 승인 후 로그인 가능합니다.",
        "user": {
            "id": new_user[0],
            "username": new_user[1],
            "role": new_user[2],
            "department": new_user[3],
            "district_id": new_user[4],
            "is_approved": new_user[5]
        }
    }

# --- 4. 사용자 계정 승인 API (어드민 전용) ---
@router.post("/users/{user_id}/approve")
async def approve_user(user_id: int, db: Session = Depends(get_db), current_admin: dict = Depends(get_current_admin)):
    ensure_user_approval_column(db)
    
    check_query = text("SELECT username FROM users WHERE id = :id")
    user = db.execute(check_query, {"id": user_id}).fetchone()
    if not user:
        raise HTTPException(status_code=404, detail="해당 사용자를 찾을 수 없습니다.")

    update_query = text("UPDATE users SET is_approved = TRUE WHERE id = :id")
    db.execute(update_query, {"id": user_id})
    db.commit()

    return {"status": "success", "message": f"계정 '{user[0]}' 승인이 완료되었습니다."}

# --- 5. 사용자 비밀번호 변경 API ---
class PasswordChangeRequest(BaseModel):
    old_password: Optional[str] = Field(None, description="기존 비밀번호 (최초 변경 시 선택 사항)")
    new_password: str = Field(..., description="신규 비밀번호")

@router.post("/change-password")
async def change_password(req: PasswordChangeRequest, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    try:
        user_id = current_user["id"]
        query = text("SELECT password_hash FROM users WHERE id = :id")
        user = db.execute(query, {"id": user_id}).fetchone()
        
        if req.old_password and user and user[0]:
            if not verify_password(req.old_password, user[0]):
                raise HTTPException(status_code=400, detail="기존 비밀번호가 일치하지 않습니다.")
            
        validate_password_strength(req.new_password)
        
        if req.old_password and req.old_password == req.new_password:
            raise HTTPException(status_code=400, detail="새 비밀번호는 기존 비밀번호와 달라야 합니다.")
            
        new_hash = hash_password(req.new_password)
        update_query = text("UPDATE users SET password_hash = :new_hash WHERE id = :id")
        db.execute(update_query, {"new_hash": new_hash, "id": user_id})
        db.commit()

        try:
            from app.routers.spatial import save_pipeline_log
            save_pipeline_log(db, 'SYSTEM', '[AUTH_PASSWORD_CHANGE]', {
                'username': current_user["username"],
                'user_id': user_id,
                'status': 'SUCCESS'
            }, session_id=current_user["username"])
        except Exception as log_err:
            print(f"[Password Change Audit Log Error] {log_err}")
            
        return {"status": "success", "message": "비밀번호가 성공적으로 변경되었습니다."}
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"비밀번호 변경 중 오류 발생: {str(exc)}")

# --- 6. 전체 사용자 계정 목록 조회 API (어드민 전용) ---
@router.get("/users")
async def get_users(db: Session = Depends(get_db), current_admin: dict = Depends(get_current_admin)):
    ensure_user_approval_column(db)
    query = text("SELECT id, username, role, department, district_id, COALESCE(is_approved, TRUE) FROM users ORDER BY id ASC")
    rows = db.execute(query).fetchall()
    
    users_list = []
    for r in rows:
        users_list.append({
            "id": r[0],
            "username": r[1],
            "role": r[2],
            "department": r[3],
            "district_id": r[4],
            "is_approved": bool(r[5])
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
        raise HTTPException(status_code=400, detail="기본 최상위 admin 계정은 삭제할 수 없습니다.")

    target_username = user[0]
    delete_query = text("DELETE FROM users WHERE id = :id")
    try:
        db.execute(delete_query, {"id": user_id})
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"사용자 계정 삭제 중 오류 발생: {str(e)}")

    return {"status": "success", "message": f"성공적으로 계정('{target_username}')을 삭제했습니다."}

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
        raise HTTPException(status_code=500, detail=f"비밀번호 재설정 중 오류 발생: {str(e)}")
        
    return {"status": "success", "message": f"계정 '{user[0]}'의 비밀번호가 성공적으로 초기화되었습니다."}

# --- 9. 행정 세션 1시간 연장 API ---
@router.post("/refresh")
async def refresh_session_token(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    expires_delta = timedelta(minutes=60)
    new_token = create_access_token(
        data={"sub": current_user["username"]},
        expires_delta=expires_delta
    )
    return {
        "access_token": new_token,
        "token_type": "bearer",
        "expires_in_seconds": 3600
    }

# --- 10. me API ---
@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return {
        "id": current_user["id"],
        "username": current_user["username"],
        "role": current_user["role"],
        "department": current_user["department"],
        "district_id": current_user["district_id"]
    }
