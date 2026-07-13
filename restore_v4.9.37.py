import os
import shutil

src_dir = os.path.dirname(os.path.abspath(__file__))
backup_dir = os.path.join(src_dir, 'backups_v4.9.37')

files_to_restore = [
    ('spatial.py', 'backend/app/routers/spatial.py'),
    ('upload.py', 'backend/app/routers/upload.py'),
    ('page.js', 'frontend/src/app/page.js'),
    ('SidebarControl.jsx', 'frontend/src/components/SidebarControl.jsx'),
    ('OptimalResultPanel.jsx', 'frontend/src/components/OptimalResultPanel.jsx')
]

print("=== v4.9.37 안전 복구(Rollback) 파이프라인 시작 ===")
if not os.path.exists(backup_dir):
    print("⚠️ 오류: 백업 폴더 backups_v4.9.37 이 존재하지 않습니다.")
    exit(1)

for backup_name, target_rel_path in files_to_restore:
    backup_path = os.path.join(backup_dir, backup_name)
    target_path = os.path.join(src_dir, target_rel_path)
    
    if os.path.exists(backup_path):
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        shutil.copy2(backup_path, target_path)
        print(f"✅ 복구 완료: {backup_name} ➔ {target_rel_path}")
    else:
        print(f"⚠️ 경고: 백업본 {backup_name} 이 누락되었습니다.")

print("=== 복구 이행 완료: 프로젝트가 v4.9.37 상태로 안전 롤백되었습니다. ===")
