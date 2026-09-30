"""OpenCV seek versus a sequential read, on the real USC files when they are mounted."""

from pathlib import Path

import pytest

from projects.voices.frame_check import run_check
from projects.voices.sources import PYFEAT_ROOT


@pytest.mark.skipif(not (PYFEAT_ROOT / "usc").is_dir(), reason="Py-Feat USC sidecars are not on this machine")
@pytest.mark.skipif(not Path("/home/mjma/voices/test_data/videos").is_dir(), reason="USC videos are not on this machine")
def test_seek_matches_sequential_and_landmarks_sit_on_the_box():
    report = run_check(20)
    mismatches = [item["frame"] for item in report["seek"] if not item["match"]]
    weak = [item for item in report["landmarks"] if item["fraction"] < 0.5]
    assert report["seek_ok"], mismatches
    assert report["landmarks_ok"], weak
