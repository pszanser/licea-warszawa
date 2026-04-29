from pathlib import Path

import folium
import pandas as pd

from scripts.visualization.generate_map import (
    add_school_markers_to_map,
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


# ---------------------------------------------------------------------------
# add_school_markers_to_map – testy linku dojazdu
# ---------------------------------------------------------------------------

_SCHOOL_ROW = {
    "SzkolaIdentyfikator": "lo_1",
    "NazwaSzkoly": "XIV LO",
    "AdresSzkoly": "ul. Złota 1, Warszawa",
    "SzkolaLat": 52.23,
    "SzkolaLon": 21.01,
    "Dzielnica": "Śródmieście",
    "TypSzkoly": "liceum",
    "Ranking_historyczny_szkola": None,
    "Progi_historyczne_szkola": None,
    "RankingPoz": None,
    "RankingRok": None,
    "url": None,
}


def _make_map_and_get_popup(origin_lat=None, origin_lon=None) -> str:
    """Pomocnik: buduje mapę z jedną szkołą i zwraca HTML popupu."""
    df = pd.DataFrame([_SCHOOL_ROW])
    m = folium.Map(location=[52.23, 21.01], zoom_start=11)
    add_school_markers_to_map(
        folium_map_object=m,
        df_schools_to_display=df,
        class_count_per_school={},
        filtered_class_details_per_school={},
        school_summary_from_filtered={},
        origin_lat=origin_lat,
        origin_lon=origin_lon,
    )
    return m.get_root().render()


def test_popup_without_origin_has_no_commute_link():
    html = _make_map_and_get_popup()
    assert "travelmode=transit" not in html
    assert "Sprawdź dojazd" not in html
    # Standardowy link do miejsca docelowego nadal obecny
    assert "destination=52.23,21.01" in html


def test_popup_with_origin_has_commute_link():
    html = _make_map_and_get_popup(origin_lat=52.20, origin_lon=21.00)
    assert "travelmode=transit" in html
    assert "&origin=52.2,21.0" in html
    assert "destination=52.23,21.01" in html
    assert "Sprawdź dojazd" in html


def test_popup_with_origin_retains_address_link():
    """Istniejący link na adresie szkoły musi pozostać bez zmian."""
    html = _make_map_and_get_popup(origin_lat=52.20, origin_lon=21.00)
    # Statyczny link destination bez origin (link na samym adresie szkoły)
    assert "maps/dir/?api=1&destination=52.23,21.01" in html
