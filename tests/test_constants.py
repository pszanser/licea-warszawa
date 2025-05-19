import pytest
from scripts.config.constants import ALL_SUBJECTS, WARSAW_CENTER_LAT, WARSAW_CENTER_LON

def test_all_subjects_non_empty():
    assert isinstance(ALL_SUBJECTS, list)
    assert len(ALL_SUBJECTS) > 0

def test_warsaw_center_coordinates_type():
    assert isinstance(WARSAW_CENTER_LAT, float)
    assert isinstance(WARSAW_CENTER_LON, float)