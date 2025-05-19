import pytest
import pandas as pd
import numpy as np
from scripts.analysis.score import _compute_min_prog, add_metrics, compute_composite

def test__compute_min_prog_nan():
    df = pd.DataFrame({
        "Prog_min_klasa": [np.nan, 150],
        "Prog_min_szkola": [120, 130],
    })
    result = _compute_min_prog(df)
    expected = pd.Series([120, 150], name="Prog_min_klasa")
    pd.testing.assert_series_equal(result, expected, check_dtype=False)

def test__compute_min_prog_value():
    df = pd.DataFrame({
        "Prog_min_klasa": [140],
        "Prog_min_szkola": [120],
    })
    result = _compute_min_prog(df)
    assert result.iloc[0] == 140

def test_add_metrics_columns():
    """
    Testuje, czy funkcja add_metrics dodaje oczekiwane kolumny metryk do DataFrame.
    
    Sprawdza, czy wynikowy DataFrame zawiera kolumny: "Quality", "AdmitProb", "CommuteScore", "ProfileMatch", "MinProg" oraz "AdmitMargin".
    """
    df = pd.DataFrame({
        "RankingPoz": [1],
        "CzasDojazdu": [20],
        "Prog_min_klasa": [110],
        "Prog_min_szkola": [100],
        "PrzedmiotyRozszerzone": ["matematyka"],
    })
    out = add_metrics(df, P=130)
    expected_cols = {
        "Quality",
        "AdmitProb",
        "CommuteScore",
        "ProfileMatch",
        "MinProg",
        "AdmitMargin",
    }
    assert expected_cols.issubset(out.columns)

def test_add_metrics_profile_match():
    df = pd.DataFrame({
        "RankingPoz": [1, 2],
        "CzasDojazdu": [10, 15],
        "Prog_min_klasa": [100, 110],
        "Prog_min_szkola": [90, 90],
        "PrzedmiotyRozszerzone": ["matematyka", "historia"],
    })
    out = add_metrics(df, P=120, desired_subject="matematyka")
    assert out["ProfileMatch"].tolist() == [1, 0]

def test_compute_composite_default_weights():
    """
    Testuje, czy funkcja compute_composite poprawnie dodaje kolumnę 'Composite' i czy wyniki są posortowane zgodnie z domyślnymi wagami metryk.
    """
    df = pd.DataFrame({
        "RankingPoz": [1, 2],
        "CzasDojazdu": [10, 20],
        "Prog_min_klasa": [100, 110],
        "Prog_min_szkola": [90, 90],
        "PrzedmiotyRozszerzone": ["mat", "his"],
    })
    out = add_metrics(df, P=130)
    result = compute_composite(out)
    assert "Composite" in result.columns
    assert result.iloc[0]["Composite"] >= result.iloc[1]["Composite"]

def test_compute_composite_custom_weights():
    """
    Testuje funkcję compute_composite z niestandardowymi wagami, sprawdzając czy metryka ProfileMatch jest prawidłowo uwzględniana przy obliczaniu wyniku złożonego.
    """
    df = pd.DataFrame({
        "RankingPoz": [1, 2],
        "CzasDojazdu": [10, 20],
        "Prog_min_klasa": [100, 110],
        "Prog_min_szkola": [90, 90],
        "PrzedmiotyRozszerzone": ["mat", "his"],
    })
    out = add_metrics(df, P=130, desired_subject="mat")
    w = {"wQ": 0, "wA": 0, "wC": 0, "wP": 1}
    result = compute_composite(out, w)
    assert result.iloc[0]["ProfileMatch"] >= result.iloc[1]["ProfileMatch"]

def test_compute_composite_missing_columns():
    df = pd.DataFrame({"A": [1]})
    with pytest.raises(ValueError):
        compute_composite(df)

def test_compute_composite_sorting():
    """
    Testuje, czy funkcja compute_composite zwraca DataFrame posortowany malejąco według wyniku złożonego.
    
    Sprawdza, czy indeksy w wyniku odpowiadają kolejności posortowanych wartości Composite.
    """
    df = pd.DataFrame({
        "RankingPoz": [2, 1],
        "CzasDojazdu": [20, 10],
        "Prog_min_klasa": [110, 100],
        "Prog_min_szkola": [100, 90],
        "PrzedmiotyRozszerzone": ["his", "mat"],
    })
    out = add_metrics(df, P=130)
    result = compute_composite(out)
    assert list(result.index) == [1, 0]
