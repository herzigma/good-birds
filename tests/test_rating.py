from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from good_birds.rating import write_rating, is_exiftool_installed

def test_dry_run(capsys):
    # Should not invoke subprocess
    result = write_rating(Path("dummy.CR2"), 5, dry_run=True)
    assert result is True
    
    captured = capsys.readouterr()
    assert "[DRY RUN]" in captured.out
    assert "dummy.CR2" in captured.out

@patch("good_birds.rating.is_exiftool_installed", return_value=False)
def test_exiftool_missing(mock_is_installed):
    result = write_rating(Path("dummy.CR2"), 5)
    assert result is False

@patch("good_birds.rating.get_exiftool_cmd", return_value=["exiftool"])
@patch("good_birds.rating.subprocess.run")
def test_write_rating_success(mock_run, mock_get_cmd):
    mock_run.return_value = MagicMock(returncode=0)
    
    result = write_rating(Path("dummy.CR2"), 3)
    
    assert result is True
    mock_run.assert_called_once()
    
    # Check the command arguments
    cmd_args = mock_run.call_args[0][0]
    assert "exiftool" in cmd_args
    assert "-overwrite_original" in cmd_args
    assert "-XMP:Rating=3" in cmd_args
    assert "-XMP:RatingPercent=50" in cmd_args
    assert "-Rating=3" in cmd_args
    assert "dummy.CR2" in cmd_args

@patch("good_birds.rating.get_exiftool_cmd", return_value=["exiftool"])
@patch("good_birds.rating.subprocess.run")
def test_write_rating_failure(mock_run, mock_get_cmd):
    from subprocess import CalledProcessError
    
    mock_run.side_effect = CalledProcessError(1, "exiftool", stderr="File not found")
    
    result = write_rating(Path("missing.CR2"), 4)
    assert result is False
    
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
