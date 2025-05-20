import pytest
import pandas as pd
import numpy as np
from scripts.analysis.score import _compute_min_prog, add_metrics, compute_composite


@pytest.fixture
def sample_school_data():
    """
    Fixture zwracająca przykładowy zbiór danych szkół do testów.
    
    Zawiera podstawowe dane potrzebne do testowania funkcji oceniających szkoły,
    w tym pozycje rankingowe, czasy dojazdu i progi punktowe.
    """
    return pd.DataFrame({
        "RankingPoz": [1, 2],
        "CzasDojazdu": [10, 20],
        "Prog_min_klasa": [100, 110],
        "Prog_min_szkola": [90, 90],
        "PrzedmiotyRozszerzone": ["matematyka", "historia"],
    })


@pytest.mark.parametrize(
    "input_data,expected_result",
    [
        (
            {"Prog_min_klasa": [np.nan, 150], "Prog_min_szkola": [120, 130]},
            [120, 150]
        ),
        (
            {"Prog_min_klasa": [140], "Prog_min_szkola": [120]}, 
            [140]
        )
    ],
    ids=["nan_value", "valid_values"]
)
def test__compute_min_prog(input_data, expected_result):
    """
    Testuje funkcję _compute_min_prog, która wybiera progi punktowe.
    
    Sprawdza, czy funkcja poprawnie wybiera wartości progów punktowych:
    - gdy wartość Prog_min_klasa jest NaN, używa wartości z Prog_min_szkola
    - gdy obie wartości są dostępne, używa wartości z Prog_min_klasa
    """
    df = pd.DataFrame(input_data)
    result = _compute_min_prog(df)
    expected = pd.Series(expected_result, name="Prog_min_klasa")
    pd.testing.assert_series_equal(result, expected, check_dtype=False)


def test_add_metrics_columns():
    """
    Testuje, czy funkcja add_metrics dodaje oczekiwane kolumny metryk do DataFrame.
    
    Sprawdza, czy wynikowy DataFrame zawiera kolumny: "Quality", "AdmitProb", 
    "CommuteScore", "ProfileMatch", "MinProg" oraz "AdmitMargin".
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


def test_add_metrics_profile_match(sample_school_data):
    """
    Testuje, czy funkcja add_metrics poprawnie ocenia dopasowanie profilu.
    
    Sprawdza, czy kolumna ProfileMatch zawiera wartość 1 dla szkoły z przedmiotem rozszerzonym
    pasującym do przedmiotu pożądanego i 0 dla szkoły bez tego przedmiotu.
    """
    out = add_metrics(sample_school_data, P=120, desired_subject="matematyka")
    assert out["ProfileMatch"].tolist() == [1, 0]


def test_compute_composite_default_weights(sample_school_data):
    """
    Testuje, czy funkcja compute_composite poprawnie dodaje kolumnę 'Composite' 
    i czy wyniki są posortowane zgodnie z domyślnymi wagami metryk.
    """
    out = add_metrics(sample_school_data, P=130)
    result = compute_composite(out)
    assert "Composite" in result.columns
    assert result.iloc[0]["Composite"] >= result.iloc[1]["Composite"]


def test_compute_composite_custom_weights(sample_school_data):
    """
    Testuje funkcję compute_composite z niestandardowymi wagami.
    
    Sprawdza, czy metryka ProfileMatch jest prawidłowo uwzględniana przy obliczaniu
    wyniku złożonego, gdy jej waga jest ustawiona na 1, a wagi pozostałych metryk na 0.
    """
    out = add_metrics(sample_school_data, P=130, desired_subject="matematyka")
    w = {"wQ": 0, "wA": 0, "wC": 0, "wP": 1}
    result = compute_composite(out, w)
    assert result.iloc[0]["ProfileMatch"] >= result.iloc[1]["ProfileMatch"]


def test_compute_composite_missing_columns():
    """
    Testuje zachowanie funkcji compute_composite, gdy podany DataFrame 
    nie zawiera wymaganych kolumn.
    
    Sprawdza, czy funkcja zgłasza wyjątek ValueError przy braku wymaganych kolumn.
    """
    df = pd.DataFrame({"A": [1]})
    with pytest.raises(ValueError):
        compute_composite(df)


def test_compute_composite_sorting():
    """
    Testuje, czy funkcja compute_composite zwraca DataFrame posortowany 
    malejąco według wyniku złożonego.
    
    Sprawdza, czy indeksy w wyniku odpowiadają kolejności posortowanych wartości Composite.
    """
    df = pd.DataFrame({
        "RankingPoz": [2, 1],
        "CzasDojazdu": [20, 10],
        "Prog_min_klasa": [110, 100],
        "Prog_min_szkola": [100, 90],
        "PrzedmiotyRozszerzone": ["historia", "matematyka"],
    })
    out = add_metrics(df, P=130)
    result = compute_composite(out)
    assert list(result.index) == [1, 0]
