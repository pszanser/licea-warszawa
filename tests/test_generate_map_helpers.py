from pathlib import Path

import folium
import pandas as pd

from scripts.visualization.generate_map import (
    add_school_markers_to_map,
    aggregate_filtered_class_data,
    build_legacy_threshold_display_table,
    build_offer_2026_display_table,
    find_school_by_map_point,
    format_ranking_history_for_display,
    get_default_year,
    get_subjects_from_dataframe,
    select_school_classes_for_year,
)


def test_get_default_year_prefers_official_offer_year(monkeypatch):
    metadata = pd.DataFrame(
        {
            "year": [2025, 2026],
            "data_status": ["full", "official_offer"],
        }
    )
    monkeypatch.setattr(pd, "read_excel", lambda *args, **kwargs: metadata)

    assert get_default_year(Path("ignored.xlsx"), [2026, 2025]) == 2026


def test_get_default_year_keeps_full_year_over_planned_offer(monkeypatch):
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


def test_select_school_classes_for_year_uses_school_identifier_and_year():
    classes = pd.DataFrame(
        {
            "SzkolaIdentyfikator": ["lo_1", "lo_1", "lo_2"],
            "OddzialNazwa": ["1A 2025", "1A 2026", "1B 2025"],
            "year": [2025, 2026, 2025],
        }
    )

    result = select_school_classes_for_year(classes, "lo_1", 2025)

    assert result["OddzialNazwa"].tolist() == ["1A 2025"]


def test_school_detail_offer_table_has_user_labels_and_no_raw_missing_values():
    classes = pd.DataFrame(
        {
            "OddzialNazwa": ["1A", "1B"],
            "PrzedmiotyRozszerzone": ["matematyka, geografia", None],
            "Zawod": [None, "technik informatyk"],
            "JezykiObce": ["angielski, niemiecki", None],
            "LiczbaMiejsc": [15.0, None],
            "Prog_min_klasa": [169.15, None],
            "ProgUsedLevel": [
                "klasowy 2025 - przybliżony",
                "szkolny 2025 - brak dopasowania klasy",
            ],
        }
    )

    result = build_offer_2026_display_table(classes)

    assert result.columns.tolist() == [
        "Klasa",
        "Rozszerzenia / zawód",
        "Języki",
        "Miejsca",
        "Próg ref. 2025",
        "Pewność",
    ]
    assert "None" not in result.to_string()
    assert "nan" not in result.to_string().lower()
    assert result.loc[0, "Próg ref. 2025"] == "169.15"
    assert result.loc[0, "Pewność"] == "klasowy, przybliżony"
    assert result.loc[1, "Rozszerzenia / zawód"] == "technik informatyk"


def test_school_detail_legacy_table_has_2025_threshold_label_and_no_raw_missing_values():
    classes = pd.DataFrame(
        {
            "OddzialNazwa": ["1A [O] mat-geo", "1B [O] mat-fiz"],
            "PrzedmiotyRozszerzone": ["matematyka geografia", None],
            "JezykiObce": ["1: angielski 2: niemiecki", None],
            "Prog_min_klasa": [160.0, None],
        }
    )

    result = build_legacy_threshold_display_table(classes)

    assert result.columns.tolist() == [
        "Klasa 2025",
        "Rozszerzenia",
        "Języki",
        "Próg 2025",
    ]
    assert "None" not in result.to_string()
    assert "nan" not in result.to_string().lower()
    assert result.loc[0, "Próg 2025"] == "160"


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
            "threshold_year": [2025, 2025],
        }
    )
    schools = pd.DataFrame({"SzkolaIdentyfikator": ["lo_1"]})

    _, _, details, summary = aggregate_filtered_class_data(classes, schools, True)

    assert summary["lo_1"]["RankingPoz"] == 8
    assert summary["lo_1"]["RankingRok"] == 2026
    assert details["lo_1"][0]["threshold_year"] == 2025


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


def test_popup_class_threshold_includes_year():
    df = pd.DataFrame([_SCHOOL_ROW])
    m = folium.Map(location=[52.23, 21.01], zoom_start=11)
    add_school_markers_to_map(
        folium_map_object=m,
        df_schools_to_display=df,
        class_count_per_school={"lo_1": 1},
        filtered_class_details_per_school={
            "lo_1": [
                {
                    "nazwa": "1A - mat, geo, ang",
                    "url": None,
                    "min_pkt_klasy": 169.15,
                    "threshold_year": 2025,
                }
            ]
        },
        school_summary_from_filtered={},
    )

    assert "(2025: 169.15)" in m.get_root().render()


def test_find_school_by_map_point_returns_source_school_id():
    schools = pd.DataFrame(
        [
            {
                "SzkolaIdentyfikator": "legacy_1",
                "source_school_id": "pzo:123",
                "SzkolaLat": 52.23,
                "SzkolaLon": 21.01,
            },
            {
                "SzkolaIdentyfikator": "legacy_2",
                "source_school_id": "pzo:456",
                "SzkolaLat": 52.30,
                "SzkolaLon": 21.10,
            },
        ]
    )

    assert (
        find_school_by_map_point(schools, {"lat": 52.23001, "lng": 21.01001})
        == "pzo:123"
    )


def test_find_school_by_map_point_ignores_plain_map_click_far_from_marker():
    schools = pd.DataFrame(
        [
            {
                "SzkolaIdentyfikator": "legacy_1",
                "SzkolaLat": 52.23,
                "SzkolaLon": 21.01,
            }
        ]
    )

    assert find_school_by_map_point(schools, {"lat": 52.0, "lng": 20.0}) is None


def test_find_school_by_map_point_falls_back_to_school_identifier():
    schools = pd.DataFrame(
        [
            {
                "SzkolaIdentyfikator": "legacy_1",
                "SzkolaLat": 52.23,
                "SzkolaLon": 21.01,
            }
        ]
    )

    assert find_school_by_map_point(schools, (52.23, 21.01)) == "legacy_1"
