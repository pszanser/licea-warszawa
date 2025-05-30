import pytest
from scripts.config.constants import ALL_SUBJECTS, WARSAW_CENTER_LAT, WARSAW_CENTER_LON


def test_all_subjects_non_empty():
    """
    Testuje, czy lista ALL_SUBJECTS nie jest pusta.

    Sprawdza, czy ALL_SUBJECTS jest listą i czy zawiera co najmniej jeden element.
    """
    assert isinstance(ALL_SUBJECTS, list)
    assert len(ALL_SUBJECTS) > 0


@pytest.mark.parametrize(
    "coordinate,expected_type", [(WARSAW_CENTER_LAT, float), (WARSAW_CENTER_LON, float)]
)
def test_warsaw_center_coordinates_type(coordinate, expected_type):
    """
    Testuje, czy współrzędne centrum Warszawy są typu float.

    Sprawdza, czy zmienne WARSAW_CENTER_LAT i WARSAW_CENTER_LON
    są zdefiniowane jako wartości zmiennoprzecinkowe.
    """
    assert isinstance(coordinate, expected_type)
