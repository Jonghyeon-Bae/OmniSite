# -*- coding: utf-8 -*-
import os
import shutil
import glob

print("=== [COLOSTART DATASET ORGANIZER & CLEANER: START] ===")

src_root = r"C:\Users\Admin\Desktop\빅프로젝트 관련자료\최종1차\데이터\최초 ColdStart를 위한 데이터셋"
dest_root = r"C:\Users\Admin\Desktop\빅프로젝트 관련자료\최종1차\1.0-prototype\Datasets"

# 1. 대상 디렉터리 구조 자동 설계
dirs = {
    "1_boundaries": os.path.join(dest_root, "1_boundaries"),
    "2_cadastral": os.path.join(dest_root, "2_cadastral"),
    "3_restrictions": os.path.join(dest_root, "3_restrictions"),
    "4_indicators": os.path.join(dest_root, "4_indicators"),
    "5_duplicates": os.path.join(dest_root, "5_duplicates")
}

for d_name, d_path in dirs.items():
    os.makedirs(d_path, exist_ok=True)
    print(f"[Dir Created] {d_name} -> {d_path}")

# --- STEP 1. 경계 데이터셋 이관 (1_boundaries) ---
boundary_patterns = ["시군구.zip", "읍면동.zip"]
for pattern in boundary_patterns:
    src_file = os.path.join(src_root, pattern)
    if os.path.exists(src_file):
        shutil.copy2(src_file, os.path.join(dirs["1_boundaries"], pattern))
        print(f"[Seeded Boundary] {pattern} -> 1_boundaries")

# --- STEP 2. 지적도 및 국유부동산 정보 이관 (2_cadastral) ---
cadastral_files = ["LSMD_CONT_LDREG_서울_용산구.zip", "11. 국유부동산정보.csv"]
for f in cadastral_files:
    src_file = os.path.join(src_root, f)
    if os.path.exists(src_file):
        shutil.copy2(src_file, os.path.join(dirs["2_cadastral"], f))
        print(f"[Seeded Cadastral] {f} -> 2_cadastral")

# --- STEP 3. AHP 지표 데이터셋 이관 (4_indicators) ---
# 04.최적데이터 하위 파일들을 분류
opt_data_path = os.path.join(src_root, "04.최적데이터")
if os.path.exists(opt_data_path):
    indicator_files = [
        "01.버스정류소_유동인구.csv",
        "02. 용산구_가로휴지통.csv",
        "03. 지하철역_유동인구.csv",
        "04. 생활인구.csv",
        "05.용산구_부지면적_좌표(흡연부스 후보).csv",
        "06. 용산구_공원데이터.xlsx",
        "07. 담배꽁초_상습_무단투기.csv",
        "10. 소상공인시장진흥공단_상가.csv",
        "11. 용산구_유흥시설_통합_인허가정보.csv"
    ]
    for f in indicator_files:
        src_file = os.path.join(opt_data_path, f)
        if os.path.exists(src_file):
            shutil.copy2(src_file, os.path.join(dirs["4_indicators"], f))
            print(f"[Seeded Indicator] {f} -> 4_indicators")

# --- STEP 4. 규제 시설 이관 및 중복 데이터 격리 (3_restrictions & 5_duplicates) ---
# 1) 어린이집/유치원 통합 인허가 정보 채택 (더 많은 정보를 수록)
nursery_best = os.path.join(opt_data_path, "12. 용산구_어린이집_유치원_통합_인허가정보.csv")
if os.path.exists(nursery_best):
    shutil.copy2(nursery_best, os.path.join(dirs["3_restrictions"], "용산구_어린이집_유치원_통합_인허가정보.csv"))
    print("[Seeded Restriction] 12. 어린이집_유치원_통합 -> 3_restrictions")

# 구버전 유치원/어린이집 축약 목록은 중복으로 격리
nursery_duplicate = os.path.join(src_root, "필수데이터", "restricted_zones", "용산구_유치원_어린이집포맷_인허가정보.csv")
if os.path.exists(nursery_duplicate):
    shutil.copy2(nursery_duplicate, os.path.join(dirs["5_duplicates"], "용산구_유치원_어린이집포맷_인허가정보.csv"))
    print("[Deduplicated] 용산구_유치원_어린이집포맷 -> 5_duplicates")

# 2) 흡연구역 데이터 정제 및 격리
# 08.용산구_전체_흡연구역_폴리곤.csv 와 09. 서울특별시_용산구_흡연구역.csv
smoking_best = os.path.join(opt_data_path, "08.용산구_전체_흡연구역_폴리곤.csv")
if os.path.exists(smoking_best):
    shutil.copy2(smoking_best, os.path.join(dirs["3_restrictions"], "용산구_전체_흡연구역_폴리곤.csv"))
    print("[Seeded Restriction] 08.용산구_전체_흡연구역_폴리곤 -> 3_restrictions")

smoking_best_2 = os.path.join(opt_data_path, "09. 서울특별시_용산구_흡연구역.csv")
if os.path.exists(smoking_best_2):
    shutil.copy2(smoking_best_2, os.path.join(dirs["3_restrictions"], "서울특별시_용산구_흡연구역.csv"))
    print("[Seeded Restriction] 09. 서울특별시_용산구_흡연구역 -> 3_restrictions")

# 구버전 중복 흡연구역 및 게시판 목록은 5_duplicates 로 격리
dup_smoking_files = [
    ("필수데이터/restricted_zones/서울특별시 용산구_흡연구역_20240719.csv", "서울특별시_용산구_흡연구역_20240719_dup.csv"),
    ("필수데이터/restricted_zones/용산구청_금연구역_검색게시판_목록.csv", "용산구청_금연구역_검색게시판_목록_dup.csv"),
    ("필수데이터/restricted_zones/서울시 금연구역  정보(표준 데이터).csv", "서울시_금연구역_정보_표준데이터_dup.csv")
]

for relative_p, rename_n in dup_smoking_files:
    full_path = os.path.join(src_root, relative_p.replace("/", os.sep))
    if os.path.exists(full_path):
        shutil.copy2(full_path, os.path.join(dirs["5_duplicates"], rename_n))
        print(f"[Deduplicated] {relative_p} -> 5_duplicates")

print("=== [COLOSTART DATASET ORGANIZER & CLEANER: COMPLETE] ===")
