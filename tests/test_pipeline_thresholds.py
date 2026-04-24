import pandas as pd

from scripts.pipeline import (
    apply_latest_rankings,
    best_thresholds_for_keys,
    historical_school_thresholds,
    school_threshold_summary,
    school_ranking_summary,
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


def test_school_ranking_summary_lists_all_known_years_and_latest_rank():
    rankings = pd.DataFrame(
        {
            "SzkolaIdentyfikator": ["lo_1", "lo_1", "lo_2"],
            "RankingPoz": [8, 4, 30],
            "RankingPozTekst": ["8", "4=", "30"],
            "year": [2025, 2026, 2025],
        }
    )

    result = school_ranking_summary(rankings)
    lo_1 = result[result["SzkolaIdentyfikator"].eq("lo_1")].iloc[0]

    assert lo_1["RankingPozNajnowszy"] == 4
    assert lo_1["RankingPozTekstNajnowszy"] == "4"
    assert lo_1["RankingRok"] == 2026
    assert lo_1["Ranking_historyczny_szkola"] == "2026: 4; 2025: 8"
    assert lo_1["Ranking_lata"] == "2026/2025"


def test_apply_latest_rankings_keeps_year_rank_and_sets_latest_rank():
    sheets = {
        "schools": pd.DataFrame(
            {
                "SzkolaIdentyfikator": ["lo_1"],
                "RankingPoz": [8],
                "RankingPozTekst": ["8"],
            }
        ),
        "classes": pd.DataFrame(
            {
                "SzkolaIdentyfikator": ["lo_1"],
                "OddzialNazwa": ["1A"],
                "RankingPoz": [8],
                "RankingPozTekst": ["8"],
            }
        ),
        "rankings": pd.DataFrame(
            {
                "SzkolaIdentyfikator": ["lo_1", "lo_1"],
                "RankingPoz": [8, 4],
                "RankingPozTekst": ["8", "4="],
                "year": [2025, 2026],
            }
        ),
    }

    result = apply_latest_rankings(sheets)
    school = result["schools"].iloc[0]
    class_row = result["classes"].iloc[0]

    assert school["RankingPozRokuDanych"] == 8
    assert school["RankingPoz"] == 4
    assert school["RankingPozTekst"] == "4"
    assert school["RankingRok"] == 2026
    assert school["Ranking_historyczny_szkola"] == "2026: 4; 2025: 8"
    assert class_row["RankingPoz"] == 4
