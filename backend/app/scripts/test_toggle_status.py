import sys
import os
import json

sys.path.insert(0, os.path.abspath("."))
from sqlalchemy import text
from app.database import engine, SessionLocal
from app.routers.spatial import HistoryStatusUpdateRequest, update_decision_history_status

def test_status_update():
    db = SessionLocal()
    try:
        # DB에서 실제 존재하는 history_id 인출
        last_hist = db.execute(text("SELECT id, status FROM decision_histories ORDER BY id DESC LIMIT 1")).fetchone()
        if not last_hist:
            print("No decision history found in DB!")
            return
        
        hid = last_hist[0]
        curr_status = last_hist[1]
        print(f"Testing status update for history_id #{hid} (Current Status: {curr_status})...")
        
        target_status = "토론 완료" if curr_status != "토론 완료" else "실증 실패"
        req = HistoryStatusUpdateRequest(status=target_status)
        
        import asyncio
        res = asyncio.run(update_decision_history_status(hid, req, db))
        print("RESULT SUCCESS:", res)

        # 다시 롤백 원상 복구
        req_orig = HistoryStatusUpdateRequest(status=curr_status)
        asyncio.run(update_decision_history_status(hid, req_orig, db))
        print("REVERTED TO ORIG STATUS:", curr_status)

    except Exception as e:
        print("EXCEPTIONAL CRASH:", e)
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_status_update()
