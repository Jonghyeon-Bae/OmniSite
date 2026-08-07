import sys
import os
sys.path.insert(0, os.path.abspath("."))
from sqlalchemy import text
from app.database import engine

with engine.connect() as conn:
    cols = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'verified_precedents'")).fetchall()
    print("verified_precedents columns:", [c[0] for c in cols])
