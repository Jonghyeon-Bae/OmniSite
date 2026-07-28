
from app.db.session import SessionLocal
from app.services.audit_service import reheal_log_chain, verify_log_chain
from sqlalchemy import text

db = SessionLocal()
rows = db.execute(text("SELECT id, session_id, step_number, action_type, detail_json, prev_hash, current_hash, created_at FROM pipeline_execution_logs ORDER BY id ASC")).fetchall()
logs = [dict(r._mapping) for r in rows]

is_v, c_idx, msg = verify_log_chain(logs)
print(f"[BEFORE REHEAL VERIFY] valid={is_v}, idx={c_idx}, msg={msg}")

res = reheal_log_chain(db)
print(f"[REHEAL RESULT] {res}")

rows2 = db.execute(text("SELECT id, session_id, step_number, action_type, detail_json, prev_hash, current_hash, created_at FROM pipeline_execution_logs ORDER BY id ASC")).fetchall()
logs2 = [dict(r._mapping) for r in rows2]
is_v2, c_idx2, msg2 = verify_log_chain(logs2)
print(f"[AFTER REHEAL VERIFY] valid={is_v2}, idx={c_idx2}, msg={msg2}")

db.close()
