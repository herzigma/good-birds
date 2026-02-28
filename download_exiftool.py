import urllib.request
import zipfile
import shutil
import os
from pathlib import Path

url = "https://master.dl.sourceforge.net/project/exiftool/exiftool-13.52_64.zip?viasf=1"
zip_path = "exiftool.zip"
extract_dir = "exiftool_extracted"
target_dir = Path("good_birds")

print(f"Downloading {url}...")
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
with urllib.request.urlopen(req) as response, open(zip_path, 'wb') as out_file:
    shutil.copyfileobj(response, out_file)

print("Extracting...")
with zipfile.ZipFile(zip_path, 'r') as zip_ref:
    zip_ref.extractall(extract_dir)

# Find the executable and the files directory
exe_path = None
files_dir = None
for root, dirs, files in os.walk(extract_dir):
    for f in files:
        if "exiftool(-k).exe" in f or "exiftool.exe" in f:
            exe_path = os.path.join(root, f)
            possible_files_dir = os.path.join(root, "exiftool_files")
            if os.path.exists(possible_files_dir):
                files_dir = possible_files_dir
            break
    if exe_path:
        break
            
if exe_path:
    print(f"Found executable at: {exe_path}")
    target_exe = target_dir / "exiftool.exe"
    
    # Remove existing files if present
    if target_exe.exists(): target_exe.unlink()
    shutil.copy2(exe_path, target_exe)
    
    if files_dir:
        print(f"Found files dir at: {files_dir}")
        target_files = target_dir / "exiftool_files"
        if target_files.exists(): shutil.rmtree(target_files)
        shutil.copytree(files_dir, target_files)
        
    print(f"Successfully copied to: {target_dir}")
else:
    print("Could not find exiftool binary in zip!")

# Cleanup
try:
    os.remove(zip_path)
    shutil.rmtree(extract_dir)
except:
    pass
