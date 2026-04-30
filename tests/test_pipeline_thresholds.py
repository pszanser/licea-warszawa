from pathlib import Path
import shutil
import uuid

import pandas as pd

from scripts.pipeline import (
    add_common_class_columns,
    add_year_metadata,
    add_threshold_usage_labels,
    attach_stable_school_ids,
    apply_threshold_matches,
    apply_latest_rankings,
    best_thresholds_for_keys,
    historical_school_thresholds,
    load_pzo_offer_tables,
    load_thresholds,
    match_reference_thresholds,
    merge_existing_year_sheets,
    parse_pointed_subjects,
    school_threshold_summary,
    school_ranking_summary,
    summarize_criteria,
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


def test_load_pzo_offer_tables_downloads_missing_raw_snapshot(monkeypatch):
    raw_dir = Path.cwd() / f".missing_pzo_unit_test_{uuid.uuid4().hex}"
    calls = {}
    snapshot = {
        "manifest": {"school_count": 1},
        "search_metadata": {},
        "search_results": {},
        "school_details": {},
    }

    class FakeClient:
        def __init__(self, **kwargs):
            calls["client_kwargs"] = kwargs

    def fake_fetch_offer_snapshot(**kwargs):
        calls["fetch_kwargs"] = kwargs
        return snapshot

    def fake_write_snapshot_files(received_snapshot, received_raw_dir):
        calls["write_snapshot"] = received_snapshot
        calls["raw_dir"] = received_raw_dir

    def fake_build_tables(received_snapshot):
        calls["build_snapshot"] = received_snapshot
        return {"schools": pd.DataFrame({"source_school_id": ["pzo:1"]})}

    monkeypatch.setattr("scripts.pipeline.PzoOmikronClient", FakeClient)
    monkeypatch.setattr(
        "scripts.pipeline.fetch_offer_snapshot", fake_fetch_offer_snapshot
    )
    monkeypatch.setattr(
        "scripts.pipeline.write_snapshot_files", fake_write_snapshot_files
    )
    monkeypatch.setattr("scripts.pipeline.build_pzo_tables", fake_build_tables)

    try:
        result = load_pzo_offer_tables(
            {
                "year": 2026,
                "school_year": "2026/2027",
                "offer": {
                    "path": str(raw_dir),
                    "base_url": "https://example.test",
                    "public_context": "/omikron-public",
                    "school_type_ids": [4],
                    "timeout": 15,
                },
            }
        )
    finally:
        shutil.rmtree(raw_dir, ignore_errors=True)

    assert calls["raw_dir"] == raw_dir
    assert calls["write_snapshot"] is snapshot
    assert calls["build_snapshot"] is snapshot
    assert calls["client_kwargs"]["base_url"] == "https://example.test"
    assert calls["client_kwargs"]["timeout"] == 15
    assert calls["fetch_kwargs"]["year"] == 2026
    assert calls["fetch_kwargs"]["school_type_ids"] == [4]
    assert result["schools"]["source_school_id"].tolist() == ["pzo:1"]


def test_attach_stable_school_ids_adds_score_column_without_reference_schools():
    schools = pd.DataFrame(
        {
            "source_school_id": ["pzo:1"],
            "NazwaSzkoly": ["Liceum Testowe"],
        }
    )
    classes = pd.DataFrame(
        {
            "source_school_id": ["pzo:1"],
            "OddzialNazwa": ["1A"],
        }
    )

    result_schools, result_classes = attach_stable_school_ids(
        schools, classes, pd.DataFrame()
    )

    assert "PzoSchoolMatchScore" in result_schools.columns
    assert pd.isna(result_schools.iloc[0]["PzoSchoolMatchScore"])
    assert pd.isna(result_classes.iloc[0]["PzoSchoolMatchScore"])
    assert result_classes.iloc[0]["PzoSchoolMatchStatus"] == "fallback_name"


def test_add_year_metadata_preserves_row_threshold_labels():
    df = pd.DataFrame({"threshold_label": ["fallback: progi 2024", ""]})

    add_year_metadata(
        df,
        {
            "year": 2026,
            "admission_year": 2026,
            "school_year": "2026/2027",
            "data_status": "official_offer",
            "status_label": "oficjalna oferta 2026/2027",
        },
        {
            "threshold_mode": "reference",
            "threshold_label": "progi referencyjne 2025",
            "threshold_years": "2025/2024",
        },
    )

    assert df["threshold_label"].tolist() == [
        "fallback: progi 2024",
        "progi referencyjne 2025",
    ]


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


def test_add_common_class_columns_preserves_existing_class_type():
    classes = pd.DataFrame(
        {
            "OddzialNazwa": ["plan O", "1A [D] mat-fiz"],
            "TypOddzialu": ["O", pd.NA],
            "PrzedmiotyRozszerzone": ["", "matematyka, fizyka"],
        }
    )

    result = add_common_class_columns(classes)

    assert result["TypOddzialu"].tolist() == ["O", "D"]


def test_load_thresholds_without_sources_returns_merge_schema():
    result = load_thresholds({"year": 2027, "admission_year": 2027})

    assert result.empty
    assert {
        "OddzialNazwa",
        "Prog_min_klasa",
        "SzkolaIdentyfikator",
        "threshold_year",
        "threshold_kind",
        "threshold_label",
    }.issubset(result.columns)


def test_match_reference_thresholds_marks_exact_match_as_trusted():
    classes = pd.DataFrame(
        {
            "source_school_id": ["pzo:1"],
            "source_class_id": ["pzo:101"],
            "SzkolaIdentyfikator": ["lo_1"],
            "OddzialNazwa": ["1A - (O) - mat, fiz (ang - niem)"],
            "OddzialKod": ["1A"],
            "TypOddzialu": ["ogólnodostępny"],
            "PrzedmiotyRozszerzone": ["matematyka, fizyka"],
            "PierwszyJezykObcy": ["język angielski"],
            "DrugiJezykObcy": ["język niemiecki"],
        }
    )
    thresholds = pd.DataFrame(
        {
            "SzkolaIdentyfikator": ["lo_1"],
            "OddzialNazwa": ["1A [O] mat-fiz (ang-niem)"],
            "SymbolOddzialu": ["1A"],
            "Prog_min_klasa": [150.5],
            "threshold_year": [2025],
            "threshold_kind": ["reference"],
            "threshold_priority": [1],
            "threshold_label": ["progi referencyjne 2025"],
        }
    )

    matches, selected = match_reference_thresholds(classes, thresholds)
    classes_with_thresholds = apply_threshold_matches(classes, matches)
    classes_with_thresholds["Prog_min_szkola"] = 140
    classes_with_thresholds = add_threshold_usage_labels(classes_with_thresholds)

    assert selected.iloc[0]["match_status"] == "trusted"
    assert classes_with_thresholds.iloc[0]["Prog_min_klasa"] == 150.5
    assert classes_with_thresholds.iloc[0]["ProgUsedLevel"] == (
        "klasowy 2025 - dokładny"
    )


def test_match_reference_thresholds_uses_best_priority_per_school():
    classes = pd.DataFrame(
        {
            "source_school_id": ["pzo:1", "pzo:2"],
            "source_class_id": ["pzo:101", "pzo:201"],
            "SzkolaIdentyfikator": ["lo_1", "lo_2"],
            "OddzialNazwa": [
                "1A - (O) - mat, fiz (ang - niem)",
                "1A - (O) - mat, geo (ang - niem)",
            ],
            "OddzialKod": ["1A", "1A"],
            "TypOddzialu": ["ogólnodostępny", "ogólnodostępny"],
            "PrzedmiotyRozszerzone": ["matematyka, fizyka", "matematyka, geografia"],
            "PierwszyJezykObcy": ["język angielski", "język angielski"],
            "DrugiJezykObcy": ["język niemiecki", "język niemiecki"],
        }
    )
    thresholds = pd.DataFrame(
        {
            "SzkolaIdentyfikator": ["lo_1", "lo_2"],
            "OddzialNazwa": [
                "1A [O] mat-fiz (ang-niem)",
                "1A [O] mat-geo (ang-niem)",
            ],
            "SymbolOddzialu": ["1A", "1A"],
            "Prog_min_klasa": [150, 140],
            "threshold_year": [2025, 2024],
            "threshold_kind": ["reference", "reference_fallback"],
            "threshold_priority": [1, 2],
            "threshold_label": ["progi referencyjne 2025", "fallback: progi 2024"],
        }
    )

    _matches, selected = match_reference_thresholds(classes, thresholds)

    assert set(selected["source_class_id"]) == {"pzo:101", "pzo:201"}
    lo_2 = selected[selected["source_class_id"].eq("pzo:201")].iloc[0]
    assert lo_2["threshold_year"] == 2024
    assert lo_2["threshold_label"] == "fallback: progi 2024"


def test_add_threshold_usage_labels_uses_actual_threshold_years():
    classes = pd.DataFrame(
        {
            "ProgMatchStatus": ["trusted", "approximate", "school_only"],
            "Prog_min_klasa": [150, 140, pd.NA],
            "Prog_min_szkola": [130, 130, 120],
            "threshold_year": [2024, 2025, pd.NA],
            "Prog_szkola_threshold_year": [2024, 2025, 2024],
        }
    )

    result = add_threshold_usage_labels(classes)

    assert result["ProgUsedLevel"].tolist() == [
        "klasowy 2024 - dokładny",
        "klasowy 2025 - przybliżony",
        "szkolny 2024 - brak dopasowania klasy",
    ]


def test_match_reference_thresholds_marks_weaker_but_coded_match_as_approximate():
    classes = pd.DataFrame(
        {
            "source_school_id": ["pzo:1"],
            "source_class_id": ["pzo:102"],
            "SzkolaIdentyfikator": ["lo_1"],
            "OddzialNazwa": ["1B1 - (O) - mat, fiz, ang (ang - niem)"],
            "OddzialKod": ["1B1"],
            "TypOddzialu": ["ogólnodostępny"],
            "PrzedmiotyRozszerzone": ["matematyka, fizyka, język angielski"],
            "PierwszyJezykObcy": ["język angielski"],
            "DrugiJezykObcy": ["język niemiecki"],
        }
    )
    thresholds = pd.DataFrame(
        {
            "SzkolaIdentyfikator": ["lo_1"],
            "OddzialNazwa": ["1B [O] mat-fiz (ang-niem)"],
            "SymbolOddzialu": ["1B"],
            "Prog_min_klasa": [148],
            "threshold_year": [2025],
            "threshold_kind": ["reference"],
            "threshold_priority": [1],
            "threshold_label": ["progi referencyjne 2025"],
        }
    )

    matches, selected = match_reference_thresholds(classes, thresholds)

    assert selected.iloc[0]["match_status"] == "approximate"
    assert bool(matches.iloc[0]["used_for_scoring"]) is True


def test_match_reference_thresholds_keeps_uncertain_tie_as_candidate_only():
    classes = pd.DataFrame(
        {
            "source_school_id": ["pzo:1"],
            "source_class_id": ["pzo:103"],
            "SzkolaIdentyfikator": ["lo_1"],
            "OddzialNazwa": ["1X - (O) - mat, fiz (ang - niem)"],
            "OddzialKod": ["1X"],
            "TypOddzialu": ["ogólnodostępny"],
            "PrzedmiotyRozszerzone": ["matematyka, fizyka"],
            "PierwszyJezykObcy": ["język angielski"],
            "DrugiJezykObcy": ["język niemiecki"],
        }
    )
    thresholds = pd.DataFrame(
        {
            "SzkolaIdentyfikator": ["lo_1", "lo_1"],
            "OddzialNazwa": [
                "1A [O] mat-fiz (ang-niem)",
                "1B [O] mat-fiz (ang-niem)",
            ],
            "SymbolOddzialu": ["1A", "1B"],
            "Prog_min_klasa": [150, 151],
            "threshold_year": [2025, 2025],
            "threshold_kind": ["reference", "reference"],
            "threshold_priority": [1, 1],
            "threshold_label": ["progi referencyjne 2025", "progi referencyjne 2025"],
        }
    )

    matches, selected = match_reference_thresholds(classes, thresholds)

    assert selected.empty
    assert set(matches["match_status"]) == {"candidate_only"}


def test_match_reference_thresholds_prefers_profile_over_reused_code():
    classes = pd.DataFrame(
        {
            "source_school_id": ["pzo:1"],
            "source_class_id": ["pzo:104"],
            "SzkolaIdentyfikator": ["lo_1"],
            "OddzialNazwa": ["1E1 - (O) - mat, geo, ang (ang - niem)"],
            "OddzialKod": ["1E1"],
            "TypOddzialu": ["ogólnodostępny"],
            "PrzedmiotyRozszerzone": ["matematyka, geografia, język angielski"],
            "PierwszyJezykObcy": ["język angielski"],
            "DrugiJezykObcy": ["język niemiecki"],
        }
    )
    thresholds = pd.DataFrame(
        {
            "SzkolaIdentyfikator": ["lo_1", "lo_1"],
            "OddzialNazwa": [
                "1E1 [O] biol-chem-mat (ang-niem)",
                "1C1 [O] geogr-ang-mat (ang-niem)",
            ],
            "SymbolOddzialu": ["1E1", "1C1"],
            "Prog_min_klasa": [167.95, 169.15],
            "threshold_year": [2025, 2025],
            "threshold_kind": ["reference", "reference"],
            "threshold_priority": [1, 1],
            "threshold_label": ["progi referencyjne 2025", "progi referencyjne 2025"],
        }
    )

    matches, selected = match_reference_thresholds(classes, thresholds)

    assert selected.iloc[0]["OldOddzialNazwa"] == "1C1 [O] geogr-ang-mat (ang-niem)"
    assert selected.iloc[0]["Prog_min_klasa"] == 169.15
    assert selected.iloc[0]["match_status"] == "approximate"
    first_two = matches.sort_values("candidate_rank").head(2)
    assert first_two.iloc[0]["match_method"].startswith("profile_exact")


def test_match_reference_thresholds_allows_same_profile_with_different_second_language():
    classes = pd.DataFrame(
        {
            "source_school_id": ["pzo:1"],
            "source_class_id": ["pzo:105"],
            "SzkolaIdentyfikator": ["lo_1"],
            "OddzialNazwa": ["1B2 - (O) - mat, fiz, ang (ang - hisz)"],
            "OddzialKod": ["1B2"],
            "TypOddzialu": ["ogólnodostępny"],
            "PrzedmiotyRozszerzone": ["matematyka, fizyka, język angielski"],
            "PierwszyJezykObcy": ["język angielski"],
            "DrugiJezykObcy": ["język hiszpański"],
        }
    )
    thresholds = pd.DataFrame(
        {
            "SzkolaIdentyfikator": ["lo_1", "lo_1"],
            "OddzialNazwa": [
                "1B1 [O] fiz-ang-mat (ang-niem)",
                "1B2 [O] fiz-inf-mat (ang-niem)",
            ],
            "SymbolOddzialu": ["1B1", "1B2"],
            "Prog_min_klasa": [169.75, 167.65],
            "threshold_year": [2025, 2025],
            "threshold_kind": ["reference", "reference"],
            "threshold_priority": [1, 1],
            "threshold_label": ["progi referencyjne 2025", "progi referencyjne 2025"],
        }
    )

    matches, selected = match_reference_thresholds(classes, thresholds)

    assert selected.iloc[0]["OldOddzialNazwa"] == "1B1 [O] fiz-ang-mat (ang-niem)"
    assert selected.iloc[0]["match_status"] == "approximate"
    assert bool(matches.sort_values("candidate_rank").iloc[0]["used_for_scoring"])


def test_parse_and_summarize_pzo_criteria_subjects():
    parsed = parse_pointed_subjects(
        "Pierwszy punktowany przedmiot: język polski "
        "Drugi punktowany przedmiot: matematyka "
        "Trzeci punktowany przedmiot : fizyka "
        "Czwarty punktowany przedmiot: język angielski"
    )
    assert parsed == {
        "Punktowany1": "język polski",
        "Punktowany2": "matematyka",
        "Punktowany3": "fizyka",
        "Punktowany4": "język angielski",
    }

    criteria = pd.DataFrame(
        {
            "source_class_id": ["pzo:1", "pzo:1"],
            "group_header_text": [
                "Pierwszy punktowany przedmiot: język polski Drugi punktowany przedmiot: matematyka",
                "",
            ],
            "display_value_text": [
                "Trzeci punktowany przedmiot : fizyka",
                "Czwarty punktowany przedmiot : język angielski",
            ],
        }
    )
    result = summarize_criteria(criteria)

    assert result.iloc[0]["PrzedmiotyPunktowane"] == (
        "język polski, matematyka, fizyka, język angielski"
    )


def test_merge_existing_year_sheets_preserves_other_years_and_year_rank():
    existing_sheets = {
        "schools": pd.DataFrame(
            {
                "SzkolaIdentyfikator": ["lo_1"],
                "year": [2025],
                "RankingPoz": [4],
                "RankingPozRokuDanych": [8],
            }
        ),
        "metadata": pd.DataFrame({"year": [2025], "data_status": ["full"]}),
    }
    new_sheets = {
        "schools": pd.DataFrame(
            {
                "SzkolaIdentyfikator": ["lo_2"],
                "year": [2026],
                "RankingPoz": [20],
            }
        ),
        "metadata": pd.DataFrame({"year": [2026], "data_status": ["planned_offer"]}),
    }

    result = merge_existing_year_sheets(existing_sheets, new_sheets, {2026})

    assert result["metadata"]["year"].tolist() == [2025, 2026]
    schools = result["schools"].sort_values("year").reset_index(drop=True)
    assert schools["year"].tolist() == [2025, 2026]
    assert schools.loc[0, "RankingPoz"] == 8
    assert "RankingPozRokuDanych" not in schools.columns
