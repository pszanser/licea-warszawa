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
