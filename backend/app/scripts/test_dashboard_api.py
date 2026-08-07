import sys
import os
import asyncio
sys.path.insert(0, os.path.abspath("."))
from app.database import SessionLocal
from app.routers.spatial import get_decision_history, get_verified_precedents

async def test_dashboard_endpoints():
    db = SessionLocal()
    try:
        print("Testing get_decision_history (GET /spatial/history)...")
        hist = await get_decision_history(db)
        print(f"-> History Count: {len(hist)}")

        print("\nTesting get_verified_precedents (GET /spatial/precedents)...")
        prec = await get_verified_precedents(db)
        print(f"-> Precedents Count: {len(prec)}")

        print("\nALL DASHBOARD ENDPOINTS OK!")
    except Exception as e:
        print(f"\nCRASH EXCEPTION DETECTED: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_dashboard_endpoints())
