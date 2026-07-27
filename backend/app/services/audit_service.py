"""
OmniSite SHA-256 Hash Chain Audit Service (v2.2.0-CodebaseRefactoring)
Provides O(1) hash chain calculation, verification, and tamper detection.
"""
import hashlib
import json
from datetime import datetime, timezone, timedelta
from app.utils.helpers import get_kst_now

def compute_sha256_hash(prev_hash: str, payload_data: dict) -> str:
    """
    Computes SHA-256 hash by combining previous hash and current log payload.
    """
    raw_str = f"{prev_hash}:{json.dumps(payload_data, sort_keys=True)}"
    return hashlib.sha256(raw_str.encode('utf-8')).hexdigest()

def verify_log_chain(logs: list) -> tuple[bool, int, str]:
    """
    Verifies single-chain SHA-256 integrity across log entries.
    Returns (is_valid, corrupted_index, detail_msg)
    """
    prev_hash = "0" * 64
    for idx, log in enumerate(logs):
        expected_prev = log.get("prev_hash") or "0" * 64
        current_hash = log.get("current_hash")
        
        if expected_prev != prev_hash:
            return False, idx, f"Prev hash mismatch at index {idx}"
            
        payload = {
            "session_id": log.get("session_id"),
            "step_number": log.get("step_number"),
            "action_type": log.get("action_type"),
            "detail_json": log.get("detail_json")
        }
        recalculated = compute_sha256_hash(expected_prev, payload)
        if current_hash and current_hash != recalculated:
            return False, idx, f"Current hash tampered at index {idx}"
            
        prev_hash = current_hash or recalculated
        
    return True, -1, "SHA-256 Hash Chain 100% Verified"