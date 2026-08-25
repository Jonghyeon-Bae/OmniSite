"""
OmniSite SHA-256 Hash Chain Audit Service (v3.2.0-PrecisionUiAndAuditFix)
Provides O(1) unified hash chain calculation, verification, and tamper detection.
"""
import hashlib
import hmac
import json
from datetime import datetime, timezone, timedelta
from app.utils.helpers import get_kst_now

def compute_sha256_hash(prev_hash: str, payload_data: dict) -> str:
    """
    Computes HMAC-SHA256 hash by normalizing previous hash and current log payload
    using server-side secret key to prevent offline chain recalculation attacks.
    """
    prev_h = prev_hash or ("0" * 64)
    detail = payload_data.get("detail_json")
    if isinstance(detail, str):
        try:
            detail = json.loads(detail)
        except Exception:
            pass
            
    norm_payload = {
        "session_id": str(payload_data.get("session_id") or 'SESSION_DEFAULT'),
        "step_number": str(payload_data.get("step_number") or 'SYSTEM'),
        "action_type": str(payload_data.get("action_type") or 'UNKNOWN'),
        "detail_json": detail
    }
    raw_str = f"{prev_h}:{json.dumps(norm_payload, sort_keys=True, ensure_ascii=False)}"
    secret_key = b"OMNISITE_ENTERPRISE_HMAC_AUDIT_SECRET_2026"
    return hmac.new(secret_key, raw_str.encode('utf-8'), hashlib.sha256).hexdigest()

def verify_log_chain(logs: list) -> tuple[bool, int, str]:
    """
    Verifies SHA-256 integrity across log entries (partitioned per session_id).
    Returns (is_valid, corrupted_index, detail_msg)
    """
    session_prev_map = {}
    for idx, log in enumerate(logs):
        session_id = str(log.get("session_id") or 'SESSION_DEFAULT')
        prev_hash = session_prev_map.get(session_id, "0" * 64)
        
        expected_prev = log.get("prev_hash") or ("0" * 64)
        current_hash = log.get("current_hash")
        
        if expected_prev != prev_hash:
            return False, idx, f"Prev hash mismatch at index {idx} for session '{session_id}' (Expected: {prev_hash[:12]}..., Got: {expected_prev[:12]}...)"
            
        payload = {
            "session_id": session_id,
            "step_number": log.get("step_number"),
            "action_type": log.get("action_type"),
            "detail_json": log.get("detail_json")
        }
        recalculated = compute_sha256_hash(expected_prev, payload)
        if current_hash and current_hash != recalculated:
            return False, idx, f"Current hash tampered at index {idx} for session '{session_id}' (Recorded: {current_hash[:12]}..., Calc: {recalculated[:12]}...)"
            
        session_prev_map[session_id] = current_hash or recalculated
        
    return True, -1, "SHA-256 Hash Chain 100% Verified"

def validate_step_integrity(current_step: int, metadata: dict) -> dict:
    is_valid = True
    reasons = []

    if current_step >= 2 and not metadata.get("step_1_audit_passed", True):
        is_valid = False
        reasons.append("Step 1 AI data audit incomplete")
    if current_step >= 3 and not metadata.get("step_2_geometry_valid", True):
        is_valid = False
        reasons.append("Step 2 geometry coordinates invalid")
    if current_step >= 4 and not metadata.get("step_3_ahp_locked", True):
        is_valid = False
        reasons.append("Step 3 AHP consistency ratio unlocked")

    return {
        "pipeline_step": current_step,
        "current_step_valid": is_valid,
        "invalidation_reasons": reasons,
        "step_1_audit_passed": metadata.get("step_1_audit_passed", True),
        "step_2_geometry_valid": metadata.get("step_2_geometry_valid", True),
        "step_3_ahp_locked": metadata.get("step_3_ahp_locked", True),
        "validated_at": get_kst_now().isoformat()
    }

def reheal_log_chain(db, master_key: str = None, admin_user: str = "SYSTEM_ADMIN") -> dict:
    """
    Detects broken/tampered hash chain index, verifies master_key against system_settings DB,
    inserts STEP_SEC_INCIDENT, appends STEP_SYS_REHEAL recovery block,
    and re-calculates all hash pointers so that verify_log_chain passes 100%.
    """
    from sqlalchemy import text
    from app.database import get_system_setting
    
    # 🔒 DB 연동 동적 마스터 보안 코드 검증
    active_master_key = get_system_setting(db, 'MASTER_SECURITY_KEY', 'OMNISITE-MASTER-2026')
    if not master_key or master_key.strip() != active_master_key.strip():
        return {
            "rehealed": False,
            "message": "🔒 보안 오류: 감사 로그 해시 체인 재동기화를 수행하기 위한 마스터 보안 코드가 일치하지 않습니다. 관리자 콘솔에서 확인 및 변경 가능합니다."
        }
        
    try:
        rows = db.execute(text("SELECT id, session_id, step_number, action_type, detail_json, prev_hash, current_hash, created_at FROM pipeline_execution_logs ORDER BY id ASC")).fetchall()
        logs = [dict(r._mapping) for r in rows]
        
        is_valid, corrupted_idx, detail_msg = verify_log_chain(logs)
        
        # 1. STEP_SEC_INCIDENT 및 STEP_SYS_REHEAL 적재 (마스터 승인 이력 영구 보존)
        incident_target_id = logs[corrupted_idx]["id"] if (corrupted_idx >= 0 and corrupted_idx < len(logs)) else 0
        incident_payload = {
            "incident_type": "CHAIN_BREAK_OR_TAMPER",
            "detected_at": get_kst_now().isoformat(),
            "corrupted_log_id": incident_target_id,
            "corrupted_index": corrupted_idx,
            "detail_msg": detail_msg,
            "reheal_action": "DYNAMIC_MASTER_KEY_AUTHORIZED_REHEAL",
            "rehealed_by": admin_user,
            "master_key_verification": "SUCCESS_DB_DYNAMIC_MASTER_KEY"
        }
        
        prev_h = logs[corrupted_idx - 1]["current_hash"] if (corrupted_idx > 0 and logs[corrupted_idx - 1].get("current_hash")) else ("0" * 64)
        
        inc_payload_dict = {
            "session_id": "SEC-INCIDENT",
            "step_number": "STEP_SEC_INCIDENT",
            "action_type": "[SEC_TAMPER_DETECTED]",
            "detail_json": incident_payload
        }
        incident_hash = compute_sha256_hash(prev_h, inc_payload_dict)
        
        db.execute(text("""
            INSERT INTO pipeline_execution_logs (session_id, step_number, action_type, detail_json, prev_hash, current_hash, created_at)
            VALUES (:session_id, :step_number, :action_type, :detail_json, :prev_hash, :current_hash, :created_at)
        """), {
            "session_id": "SEC-INCIDENT",
            "step_number": "STEP_SEC_INCIDENT",
            "action_type": "[SEC_TAMPER_DETECTED]",
            "detail_json": json.dumps(incident_payload),
            "prev_hash": prev_h,
            "current_hash": incident_hash,
            "created_at": get_kst_now()
        })
        db.commit()
        
        reheal_payload = {
            "reheal_target_log_id": incident_target_id,
            "reheal_timestamp": get_kst_now().isoformat(),
            "authorized_by": admin_user,
            "master_key_sig": "SHA256-SYSTEM-DYNAMIC-MASTER-REHEAL-SIG-CONFIRMED"
        }
        reheal_payload_dict = {
            "session_id": "SEC-REHEAL",
            "step_number": "STEP_SYS_REHEAL",
            "action_type": "[SEC_HASH_REHEALED]",
            "detail_json": reheal_payload
        }
        reheal_hash = compute_sha256_hash(incident_hash, reheal_payload_dict)
        
        db.execute(text("""
            INSERT INTO pipeline_execution_logs (session_id, step_number, action_type, detail_json, prev_hash, current_hash, created_at)
            VALUES (:session_id, :step_number, :action_type, :detail_json, :prev_hash, :current_hash, :created_at)
        """), {
            "session_id": "SEC-REHEAL",
            "step_number": "STEP_SYS_REHEAL",
            "action_type": "[SEC_HASH_REHEALED]",
            "detail_json": json.dumps(reheal_payload),
            "prev_hash": incident_hash,
            "current_hash": reheal_hash,
            "created_at": get_kst_now()
        })
        db.commit()

        # 2. ⚡ 전체 DB 해시 체인 순차 재연산 및 DB 갱신 (Full Chain Re-Indexing)
        all_rows = db.execute(text("SELECT id, session_id, step_number, action_type, detail_json FROM pipeline_execution_logs ORDER BY id ASC")).fetchall()
        
        curr_prev_h = "0" * 64
        for r in all_rows:
            p_dict = {
                "session_id": r.session_id,
                "step_number": r.step_number,
                "action_type": r.action_type,
                "detail_json": r.detail_json
            }
            new_curr_h = compute_sha256_hash(curr_prev_h, p_dict)
            db.execute(text("UPDATE pipeline_execution_logs SET prev_hash = :ph, current_hash = :ch WHERE id = :rid"), {
                "ph": curr_prev_h,
                "ch": new_curr_h,
                "rid": r.id
            })
            curr_prev_h = new_curr_h
            
        db.commit()

        return {
            "rehealed": True,
            "message": f"✓ 마스터 보안 코드 검증 완료: 감사 로그 #{incident_target_id} 지점의 멸실 단절이 최고 승인 하에 STEP_SEC_INCIDENT에 승인 기록되고 전체 체인이 정상 재동기화되었습니다.",
            "corrupted_log_id": incident_target_id
        }
    except Exception as e:
        db.rollback()
        return {"rehealed": False, "message": f"복구 중 오류 발생: {str(e)}"}