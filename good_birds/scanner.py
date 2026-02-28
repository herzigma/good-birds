import datetime
import logging
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

import rawpy
from PIL import Image, ExifTags

try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass

from .models import PhotoInfo
from .rating import get_exiftool_cmd

logger = logging.getLogger(__name__)

# Standard RAW formats we support
RAW_EXTENSIONS = ('.cr2', '.cr3', '.nef', '.arw', '.raw')
# Standard non-RAW image formats we support mapping metadata for natively
NON_RAW_EXTENSIONS = ('.jpg', '.jpeg', '.heif', '.heic', '.webp')

def get_exif_data(image: Image.Image) -> dict:
    """Extract EXIF data into a more readable dictionary."""
    exif_data = {}
    exif = image.getexif()
    if exif is None:
        return exif_data
        
    for tag_id, value in exif.items():
        tag = ExifTags.TAGS.get(tag_id, tag_id)
        exif_data[tag] = value
        
    # Also get IFD data (where the valuable stuff often hides in JPEGs)
    ifd = exif.get_ifd(ExifTags.IFD.Exif)
    for tag_id, value in ifd.items():
        tag = ExifTags.TAGS.get(tag_id, tag_id)
        exif_data[tag] = value
        
    return exif_data

def scan_file(file_path: Path) -> Optional[PhotoInfo]:
    """
    Scan a single RAW file to extract metadata without fully decoding the RAW image data.
    """
    try:
        with rawpy.imread(str(file_path)) as raw:
            try:
                # Try to get the embedded preview (much faster than decoding RAW)
                # For CR2, rawpy can usually extract the JPEG preview
                thumb = raw.extract_thumb()
                if thumb.format == rawpy.ThumbFormat.JPEG:
                    # Load from bytes
                    import io
                    preview_img = Image.open(io.BytesIO(thumb.data))
                    
                    # Extract EXIF from this embedded preview
                    exif = get_exif_data(preview_img)
                    
                    # Parse interesting fields
                    dt_orig_str = exif.get("DateTimeOriginal")
                    sub_sec_str = exif.get("SubsecTimeOriginal", "00")
                    
                    if not dt_orig_str:
                        # Fallback to file modified time if EXIF is missing
                        mtime = file_path.stat().st_mtime
                        dt_orig = datetime.datetime.fromtimestamp(mtime)
                    else:
                        # EXIF format is usually "YYYY:MM:DD HH:MM:SS"
                        try:
                            dt_orig = datetime.datetime.strptime(dt_orig_str, "%Y:%m:%d %H:%M:%S")
                        except ValueError:
                            mtime = file_path.stat().st_mtime
                            dt_orig = datetime.datetime.fromtimestamp(mtime)
                            
                    iso = exif.get("ISOSpeedRatings")
                    
                    # Shutter speed is often stored as ExposureTime (a ratio)
                    exposure_time = exif.get("ExposureTime")
                    shutter_str = None
                    if exposure_time:
                        if isinstance(exposure_time, float):
                            if exposure_time < 1:
                                shutter_str = f"1/{int(1/exposure_time)}"
                            else:
                                shutter_str = f"{exposure_time}s"
                        else:
                            # It might be a tuple representing a fraction
                            pass
                            
                    aperture = exif.get("FNumber")
                    if isinstance(aperture, tuple) and len(aperture) == 2:
                        try:
                            aperture = float(aperture[0]) / float(aperture[1])
                        except ZeroDivisionError:
                            aperture = None
                    
                    return PhotoInfo(
                        path=file_path,
                        timestamp=dt_orig,
                        sub_sec=str(sub_sec_str),
                        iso=iso,
                        shutter_speed=shutter_str,
                        aperture=aperture
                    )
            except rawpy.LibRawNoThumbnailError:
                pass
                
    except Exception as e:
        # We might fail on non-raw files or corrupted files
        pass
        
    return None

def scan_standard_file(file_path: Path) -> Optional[PhotoInfo]:
    """
    Fallback scanner for non-RAW files using PIL directly.
    """
    try:
        with Image.open(file_path) as img:
            exif = get_exif_data(img)
            
            dt_orig_str = exif.get("DateTimeOriginal")
            sub_sec_str = exif.get("SubsecTimeOriginal", "00")
            
            if not dt_orig_str:
                mtime = file_path.stat().st_mtime
                dt_orig = datetime.datetime.fromtimestamp(mtime)
            else:
                try:
                    dt_orig = datetime.datetime.strptime(dt_orig_str, "%Y:%m:%d %H:%M:%S")
                except ValueError:
                    mtime = file_path.stat().st_mtime
                    dt_orig = datetime.datetime.fromtimestamp(mtime)
                    
            iso = exif.get("ISOSpeedRatings")
            
            exposure_time = exif.get("ExposureTime")
            shutter_str = None
            if exposure_time:
                if isinstance(exposure_time, float):
                    if exposure_time < 1:
                        shutter_str = f"1/{int(1/exposure_time)}"
                    else:
                        shutter_str = f"{exposure_time}s"
                        
            aperture = exif.get("FNumber")
            if isinstance(aperture, tuple) and len(aperture) == 2:
                try:
                    aperture = float(aperture[0]) / float(aperture[1])
                except ZeroDivisionError:
                    aperture = None
            
            return PhotoInfo(
                path=file_path,
                timestamp=dt_orig,
                sub_sec=str(sub_sec_str),
                iso=iso,
                shutter_speed=shutter_str,
                aperture=aperture
            )
    except Exception as e:
        logger.debug(f"Failed to scan standard file {file_path.name}: {e}")
        pass
        
    return None

def scan_directory(
    directory: Path, 
    extensions: Tuple[str, ...] = RAW_EXTENSIONS,
    exclude_non_raw: bool = False
) -> List[PhotoInfo]:
    """Scan a directory for supported raw files using exiftool (if available) for batch extraction."""
    
    # Determine the full suite of extensions we are looking for
    target_extensions = list(extensions)
    if not exclude_non_raw:
        target_extensions.extend(NON_RAW_EXTENSIONS)
    
    logger.info(f"Scanning directory {directory} for extensions {target_extensions}")
    photos = []
    
    cmd = get_exiftool_cmd()
    exif_data_by_file = {}
    
    if cmd:
        logger.info("Exiftool found. Running batch EXIF extraction...")
        # Build ext arguments
        ext_args = []
        for ext in target_extensions:
            ext_args.extend(["-ext", ext.lstrip('.')])
            
        exif_cmd = cmd + [
            "-T", 
            "-filename", 
            "-datetimeoriginal", 
            "-subsectimeoriginal", 
            "-iso", 
            "-exposuretime", 
            "-fnumber",
            *ext_args,
            str(directory)
        ]
        
        try:
            result = subprocess.run(exif_cmd, capture_output=True, text=True, check=True)
            for line in result.stdout.splitlines():
                parts = line.split('\t')
                if len(parts) >= 6:
                    filename, dt, subsec, iso, exp, fnum = parts[:6]
                    exif_data_by_file[filename] = {
                        "datetime": dt,
                        "subsec": subsec,
                        "iso": iso,
                        "exposure": exp,
                        "fnumber": fnum
                    }
            logger.info(f"Batch extracted EXIF for {len(exif_data_by_file)} files via exiftool.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Exiftool batch extraction failed: {e.stderr[:200]}")
            logger.info("Falling back to rawpy extraction for all files.")
        except Exception as e:
            logger.error(f"Unexpected error running exiftool: {str(e)}")
    else:
        logger.warning("Exiftool not found, falling back to rawpy preview EXIF extraction.")

    # 1. First pass: look at all files to build a set of RAW files
    # This prevents us from scoring IMG_1234.JPG if IMG_1234.CR2 exists.
    raw_stems = set()
    all_files = list(directory.iterdir())
    
    for file_path in all_files:
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() in extensions:
            raw_stems.add(file_path.stem)

    # Iterate directory and build PhotoInfo objects
    for file_path in all_files:
        if not file_path.is_file():
            continue
            
        ext = file_path.suffix.lower()
        if ext in target_extensions:
            # Skip if it is a NON-RAW but we have the RAW
            if ext in NON_RAW_EXTENSIONS and file_path.stem in raw_stems:
                logger.debug(f"Skipping {file_path.name} because matching RAW was found.")
                continue
            info = None
            filename = file_path.name
            
            if filename in exif_data_by_file:
                # Parse from exiftool output
                data = exif_data_by_file[filename]
                dt_str = data["datetime"]
                
                if dt_str and dt_str != "-":
                    try:
                        timestamp = datetime.datetime.strptime(dt_str, "%Y:%m:%d %H:%M:%S")
                    except ValueError:
                        timestamp = datetime.datetime.fromtimestamp(file_path.stat().st_mtime)
                else:
                    timestamp = datetime.datetime.fromtimestamp(file_path.stat().st_mtime)
                    logger.warning(f"No DateTimeOriginal for {filename}, using fallback mtime.")
                    
                subsec_str = data["subsec"] if data["subsec"] != "-" else "00"
                iso_val = int(data["iso"]) if data["iso"] != "-" and data["iso"].isdigit() else None
                
                exp_str = data["exposure"] if data["exposure"] != "-" else None
                
                fnum_val = None
                if data["fnumber"] != "-":
                    try:
                        fnum_val = float(data["fnumber"])
                    except ValueError:
                        pass
                
                info = PhotoInfo(
                    path=file_path,
                    timestamp=timestamp,
                    sub_sec=subsec_str,
                    iso=iso_val,
                    shutter_speed=exp_str,
                    aperture=fnum_val
                )
            else:
                # Use fallback
                logger.debug(f"Exiftool data not found for {filename}, falling back to manual scan.")
                if ext in extensions:
                    info = scan_file(file_path)
                else:
                    info = scan_standard_file(file_path)
                
            if info:
                photos.append(info)
                
    logger.info(f"Successfully scanned {len(photos)} supported files.")
    
    # Sort them chronologically
    photos.sort(key=lambda p: p.full_timestamp_sort_key)
    return photos
