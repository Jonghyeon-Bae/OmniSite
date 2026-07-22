import os
import zipfile

zip_path = r'c:\Users\Admin\Desktop\빅프로젝트 관련자료\최종1차\1.0-prototype\Datasets\1_boundaries\읍면동.zip'
extract_dir = r'c:\Users\Admin\Desktop\빅프로젝트 관련자료\최종1차\1.0-prototype\Datasets\1_boundaries\extracted'

os.makedirs(extract_dir, exist_ok=True)
with zipfile.ZipFile(zip_path, 'r') as zip_ref:
    zip_ref.extractall(extract_dir)

print(f"Extracted files to {extract_dir}: {os.listdir(extract_dir)}")
