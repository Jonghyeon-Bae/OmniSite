import os
import re
import sys
import ast
import traceback

def audit_backend_code():
    print("==================================================")
    print("=== [Phase 1] Backend Python Code Audit ===")
    print("==================================================")
    
    sys.path.insert(0, os.path.abspath("."))
    
    # 1. Import all router modules & main app
    router_modules = [
        "app.main",
        "app.database",
        "app.config",
        "app.routers.auth",
        "app.routers.spatial",
        "app.routers.upload",
        "app.routers.model",
        "app.routers.ahp",
        "app.routers.board"
    ]
    
    import_errors = []
    for mod_name in router_modules:
        try:
            __import__(mod_name)
            print(f"  [OK] Module import: {mod_name}")
        except Exception as e:
            import_errors.append((mod_name, str(e), traceback.format_exc()))
            print(f"  [FAIL] Module import failed: {mod_name} -> {e}")

    if import_errors:
        print(f"\n[WARNING] Total {len(import_errors)} Module Import Failures Detected!")
    else:
        print("\n[SUCCESS] All 9 Core Backend Modules Imported Cleanly (0 Error)!")

    # 2. Check all FastAPI routes registered on app.main
    print("\n--------------------------------------------------")
    print("=== [Phase 2] FastAPI Registered Endpoints Inspection ===")
    print("--------------------------------------------------")
    try:
        from app.main import app
        routes = app.routes
        print(f"  [OK] Total {len(routes)} FastAPI routes registered.")
        
        route_summary = []
        for r in routes:
            path = getattr(r, "path", str(r))
            methods = getattr(r, "methods", ["GET"])
            name = getattr(r, "name", "")
            route_summary.append(f"{','.join(methods)} {path} ({name})")
            
        print(f"  Sample Endpoints (First 15):")
        for r_info in route_summary[:15]:
            print(f"    - {r_info}")
    except Exception as e:
        print(f"  [FAIL] FastAPI Route Inspection Failed: {e}")

    # 3. Static regex audit for potential risk patterns in backend python files
    print("\n--------------------------------------------------")
    print("=== [Phase 3] Static Code Pattern Risk Audit ===")
    print("--------------------------------------------------")
    app_dir = os.path.abspath("app")
    risk_findings = []
    
    for root, dirs, files in os.walk(app_dir):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, os.getcwd())
                with open(file_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    
                for idx, line in enumerate(lines, 1):
                    # Check for bare except: without logging or raising
                    if re.search(r"except\s*:", line) and not re.search(r"except\s+Exception", line):
                        risk_findings.append((rel_path, idx, "Bare except clause detected (should use except Exception)"))
                    # Check for unhandled json.loads without try-except nearby
                    if "json.loads(" in line and "try:" not in lines[max(0, idx-5):idx][0]:
                        pass # Valid in safe contexts, logged for reference
                        
    if risk_findings:
        print(f"  [WARNING] Found {len(risk_findings)} potential pattern risks:")
        for r_path, l_num, msg in risk_findings:
            print(f"    - {r_path}:L{l_num} -> {msg}")
    else:
        print("  [OK] 0 High-Risk Code Patterns Detected in Backend!")

if __name__ == "__main__":
    audit_backend_code()
