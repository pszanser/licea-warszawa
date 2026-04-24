import pandas as pd

from scripts.pipeline import (
    best_thresholds_for_keys,
    historical_school_thresholds,
    school_threshold_summary,
)


def test_best_thresholds_prefers_lower_priority_source():
    thresholds = pd.DataFrame(
        {
            "SzkolaIdentyfikator": ["lo_1", "lo_1"],
            "OddzialNazwa": ["1A", "1A"],
            "Prog_min_klasa": [120, 150],
            "threshold_year": [2024, 2025],
            "threshold_priority": [2, 1],
        }
    )

    result = best_thresholds_for_keys(
        thresholds, ["SzkolaIdentyfikator", "OddzialNazwa"]
    )

    assert len(result) == 1
    assert result.iloc[0]["Prog_min_klasa"] == 150
    assert result.iloc[0]["threshold_year"] == 2025


def test_school_threshold_summary_uses_one_active_year_per_school():
    thresholds = pd.DataFrame(
        {
            "SzkolaIdentyfikator": ["lo_1", "lo_1", "lo_1", "lo_2"],
            "Prog_min_klasa": [120, 130, 150, 100],
            "threshold_year": [2024, 2025, 2025, 2024],
            "threshold_kind": ["historical", "actual", "actual", "historical"],
            "threshold_label": [
                "historyczne progi 2024",
                "faktyczne progi 2025",
                "faktyczne progi 2025",
                "historyczne progi 2024",
            ],
            "threshold_priority": [2, 1, 1, 2],
        }
    )

    result = school_threshold_summary(thresholds)
    lo_1 = result[result["SzkolaIdentyfikator"].eq("lo_1")].iloc[0]
    lo_2 = result[result["SzkolaIdentyfikator"].eq("lo_2")].iloc[0]

    assert lo_1["Prog_min_szkola"] == 130
    assert lo_1["Prog_max_szkola"] == 150
    assert lo_1["Prog_szkola_threshold_year"] == 2025
    assert lo_2["Prog_min_szkola"] == 100
    assert lo_2["Prog_szkola_threshold_year"] == 2024


def test_historical_school_thresholds_lists_all_known_years():
    thresholds = pd.DataFrame(
        {
            "SzkolaIdentyfikator": ["lo_1", "lo_1", "lo_1"],
            "Prog_min_klasa": [120, 130, 150],
            "threshold_year": [2024, 2025, 2025],
        }
    )

    result = historical_school_thresholds(thresholds)

    assert result.iloc[0]["Progi_historyczne_szkola"] == "2025: 130-150; 2024: 120"
    assert result.iloc[0]["Progi_historyczne_lata"] == "2025/2024"
