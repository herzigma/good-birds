import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from good_birds.rating import write_rating, write_xmp_sidecar, write_rrdata_sidecar, is_exiftool_installed

def test_dry_run(capsys, tmp_path):
    dummy = tmp_path / "dummy.CR2"
    dummy.touch()
    # Should not invoke subprocess and should NOT create a sidecar
    result = write_rating(dummy, 5, dry_run=True)
    assert result is True
    
    captured = capsys.readouterr()
    assert "[DRY RUN]" in captured.out
    assert "dummy.CR2" in captured.out
    
    # Verify no sidecar was created
    sidecar = tmp_path / "dummy.CR2.xmp"
    assert not sidecar.exists()

@patch("good_birds.rating.is_exiftool_installed", return_value=False)
def test_exiftool_missing(mock_is_installed):
    result = write_rating(Path("dummy.CR2"), 5)
    assert result is False

@patch("good_birds.rating.get_exiftool_cmd", return_value=["exiftool"])
@patch("good_birds.rating.subprocess.run")
def test_write_rating_success(mock_run, mock_get_cmd, tmp_path):
    mock_run.return_value = MagicMock(returncode=0)
    
    dummy = tmp_path / "dummy.CR2"
    dummy.touch()
    result = write_rating(dummy, 3)
    
    assert result is True
    mock_run.assert_called_once()
    
    # Check the command arguments
    cmd_args = mock_run.call_args[0][0]
    assert "exiftool" in cmd_args
    assert "-overwrite_original" in cmd_args
    assert "-XMP:Rating=3" in cmd_args
    assert "-XMP:RatingPercent=50" in cmd_args
    assert "-Rating=3" in cmd_args
    
    # Verify sidecar was also created
    sidecar = tmp_path / "dummy.CR2.xmp"
    assert sidecar.exists()
    content = sidecar.read_text(encoding="utf-8")
    assert 'xmp:Rating="3"' in content

    # Verify rr_sidecar was not created
    rr_sidecar = tmp_path / "dummy.CR2.rrdata"
    assert not rr_sidecar.exists()

@patch("good_birds.rating.get_exiftool_cmd", return_value=["exiftool"])
@patch("good_birds.rating.subprocess.run")
def test_write_rating_failure(mock_run, mock_get_cmd):
    from subprocess import CalledProcessError
    
    mock_run.side_effect = CalledProcessError(1, "exiftool", stderr="File not found")
    
    result = write_rating(Path("missing.CR2"), 4)
    assert result is False

@patch("good_birds.rating.get_exiftool_cmd", return_value=["exiftool"])
@patch("good_birds.rating.subprocess.run")
def test_write_rating_no_sidecar(mock_run, mock_get_cmd, tmp_path):
    """Test that sidecar=False skips sidecar generation."""
    mock_run.return_value = MagicMock(returncode=0)
    
    dummy = tmp_path / "test.CR2"
    dummy.touch()
    result = write_rating(dummy, 5, sidecar=False)
    
    assert result is True
    mock_run.assert_called_once()
    
    # Verify NO sidecar was created
    sidecar = tmp_path / "test.CR2.xmp"
    assert not sidecar.exists()

    # Verify rr_sidecar was not created
    rr_sidecar = tmp_path / "test.CR2.rrdata"
    assert not rr_sidecar.exists()

@patch("good_birds.rating.get_exiftool_cmd", return_value=["exiftool"])
@patch("good_birds.rating.subprocess.run")
def test_write_ratings_rr_sidecar(mock_run, mock_get_cmd, tmp_path):
    mock_run.return_value = MagicMock(returncode=0)
    
    dummy = tmp_path / "test.CR2"
    dummy.touch()
    result = write_rating(dummy, 5, rr_sidecar=True)
    
    assert result is True
    mock_run.assert_called_once()
    
    # Verify sidecar was also created
    sidecar = tmp_path / "test.CR2.xmp"
    assert sidecar.exists()

    # Verify rr_sidecar was created
    rr_sidecar = tmp_path / "test.CR2.rrdata"
    assert rr_sidecar.exists()

@patch("good_birds.rating.get_exiftool_cmd", return_value=["exiftool"])
@patch("good_birds.rating.subprocess.run")
def test_write_ratings_rr_sidecar_low_rating(mock_run, mock_get_cmd, tmp_path):
    mock_run.return_value = MagicMock(returncode=0)
    
    dummy = tmp_path / "test.CR2"
    dummy.touch()
    result = write_rating(dummy, 3, rr_sidecar=True)  # rating != 5
    
    assert result is True
    mock_run.assert_called_once()
    
    # Verify sidecar was also created
    sidecar = tmp_path / "test.CR2.xmp"
    assert sidecar.exists()

    # Verify rr_sidecar was not created
    rr_sidecar = tmp_path / "test.CR2.rrdata"
    assert not rr_sidecar.exists()

# --- XMP Sidecar Tests ---

def test_write_xmp_sidecar_creates_file(tmp_path):
    """Test that write_xmp_sidecar creates a correctly named .xmp file."""
    dummy = tmp_path / "IMG_1234.CR2"
    dummy.touch()
    
    result = write_xmp_sidecar(dummy, 5)
    
    assert result is True
    sidecar = tmp_path / "IMG_1234.CR2.xmp"
    assert sidecar.exists()

def test_write_xmp_sidecar_content(tmp_path):
    """Test that the sidecar file contains valid XMP with the correct rating."""
    dummy = tmp_path / "photo.ARW"
    dummy.touch()
    
    write_xmp_sidecar(dummy, 3)
    
    sidecar = tmp_path / "photo.ARW.xmp"
    content = sidecar.read_text(encoding="utf-8")
    
    # Check for required XMP structure
    assert "<?xpacket" in content
    assert "x:xmpmeta" in content
    assert "rdf:RDF" in content
    assert 'xmlns:xmp="http://ns.adobe.com/xap/1.0/"' in content
    assert 'xmp:Rating="3"' in content

def test_write_xmp_sidecar_overwrites(tmp_path):
    """Test that writing a sidecar again updates the rating."""
    dummy = tmp_path / "test.CR2"
    dummy.touch()
    
    write_xmp_sidecar(dummy, 1)
    content1 = (tmp_path / "test.CR2.xmp").read_text(encoding="utf-8")
    assert 'xmp:Rating="1"' in content1
    
    write_xmp_sidecar(dummy, 5)
    content2 = (tmp_path / "test.CR2.xmp").read_text(encoding="utf-8")
    assert 'xmp:Rating="5"' in content2
    assert 'xmp:Rating="1"' not in content2
    
# --- rrdata Sidecar Tests ---

def test_write_rrdata_sidecar_creates_file(tmp_path):
    """Test that write_rrdata_sidecar creates a correctly named .rrdata file."""
    dummy = tmp_path / "IMG_1234.CR2"
    dummy.touch()
    
    result = write_rrdata_sidecar(dummy, 5)
    
    assert result is True
    sidecar = tmp_path / "IMG_1234.CR2.rrdata"
    assert sidecar.exists()

def test_write_rrdata_sidecar_content(tmp_path):
    """Test that the sidecar file contains valid rrdata with the correct rating."""
    dummy = tmp_path / "photo.ARW"
    dummy.touch()
    
    write_rrdata_sidecar(dummy, 3)
    
    sidecar = tmp_path / "photo.ARW.rrdata"
    content = sidecar.read_text(encoding="utf-8")
    
    # Check for required rrdata structure
    rrdata = json.loads(content)
    assert rrdata["version"] == 1
    assert rrdata["rating"] == 3
    assert isinstance(rrdata["adjustments"], dict)
    assert rrdata["tags"] is None

def test_write_rrdata_sidecar_overwrites(tmp_path):
    """Test that writing a sidecar again updates the rating."""
    dummy = tmp_path / "test.CR2"
    dummy.touch()
    
    write_rrdata_sidecar(dummy, 1)
    content1 = (tmp_path / "test.CR2.rrdata").read_text(encoding="utf-8")
    rrdata1 = json.loads(content1)
    assert rrdata1["rating"] == 1
    
    write_rrdata_sidecar(dummy, 5)
    content2 = (tmp_path / "test.CR2.rrdata").read_text(encoding="utf-8")
    rrdata2 = json.loads(content2)
    assert rrdata2["rating"] == 5
    
# --- Skip writing EXIF data to image Tests ---

@patch("good_birds.rating.get_exiftool_cmd", return_value=["exiftool"])
@patch("good_birds.rating.subprocess.run")
def test_write_no_exif(mock_run, mock_get_cmd, tmp_path):
    mock_run.return_value = MagicMock(returncode=0)
    
    dummy = tmp_path / "test.CR2"
    dummy.touch()
    result = write_rating(dummy, 5, write_exif=False)
    
    assert result is True
    mock_run.assert_not_called()
    
    # Verify sidecar was also created
    sidecar = tmp_path / "test.CR2.xmp"
    assert sidecar.exists()

    # Verify rr_sidecar was not created
    rr_sidecar = tmp_path / "test.CR2.rrdata"
    assert not rr_sidecar.exists()

@patch("good_birds.rating.get_exiftool_cmd", return_value=["exiftool"])
@patch("good_birds.rating.subprocess.run")
def test_write_no_exif(mock_run, mock_get_cmd, tmp_path):
    mock_run.return_value = MagicMock(returncode=0)
    
    dummy = tmp_path / "test.CR2"
    dummy.touch()
    result = write_rating(dummy, 5, sidecar=False, rr_sidecar=True, write_exif=False)
    
    assert result is True
    mock_run.assert_not_called()
    
    # Verify sidecar was also created
    sidecar = tmp_path / "test.CR2.xmp"
    assert not sidecar.exists()

    # Verify rr_sidecar was not created
    rr_sidecar = tmp_path / "test.CR2.rrdata"
    assert rr_sidecar.exists()

@pytest.mark.integration
def test_real_exiftool():
    """
    This test will be skipped without `-m integration`.
    It requires a real exiftool installation.
    """
    if not is_exiftool_installed():
        pytest.skip("exiftool not installed")
        
    # We don't want to actually write to files in an automated test
    # unless we create a temporary CR2, which is complex.
    # So we'll just test that is_exiftool_installed works correctly.
    assert is_exiftool_installed() is True
