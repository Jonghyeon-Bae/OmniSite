import os
import sys
import shutil

sys.stdout.reconfigure(encoding='utf-8')

project_root = r"c:\Users\Admin\Desktop\빅프로젝트 관련자료\최종1차\1.0-prototype"
datasets_root = os.path.join(project_root, "Datasets")
lowercase_dataset_dir = os.path.join(project_root, "dataset")

print("========================================================")
print(" [Datasets Directory Unification Engine]")
print("========================================================")

# 1. Remove temporary lowercase 'dataset/' directory if exists
if os.path.exists(lowercase_dataset_dir):
    shutil.rmtree(lowercase_dataset_dir)
    print("  ✅ Removed temporary duplicate directory 'dataset/'")

# 2. Ensure standard 4-Step Coldstart 'Datasets/' subdirectories
dir_step1 = os.path.join(datasets_root, "1_boundaries")
dir_step2 = os.path.join(datasets_root, "2_cadastral")
dir_step3 = os.path.join(datasets_root, "3_restrictions")
dir_step4 = os.path.join(datasets_root, "4_indicators")

for d in [dir_step1, dir_step2, dir_step3, dir_step4]:
    os.makedirs(d, exist_ok=True)

# Sources
essential_src_dir = r"C:\Users\Admin\Desktop\빅프로젝트 관련자료\최종1차\데이터\최초 ColdStart를 위한 데이터셋\필수데이터"
optimal_src_dir = r"C:\Users\Admin\Desktop\빅프로젝트 관련자료\최종1차\데이터\최초 ColdStart를 위한 데이터셋\04.최적데이터"
clean_src_dir = r"C:\Users\Admin\Desktop\빅프로젝트 관련자료\최종1차\데이터\0706 정제데이터\01.정제데이터"
mapping_src_dir = r"C:\Users\Admin\Desktop\빅프로젝트 관련자료\최종1차\데이터\정리데이터"

# Step Mapping
copy_map = {
    # Step 1: Boundaries
    os.path.join(mapping_src_dir, "용산구_법정동_행정동_연계매핑.csv"): os.path.join(dir_step1, "용산구_법정동_행정동_연계매핑.csv"),
    
    # Step 2: Cadastral & National Property
    os.path.join(clean_src_dir, "05.용산구_부지면적_좌표(흡연부스 후보).csv"): os.path.join(dir_step2, "05.용산구_부지면적_좌표(흡연부스 후보).csv"),
    os.path.join(essential_src_dir, "cadastral_lands", "11. 국유부동산정보.csv"): os.path.join(dir_step2, "11. 국유부동산정보.csv"),
    
    # Step 3: Restrictions
    os.path.join(clean_src_dir, "06. 06-07 금연구역 통합본.csv"): os.path.join(dir_step3, "06. 06-07 금연구역 통합본.csv"),
    
    # Step 4: Indicators (Shops, Transit, Dumping, Population)
    os.path.join(optimal_src_dir, "10. 소상공인시장진흥공단_상가.csv"): os.path.join(dir_step4, "10. 소상공인시장진흥공단_상가.csv"),
    os.path.join(mapping_src_dir, "서울시 버스정류소 위치정보_YONGSAN.csv"): os.path.join(dir_step4, "서울시 버스정류소 위치정보_YONGSAN.csv"),
    os.path.join(clean_src_dir, "02. 지하철역 위치.csv"): os.path.join(dir_step4, "02. 지하철역 위치.csv"),
    os.path.join(mapping_src_dir, "BUS_STATION_BOARDING_MONTH_202605_YONGSAN.csv"): os.path.join(dir_step4, "BUS_STATION_BOARDING_MONTH_202605_YONGSAN.csv"),
    os.path.join(mapping_src_dir, "CARD_SUBWAY_MONTH_202605_YONGSAN.csv"): os.path.join(dir_step4, "CARD_SUBWAY_MONTH_202605_YONGSAN.csv"),
    os.path.join(clean_src_dir, "07. 담배꽁초_상습_무단투기.csv"): os.path.join(dir_step4, "07. 담배꽁초_상습_무단투기.csv"),
    os.path.join(mapping_src_dir, "LOCAL_PEOPLE_DONG_202605_YONGSAN_PEAK.csv"): os.path.join(dir_step4, "LOCAL_PEOPLE_DONG_202605_YONGSAN_PEAK.csv")
}

for src, dst in copy_map.items():
    if os.path.exists(src):
        shutil.copy2(src, dst)
        sz = os.path.getsize(dst)
        print(f"  ✅ [Unified Datasets] Copied to '{os.path.relpath(dst, datasets_root)}' ({sz:,} bytes)")
    else:
        print(f"  ❌ Source file missing: {src}")

print(f"\n[Unification Complete] Single 'Datasets/' 4-Step structure established successfully!")
