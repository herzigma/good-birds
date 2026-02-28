import datetime
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
import numpy as np


@dataclass
class PhotoInfo:
    """Represents metadata and the embedded preview for a single RAW photo."""
    path: Path
    timestamp: datetime.datetime
    sub_sec: str
    iso: Optional[int] = None
    shutter_speed: Optional[str] = None  # e.g., "1/1000"
    aperture: Optional[float] = None
    
    # Store the preview image as a numpy array lazily if needed, 
    # but usually we'll process it immediately to save memory.
    # To avoid holding massive arrays in memory for thousands of photos,
    # we'll read and process the preview on demand.
    
    @property
    def full_timestamp_sort_key(self) -> tuple:
        """Helper to sort photos accurately including sub-second data."""
        return (self.timestamp, self.sub_sec)


@dataclass
class ScoredPhoto:
    """A photo that has been scored for sharpness and exposure."""
    info: PhotoInfo
    sharpness_score: float = 0.0
    exposure_score: float = 0.0
    combined_score: float = 0.0


@dataclass
class Burst:
    """A collection of photos taken in rapid succession."""
    photos: List[ScoredPhoto] = field(default_factory=list)
    best_photo: Optional[ScoredPhoto] = None
    
    @property
    def start_time(self) -> datetime.datetime:
        return self.photos[0].info.timestamp if self.photos else None
        
    @property
    def end_time(self) -> datetime.datetime:
        return self.photos[-1].info.timestamp if self.photos else None
        
    def __len__(self) -> int:
        return len(self.photos)
