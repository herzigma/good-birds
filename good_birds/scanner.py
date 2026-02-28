import datetime
from pathlib import Path
from typing import List, Optional, Tuple

import rawpy
from PIL import Image, ExifTags

from .models import PhotoInfo

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

def scan_directory(directory: Path, extensions: Tuple[str, ...] = ('.cr2', '.cr3', '.NEF', '.ARW', '.raw')) -> List[PhotoInfo]:
    """Scan a directory for supported raw files."""
    photos = []
    
    # We only scan the top-level directory for now
    for file_path in directory.iterdir():
        if not file_path.is_file():
            continue
            
        if file_path.suffix.lower() in extensions:
            info = scan_file(file_path)
            if info:
                photos.append(info)
                
    # Sort them chronically
    photos.sort(key=lambda p: p.full_timestamp_sort_key)
    return photos
