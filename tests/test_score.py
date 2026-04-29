import pytest
import pandas as pd
import numpy as np
from scripts.analysis.score import (
    _compute_min_prog,
    add_distance_from_point,
    add_metrics,
    compute_composite,
    haversine_km,
    risk_label,
    select_start_point,
    score_personalized_classes,
    shortlist_schools_by_distance,
    summarize_best_schools,
)


@pytest.fixture
def sample_school_data():
    """
    Fixture zwracająca przykładowy zbiór danych szkół do testów.

    Zawiera podstawowe dane potrzebne do testowania funkcji oceniających szkoły,
    w tym pozycje rankingowe, czasy dojazdu i progi punktowe.
    """
    return pd.DataFrame(
        {
            "RankingPoz": [1, 2],
            "CzasDojazdu": [10, 20],
            "Prog_min_klasa": [100, 110],
            "Prog_min_szkola": [90, 90],
            "PrzedmiotyRozszerzone": ["matematyka", "historia"],
        }
    )


@pytest.mark.parametrize(
    "input_data,expected_result",
    [
        ({"Prog_min_klasa": [np.nan, 150], "Prog_min_szkola": [120, 130]}, [120, 150]),
        ({"Prog_min_klasa": [140], "Prog_min_szkola": [120]}, [140]),
    ],
    ids=["nan_value", "valid_values"],
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
    df = pd.DataFrame(
        {
            "RankingPoz": [1],
            "CzasDojazdu": [20],
            "Prog_min_klasa": [110],
            "Prog_min_szkola": [100],
            "PrzedmiotyRozszerzone": ["matematyka"],
        }
    )
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
    df = pd.DataFrame(
        {
            "RankingPoz": [2, 1],
            "CzasDojazdu": [20, 10],
            "Prog_min_klasa": [110, 100],
            "Prog_min_szkola": [100, 90],
            "PrzedmiotyRozszerzone": ["historia", "matematyka"],
        }
    )
    out = add_metrics(df, P=130)
    result = compute_composite(out)
    assert list(result.index) == [1, 0]


def test_haversine_km_handles_distance_and_missing_values():
    distance = haversine_km(52.2297, 21.0122, 52.2297, 21.1122)
    assert 6.5 < distance < 7.5

    df = pd.DataFrame({"SzkolaLat": [52.2297, np.nan], "SzkolaLon": [21.1122, 21.0]})
    result = add_distance_from_point(df, 52.2297, 21.0122)

    assert result["OdlegloscKm"].notna().tolist() == [True, False]


def test_shortlist_schools_by_distance_limits_and_sorts():
    schools = pd.DataFrame(
        {
            "NazwaSzkoly": ["C", "A", "B"],
            "OdlegloscKm": [3.0, 1.0, 2.0],
        }
    )

    result = shortlist_schools_by_distance(schools, limit=2)

    assert result["NazwaSzkoly"].tolist() == ["A", "B"]


def test_shortlist_schools_by_distance_respects_max_distance():
    schools = pd.DataFrame(
        {
            "NazwaSzkoly": ["C", "A", "B"],
            "OdlegloscKm": [9.0, 1.0, 4.0],
        }
    )

    result = shortlist_schools_by_distance(schools, limit=10, max_distance_km=5)

    assert result["NazwaSzkoly"].tolist() == ["A", "B"]


def test_score_personalized_classes_returns_fit_score_between_zero_and_hundred():
    classes = pd.DataFrame(
        {
            "RankingPoz": [1, 50],
            "Prog_min_klasa": [120, 150],
            "Prog_min_szkola": [110, 140],
            "OdlegloscKm": [2.0, 10.0],
            "matematyka": [1, 0],
            "OddzialNazwa": ["mat-fiz", "hum"],
        }
    )

    result = score_personalized_classes(
        classes,
        points=135,
        weights={"ranking": 5, "admission": 5, "distance": 5, "profile": 5},
        profile_subjects=["matematyka"],
    )

    assert result["FitScore"].between(0, 100).all()
    assert result.iloc[0]["OddzialNazwa"] == "mat-fiz"
    assert "RyzykoProgu" in result.columns
    assert "BrakiDanych" in result.columns
    assert "Dlaczego" in result.columns
    assert {"RankingScore", "AdmissionScore", "DistanceScore", "ProfileScore"}.issubset(
        result.columns
    )


def test_score_personalized_classes_scores_distance_on_absolute_scale():
    classes = pd.DataFrame(
        {
            "Prog_min_klasa": [100, 100, 100, 100],
            "Prog_min_szkola": [100, 100, 100, 100],
            "OdlegloscKm": [0.0, 7.5, 15.0, 20.0],
            "OddzialNazwa": ["zero", "half", "limit", "far"],
        }
    )

    result = score_personalized_classes(
        classes,
        points=120,
        weights={"distance": 10},
        distance_score_limit_km=15,
    ).sort_values("OdlegloscKm")

    assert result["DistanceScore"].round(1).tolist() == [100.0, 50.0, 0.0, 0.0]
    assert result["FitScore"].round(1).tolist() == [100.0, 50.0, 0.0, 0.0]


def test_score_personalized_classes_uses_stable_ranking_reference():
    classes = pd.DataFrame(
        {
            "RankingPoz": [10],
            "Prog_min_klasa": [100],
            "Prog_min_szkola": [100],
            "OdlegloscKm": [1.0],
        }
    )

    result = score_personalized_classes(
        classes,
        points=120,
        weights={"ranking": 10},
        ranking_max_reference=50,
    )

    assert result.iloc[0]["RankingScore"] == pytest.approx(81.632653, rel=1e-5)
    assert result.iloc[0]["FitScore"] == pytest.approx(81.632653, rel=1e-5)


def test_score_personalized_classes_counts_missing_weighted_components_as_zero():
    classes = pd.DataFrame(
        {
            "RankingPoz": [1, np.nan],
            "Prog_min_klasa": [120, 130],
            "Prog_min_szkola": [110, 120],
            "OdlegloscKm": [0.0, 0.0],
        }
    )

    result = score_personalized_classes(
        classes,
        points=140,
        weights={"ranking": 10},
    )

    assert result.loc[0, "FitScore"] == 100
    assert result.loc[1, "FitScore"] == 0
    assert result.loc[1, "BrakiDanych"] == "brak rankingu"
    assert "brak rankingu" in result.loc[1, "Dlaczego"]


def test_score_personalized_classes_marks_missing_threshold():
    classes = pd.DataFrame(
        {
            "RankingPoz": [1, 1],
            "Prog_min_klasa": [120, np.nan],
            "Prog_min_szkola": [110, np.nan],
            "OdlegloscKm": [0.0, 0.0],
        }
    )

    result = score_personalized_classes(
        classes,
        points=140,
        weights={"admission": 10},
    )

    assert pd.notna(result.loc[0, "FitScore"])
    assert result.loc[1, "FitScore"] == 0
    assert result.loc[1, "BrakiDanych"] == "brak progu"
    assert "brak progu" in result.loc[1, "Dlaczego"]


def test_summarize_best_schools_uses_best_class_and_adds_context_columns():
    fit_results = pd.DataFrame(
        {
            "SzkolaIdentyfikator": ["S1", "S1", "S2"],
            "FitScore": [60.0, 90.0, 80.0],
            "NazwaSzkoly": ["Szkoła A", "Szkoła A", "Szkoła B"],
            "Dzielnica": ["Mokotów", "Mokotów", "Śródmieście"],
            "OddzialNazwa": ["1a", "1b", "1c"],
            "OdlegloscKm": [3.0, 3.0, 5.0],
            "RankingScore": [70, 90, 80],
            "AdmissionScore": [95, 90, 75],
            "DistanceScore": [80, 80, 60],
            "ProfileScore": [50, 100, 100],
            "RankingPoz": [20, 20, 10],
            "MinProg": [130, 140, 150],
            "AdmitMargin": [30, 20, 10],
            "RyzykoProgu": ["bezpiecznie", "bezpiecznie", "realnie"],
            "BrakiDanych": ["", "brak progu", ""],
            "PrzedmiotyRozszerzone": ["mat", "mat-fiz", "bio-chem"],
            "Dlaczego": ["niżej", "najlepsza klasa", "druga szkoła"],
        }
    )

    result = summarize_best_schools(fit_results)

    assert result["NazwaSzkoly"].tolist() == ["Szkoła A", "Szkoła B"]
    assert result.iloc[0]["OddzialNazwa"] == "1b"
    assert result.iloc[0]["Liczba pasujących klas"] == 2
    assert result.columns.tolist() == [
        "FitScore",
        "NazwaSzkoly",
        "Dzielnica",
        "OddzialNazwa",
        "Liczba pasujących klas",
        "OdlegloscKm",
        "RankingScore",
        "AdmissionScore",
        "DistanceScore",
        "ProfileScore",
        "RankingPoz",
        "MinProg",
        "AdmitMargin",
        "RyzykoProgu",
        "BrakiDanych",
        "PrzedmiotyRozszerzone",
        "Dlaczego",
    ]


def test_summarize_best_schools_keeps_whole_best_class_row():
    fit_results = pd.DataFrame(
        {
            "SzkolaIdentyfikator": ["S1", "S1"],
            "FitScore": [90.0, 80.0],
            "NazwaSzkoly": ["Szkoła A", "Szkoła A"],
            "OddzialNazwa": ["1b", "1a"],
            "BrakiDanych": [np.nan, "brak progu"],
            "PrzedmiotyRozszerzone": [np.nan, "mat-fiz"],
        }
    )

    result = summarize_best_schools(fit_results)

    assert result.iloc[0]["OddzialNazwa"] == "1b"
    assert pd.isna(result.iloc[0]["BrakiDanych"])
    assert pd.isna(result.iloc[0]["PrzedmiotyRozszerzone"])


def test_summarize_best_schools_requires_identifier_and_score():
    with pytest.raises(ValueError, match="FitScore"):
        summarize_best_schools(pd.DataFrame({"SzkolaIdentyfikator": ["S1"]}))


@pytest.mark.parametrize(
    "margin,expected",
    [
        (20, "bezpiecznie"),
        (1, "realnie"),
        (-5, "ryzykownie"),
        (-20, "bardzo ryzykownie"),
        (np.nan, "brak danych"),
    ],
)
def test_risk_label(margin, expected):
    assert risk_label(margin) == expected


def test_select_start_point_requires_map_data():
    assert select_start_point(None) is None
    assert select_start_point({"center": {"lat": 52.2, "lng": 21.0}}) is None


def test_select_start_point_uses_center_when_allowed():
    result = select_start_point(
        {"center": {"lat": 52.2, "lng": 21.0}}, allow_center=True
    )

    assert result == (52.2, 21.0)


def test_select_start_point_prefers_click_over_center():
    result = select_start_point(
        {
            "last_clicked": {"lat": 52.1, "lng": 21.1},
            "center": {"lat": 52.2, "lng": 21.0},
        },
        allow_center=True,
    )

    assert result == (52.1, 21.1)
