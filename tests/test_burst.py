import datetime
from pathlib import Path

from good_birds.models import PhotoInfo
from good_birds.burst import group_into_bursts

def _make_photo(seconds: int, sub_sec: str = "00") -> PhotoInfo:
    return PhotoInfo(
        path=Path(f"img_{seconds}_{sub_sec}.CR2"),
        timestamp=datetime.datetime(2023, 1, 1, 12, 0, seconds),
        sub_sec=sub_sec
    )

def test_group_into_bursts_empty():
    assert group_into_bursts([]) == []

def test_group_into_bursts_single_photo():
    photos = [_make_photo(0)]
    bursts = group_into_bursts(photos)
    assert len(bursts) == 1
    assert len(bursts[0]) == 1

def test_group_into_bursts_simple():
    # 0s, 1s (burst 1), 5s, 6s (burst 2)
    photos = [
        _make_photo(0),
        _make_photo(1),
        _make_photo(5),
        _make_photo(6),
    ]
    bursts = group_into_bursts(photos, threshold_seconds=1.5)
    
    assert len(bursts) == 2
    assert len(bursts[0]) == 2
    assert len(bursts[1]) == 2
    
    assert bursts[0].photos[0].info.path.name == "img_0_00.CR2"
    assert bursts[1].photos[0].info.path.name == "img_5_00.CR2"

def test_group_into_bursts_subseconds():
    # 0.0s, 0.5s, 1.2s
    # In EXIF, timestamp is same second, sub_sec differs
    photos = [
        PhotoInfo(Path("1"), datetime.datetime(2023, 1, 1, 12, 0, 0), "00"),
        PhotoInfo(Path("2"), datetime.datetime(2023, 1, 1, 12, 0, 0), "50"),
        PhotoInfo(Path("3"), datetime.datetime(2023, 1, 1, 12, 0, 1), "20"),
    ]
    
    # Threshold 0.6s -> should group 1&2, put 3 in new burst 
    # (1.2 - 0.5 = 0.7 > 0.6)
    bursts = group_into_bursts(photos, threshold_seconds=0.6)
    assert len(bursts) == 2
    assert len(bursts[0]) == 2
    assert len(bursts[1]) == 1
