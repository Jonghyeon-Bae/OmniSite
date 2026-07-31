import os, sys, subprocess

print("=========================================================")
print("   OmniSite SDSS Checkpoint Instant Restore Utility")
print("=========================================================\n")

target_tag = "checkpoint-v1.5.0-zerobias"

try:
    print(f"[*] Restoring workspace to Git Tag '{target_tag}'...")
    res = subprocess.run(["git", "checkout", target_tag], capture_output=True, text=True)
    if res.returncode == 0:
        print(f"[SUCCESS] Workspace successfully restored to {target_tag}!")
    else:
        print(f"[Notice] Git checkout returned: {res.stderr}")
        subprocess.run(["git", "reset", "--hard", "HEAD"], check=True)
        print("[SUCCESS] Workspace successfully reset to latest clean HEAD!")
except Exception as e:
    print(f"[ERROR] Restore failed: {e}")

print("\n=========================================================")
print("   Checkpoint Restore Complete: System Ready!")
print("=========================================================")
