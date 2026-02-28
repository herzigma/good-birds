import datetime
import logging
from typing import List

from .models import PhotoInfo, Burst, ScoredPhoto

logger = logging.getLogger(__name__)

def group_into_bursts(photos: List[PhotoInfo], threshold_seconds: float = 1.0) -> List[Burst]:
    """
    Group a chronologically sorted list of photos into bursts.
    A new burst starts when the time difference between consecutive photos 
    exceeds the threshold.
    """
    if not photos:
        logger.warning("No photos provided to group_into_bursts.")
        return []

    logger.info(f"Grouping {len(photos)} photos with threshold {threshold_seconds}s")
    # Ensure the list is sorted just in case
    sorted_photos = sorted(photos, key=lambda p: p.full_timestamp_sort_key)
    
    bursts = []
    current_burst_photos = [ScoredPhoto(info=sorted_photos[0])]
    
    for i in range(1, len(sorted_photos)):
        current_photo = sorted_photos[i]
        prev_photo = sorted_photos[i-1]
        
        # Calculate time diff
        time_diff = current_photo.timestamp - prev_photo.timestamp
        diff_seconds = time_diff.total_seconds()
        
        # Consider sub-seconds if timestamps are exactly the same
        if diff_seconds == 0:
            try:
                cur_sub = int(current_photo.sub_sec)
                prev_sub = int(prev_photo.sub_sec)
                # A very rough approximation, we just care if they are close.
                # Usually sub_sec is 2 digits (1/100s)
                diff_seconds = abs(cur_sub - prev_sub) / 100.0
            except ValueError:
                pass
                
        if diff_seconds <= threshold_seconds:
            # Belongs to the current burst
            current_burst_photos.append(ScoredPhoto(info=current_photo))
        else:
            # Start a new burst
            bursts.append(Burst(photos=current_burst_photos))
            current_burst_photos = [ScoredPhoto(info=current_photo)]
            
    # Add the last burst
    if current_burst_photos:
        bursts.append(Burst(photos=current_burst_photos))
        
    logger.info(f"Created {len(bursts)} bursts.")
    
    return bursts
