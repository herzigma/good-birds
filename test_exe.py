import sys
import os
import subprocess

def main():
    print("Testing PyInstaller ExifTool execution")
    if hasattr(sys, '_MEIPASS'):
        files_dir = os.path.join(sys._MEIPASS, 'exiftool_files')
        perl_exe = os.path.join(files_dir, 'perl.exe')
        exiftool_pl = os.path.join(files_dir, 'exiftool.pl')
        
        cmd = [perl_exe, exiftool_pl, "-ver"]
        print(f"Running command: {cmd}")
        
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            print("STDOUT:", res.stdout)
            print("STDERR:", res.stderr)
            print("Return Code:", res.returncode)
        except subprocess.TimeoutExpired:
            print("TIMEOUT EXPIRED!")
        except Exception as e:
            print(f"ERROR: {e}")
    else:
        print("Not bundled.")

if __name__ == '__main__':
    main()
