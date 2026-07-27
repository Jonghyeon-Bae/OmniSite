"""
OmniSite Shared Utilities and Helpers Module (v2.2.0-CodebaseRefactoring)
"""
from datetime import datetime, timezone, timedelta

def get_kst_now() -> datetime:
    """
    Returns current datetime in KST (Asia/Seoul: UTC+9).
    Guarantees strict KST timestamping across all OmniSite operations.
    """
    return datetime.now(timezone(timedelta(hours=9)))

def get_kst_now_str() -> str:
    """
    Returns formatted KST timestamp string: YYYY-MM-DD HH:MM:SS KST
    """
    return get_kst_now().strftime("%Y-%m-%d %H:%M:%S KST")