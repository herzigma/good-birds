import os
import sys
import subprocess
import shutil
import textwrap
from pathlib import Path

# Windows Explorer uses a specific mapping between 1-5 stars and percent values.
# Both XMP:Rating and XMP:RatingPercent must be set for stars to show in
# Windows File Properties and DigiKam.
RATING_TO_PERCENT = {
    0: 0,
    1: 1,
    2: 25,
    3: 50,
    4: 75,
    5: 99,
}

def get_exiftool_cmd() -> list[str] | None:
    """
    Get the command array to run exiftool. 
    Checks the bundled PyInstaller _MEIPASS directory first, then the system PATH.
    """
    # Check if bundled in PyInstaller
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        files_dir = os.path.join(sys._MEIPASS, 'exiftool_files')
        perl_exe = os.path.join(files_dir, 'perl.exe')
        exiftool_pl = os.path.join(files_dir, 'exiftool.pl')
        
        # Bypass exiftool.exe wrapper to avoid environment/PATH bugs.
        if os.path.exists(perl_exe) and os.path.exists(exiftool_pl):
            return [perl_exe, exiftool_pl]
            
    # Check if running from source with a downloaded binary
    local_exiftool = Path(__file__).parent / "exiftool.exe"
    if local_exiftool.exists():
        return [str(local_exiftool)]
            
    # Fallback to system path
    exe_path = shutil.which("exiftool")
    if exe_path:
        return [exe_path]
    return None

def is_exiftool_installed() -> bool:
    """Check if exiftool is available on the system PATH or bundled."""
    return get_exiftool_cmd() is not None

def write_xmp_sidecar(file_path: Path, rating: int) -> bool:
    """
    Write a minimal XMP sidecar file alongside the image.
    
    Creates a file named <original_filename>.xmp (e.g. IMG_1234.CR2.xmp)
    containing a standards-compliant XMP packet with xmp:Rating.
    This is required for Darktable, RawTherapee, and RapidRaw to display
    star ratings, as they read from sidecar files rather than embedded metadata.
    
    Returns True if successful, False otherwise.
    """
    sidecar_path = file_path.parent / f"{file_path.name}.xmp"
    
    xmp_content = textwrap.dedent(f"""\
        <?xpacket begin='\ufeff' id='W5M0MpCehiHzreSzNTczkc9d'?>
        <x:xmpmeta xmlns:x="adobe:ns:meta/">
         <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
          <rdf:Description rdf:about=""
           xmlns:xmp="http://ns.adobe.com/xap/1.0/"
           xmp:Rating="{rating}"/>
         </rdf:RDF>
        </x:xmpmeta>
        <?xpacket end='w'?>
    """)
    
    try:
        sidecar_path.write_text(xmp_content, encoding="utf-8")
        return True
    except Exception as e:
        print(f"Error writing sidecar for {file_path.name}: {e}")
        return False


def write_rating(file_path: Path, rating: int, dry_run: bool = False, sidecar: bool = True) -> bool:
    """
    Write star rating metadata to a file using exiftool and an XMP sidecar.
    
    Sets three embedded tags for maximum compatibility:
      - XMP:Rating        (standard, read by Lightroom/DigiKam/etc.)
      - XMP:RatingPercent (Microsoft-specific, needed for Windows Explorer stars)
      - Rating            (EXIF-level fallback)
    
    Optionally writes an XMP sidecar file (<filename>.xmp) for applications that
    read ratings from sidecar files (Darktable, RawTherapee, RapidRaw).
    Sidecar generation is controlled by the `sidecar` parameter (default: True).
    
    Returns True if successful, False otherwise.
    """
    if dry_run:
        print(f"[DRY RUN] Would write rating {rating} to {file_path.name}")
        return True
        
    exiftool_cmd = get_exiftool_cmd()
    if not exiftool_cmd:
        print("Error: exiftool is not installed, bundled, or not in PATH.")
        return False
    
    rating_percent = RATING_TO_PERCENT.get(rating, 0)
        
    try:
        # Construct exact command array.
        # -overwrite_original prevents creating a _original backup file
        # Three tags for full compatibility with Windows, DigiKam, Lightroom, etc.
        cmd = exiftool_cmd + [
            "-overwrite_original", 
            f"-XMP:Rating={rating}",
            f"-XMP:RatingPercent={rating_percent}",
            f"-Rating={rating}",
            str(file_path)
        ]
        
        # Run silently unless there's an error
        result = subprocess.run(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        
        # Also write an XMP sidecar for Darktable/RawTherapee/RapidRaw
        if sidecar:
            write_xmp_sidecar(file_path, rating)
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"Error writing to {file_path.name}: {e.stderr}")
        return False
    except Exception as e:
        print(f"Unexpected error writing to {file_path.name}: {e}")
        return False
