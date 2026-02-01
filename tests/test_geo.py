import pytest
import pandas as pd
from scripts import geo


def test_haversine_distance_basic():
    dist = geo.haversine_distance(0, 0, 0, 1)
    assert dist == pytest.approx(111.19, rel=1e-2)


def test_find_nearest_schools():
    df = pd.DataFrame(
        {
            "NazwaSzkoly": ["A", "B", "C"],
            "SzkolaLat": [0.0, 0.0, 1.0],
            "SzkolaLon": [0.0, 2.0, 0.0],
        }
    )
    res = geo.find_nearest_schools(df, 0.0, 0.0, top_n=2)
    assert list(res["NazwaSzkoly"]) == ["A", "C"]

def test_find_nearest_schools_empty_dataframe():
    """Test behavior with empty DataFrame."""
    df = pd.DataFrame({"NazwaSzkoly": [], "SzkolaLat": [], "SzkolaLon": []})
    result = geo.find_nearest_schools(df, 0.0, 0.0)
    assert result.empty

def test_find_nearest_schools_missing_coordinates():
    """Test behavior with missing coordinates."""
    df = pd.DataFrame(
        {
            "NazwaSzkoly": ["A", "B", "C"],
            "SzkolaLat": [0.0, None, 1.0],
            "SzkolaLon": [0.0, 2.0, None],
        }
    )
    result = geo.find_nearest_schools(df, 0.0, 0.0, top_n=5)
    assert len(result) == 1  # Only school A has complete coordinates
    assert result.iloc[0]["NazwaSzkoly"] == "A"

def test_find_nearest_schools_top_n_larger_than_available():
    """Test behavior when top_n is larger than available schools."""
    df = pd.DataFrame(
        {
            "NazwaSzkoly": ["A", "B"],
            "SzkolaLat": [0.0, 1.0],
            "SzkolaLon": [0.0, 0.0],
        }
    )
    result = geo.find_nearest_schools(df, 0.0, 0.0, top_n=10)
    assert len(result) == 2  # Should return all available schools
