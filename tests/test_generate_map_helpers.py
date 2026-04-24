from pathlib import Path

import pandas as pd

from scripts.visualization.generate_map import (
    aggregate_filtered_class_data,
    format_ranking_history_for_display,
    get_default_year,
    get_subjects_from_dataframe,
)


def test_get_default_year_prefers_latest_full_year(monkeypatch):
    metadata = pd.DataFrame(
        {
            "year": [2025, 2026],
            "data_status": ["full", "planned_offer"],
        }
    )
    monkeypatch.setattr(pd, "read_excel", lambda *args, **kwargs: metadata)

    assert get_default_year(Path("ignored.xlsx"), [2026, 2025]) == 2025


def test_get_default_year_falls_back_to_latest_available_year(monkeypatch):
    metadata = pd.DataFrame(
        {
            "year": [2025, 2026],
            "data_status": ["legacy", "planned_offer"],
        }
    )
    monkeypatch.setattr(pd, "read_excel", lambda *args, **kwargs: metadata)

    assert get_default_year(Path("ignored.xlsx"), [2026, 2025]) == 2026


def test_format_ranking_history_for_display():
    assert (
        format_ranking_history_for_display("2026: 4; 2025: 8") == "4 (2026), 8 (2025)"
    )


def test_get_subjects_from_dataframe_skips_empty_binary_columns():
    classes = pd.DataFrame(
        {
            "matematyka": [0, 1],
            "biologia": [0, 0],
            "IdSzkoly": [pd.NA, pd.NA],
        }
    )

    assert get_subjects_from_dataframe(classes) == ["matematyka"]


def test_aggregate_filtered_class_data_keeps_ranking_year():
    classes = pd.DataFrame(
        {
            "SzkolaIdentyfikator": ["lo_1", "lo_1"],
            "OddzialNazwa": ["1A", "1B"],
            "Prog_min_klasa": [120, 130],
            "Prog_min_szkola": [120, 120],
            "Prog_max_szkola": [130, 130],
            "RankingPoz": [8, 8],
            "RankingRok": [2026, 2026],
        }
    )
    schools = pd.DataFrame({"SzkolaIdentyfikator": ["lo_1"]})

    _, _, _, summary = aggregate_filtered_class_data(classes, schools, True)

    assert summary["lo_1"]["RankingPoz"] == 8
    assert summary["lo_1"]["RankingRok"] == 2026
