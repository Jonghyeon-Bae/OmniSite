# -*- coding: utf-8 -*-
import os
import shutil
import glob

print("=== [DATASET MANAGER: STARTING FILE AGGREGATION] ===")

src_dir_1 = "c:/Users/Admin/Desktop/빅프로젝트 관련자료/최종1차/데이터/최종"
src_dir_2 = "c:/Users/Admin/Desktop/빅프로젝트 관련자료/최종1차/데이터/Dont_Touch"
dest_dir = "c:/Users/Admin/Desktop/빅프로젝트 관련자료/최종1차/1.0-prototype/Datasets"

if not os.path.exists(dest_dir):
    os.makedirs(dest_dir)
    print(f"Created Datasets folder at: {dest_dir}")

# List of files we want to copy defensively
copy_patterns = [
    "*emd.*",
    "*sig.*",
    "*LOCAL_PEOPLE_DONG*",
    "*BUS_STATION_BOARDING*",
    "*CARD_SUBWAY_MONTH*",
    "*LSMD_CONT_LDREG*",
    "*소상공인*",
    "*어린이집*",
    "*학교*",
    "*민원*",
    "*국유부동산*",
    "*정제데이터*"
]

copied_count = 0

def copy_matching_files(src_folder):
    global copied_count
    if not os.path.exists(src_folder):
        print(f"Source folder not exists: {src_folder}")
        return
        
    for pattern in copy_patterns:
        matched = glob.glob(os.path.join(src_folder, pattern))
        for filepath in matched:
            filename = os.path.basename(filepath)
            dest_path = os.path.join(dest_dir, filename)
            try:
                # Copy file
                shutil.copy2(filepath, dest_path)
                print(f"Copied: {filename} to Datasets")
                copied_count += 1
            except Exception as e:
                print(f"Failed to copy {filename}: {e}")

# Run copy from both folders
copy_matching_files(src_dir_1)
copy_matching_files(src_dir_2)

print(f"=== File Aggregation Complete. Total files copied: {copied_count} ===")
