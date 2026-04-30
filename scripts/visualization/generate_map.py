import html
import folium
from folium.plugins import MarkerCluster, Fullscreen, LocateControl, HeatMap
import logging
import math
import os
from pathlib import Path
import pandas as pd
import re
from typing import Callable, Any
from urllib.parse import urlparse

import sys

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.pipeline import extract_class_type

RESULTS_DIR = ROOT / "results"
APP_DATA_FILE = RESULTS_DIR / "app" / "licea_warszawa.xlsx"
DATA_PATTERN = "LO_Warszawa_2025_*.xlsx"
MAP_OUTPUT_FILENAME = "mapa_licea_warszawa.html"
WARSAW_CENTER_COORDS = [52.2297, 21.0122]  # Współrzędne centrum Warszawy


def get_latest_xls_file(directory: Path, pattern: str) -> Path | None:
    """
    Znajduje najnowszy plik Excel w danym katalogu pasujący do wzorca.
    """
    files = list(directory.glob(pattern))
    if not files:
        print(
            f"Nie znaleziono plików pasujących do wzorca '{pattern}' w '{directory}'."
        )
        return None
    latest_file = max(files, key=os.path.getmtime)
    print(f"Używam pliku danych: {latest_file}")
    return latest_file


def get_app_or_latest_xls_file(directory: Path = RESULTS_DIR) -> Path | None:
    """Preferuje stabilny plik aplikacyjny, z fallbackiem na stary jednoroczny Excel."""
    if APP_DATA_FILE.exists():
        print(f"Używam pliku aplikacyjnego: {APP_DATA_FILE}")
        return APP_DATA_FILE
    return get_latest_xls_file(directory, DATA_PATTERN)


def _sheet_name(excel_path: Path, new_name: str, legacy_name: str) -> str:
    xls = pd.ExcelFile(excel_path)
    return new_name if new_name in xls.sheet_names else legacy_name


def get_available_years(excel_path: Path) -> list[int]:
    """Zwraca lata dostępne w pliku aplikacji lub [2025] dla legacy Excela."""
    try:
        sheet = _sheet_name(excel_path, "metadata", "info")
        if sheet == "metadata":
            metadata = pd.read_excel(excel_path, sheet_name=sheet)
            return sorted(
                [int(year) for year in metadata["year"].dropna().unique()],
                reverse=True,
            )
        schools_sheet = _sheet_name(excel_path, "schools", "szkoly")
        schools = pd.read_excel(excel_path, sheet_name=schools_sheet, nrows=10)
        if "year" in schools.columns:
            return sorted(
                [int(year) for year in schools["year"].dropna().unique()],
                reverse=True,
            )
    except Exception:
        pass
    return [2025]


def get_default_year(excel_path: Path, available_years: list[int] | None = None) -> int:
    """Zwraca domyślny rok aplikacji z preferencją dla oficjalnej oferty."""
    years = available_years or get_available_years(excel_path)
    if not years:
        return 2025

    try:
        metadata = pd.read_excel(excel_path, sheet_name="metadata")
        if {"year", "data_status"}.issubset(metadata.columns):
            preferred_statuses = ["official_offer", "full"]
            for status in preferred_statuses:
                preferred_years = metadata[metadata["data_status"].eq(status)][
                    "year"
                ].dropna()
                preferred_years = [int(year) for year in preferred_years.unique()]
                preferred_years = [year for year in preferred_years if year in years]
                if preferred_years:
                    return max(preferred_years)
    except Exception as exc:
        logger.exception(
            "Nie udało się odczytać arkusza metadata z %s; "
            "używam domyślnego roku z listy %s. Błąd: %s",
            excel_path,
            years,
            exc,
        )

    return max(years)


def _coerce_map_point(point: Any) -> tuple[float, float] | None:
    """Normalizuje punkt kliknięcia zwracany przez streamlit-folium."""
    if point is None:
        return None
    if isinstance(point, dict):
        lat = point.get("lat")
        lon = point.get("lng", point.get("lon"))
    elif isinstance(point, (tuple, list)) and len(point) >= 2:
        lat = point[0]
        lon = point[1]
    else:
        return None
    if lat is None or lon is None:
        return None
    try:
        return float(lat), float(lon)
    except (TypeError, ValueError):
        return None


def _row_school_id(row: pd.Series) -> str | None:
    for id_col in ["source_school_id", "SzkolaIdentyfikator"]:
        if id_col not in row.index:
            continue
        value = row.get(id_col)
        if pd.notna(value) and str(value).strip():
            return str(value)
    return None


def _find_school_id_in_rows(df_schools: pd.DataFrame, school_id: str) -> str | None:
    for id_col in ["source_school_id", "SzkolaIdentyfikator"]:
        if id_col not in df_schools.columns:
            continue
        matches = df_schools[df_schools[id_col].astype(str).eq(str(school_id))]
        if not matches.empty:
            return str(matches.iloc[0][id_col])
    return None


def _school_id_from_popup(popup_html: Any) -> str | None:
    if popup_html is None:
        return None
    match = re.search(
        r"data-source-school-id=[\"']([^\"']+)[\"']",
        str(popup_html),
    )
    return html.unescape(match.group(1)) if match else None


def _normalize_map_text(value: Any) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _safe_popup_href(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    parsed = urlparse(text)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return html.escape(text, quote=True)


def _safe_popup_text(value: Any, fallback: str = "") -> str:
    try:
        if pd.isna(value):
            return fallback
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none"}:
        return fallback
    return html.escape(text, quote=False)


def _safe_map_coordinate(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _format_map_coordinate(value: float) -> str:
    return str(float(value))


def _threshold_year_prefix(value: Any) -> str:
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    try:
        year = int(float(value))
    except (TypeError, ValueError):
        return ""
    return f"{year}: "


def _school_id_from_tooltip(
    df_schools: pd.DataFrame, tooltip: Any, candidate_indices: pd.Index
) -> str | None:
    tooltip_text = _normalize_map_text(tooltip)
    if not tooltip_text:
        return None
    candidates = df_schools.loc[candidate_indices]
    for _, row in candidates.iterrows():
        district = row.get("Dzielnica")
        names = [
            _normalize_map_text(row.get("NazwaSzkoly")),
            _normalize_map_text(f"{row.get('NazwaSzkoly')} ({district})"),
        ]
        if tooltip_text in names:
            return _row_school_id(row)
    return None


def find_school_by_map_point(
    df_schools: pd.DataFrame,
    point: Any,
    tooltip: Any = None,
    popup: Any = None,
    max_distance_degrees: float = 0.0008,
) -> str | None:
    """Zwraca identyfikator szkoły najbliższej klikniętemu znacznikowi mapy."""
    if df_schools.empty or {"SzkolaLat", "SzkolaLon"}.difference(df_schools.columns):
        return None

    lat_lon = _coerce_map_point(point)
    if lat_lon is None:
        return None
    lat, lon = lat_lon

    school_lat = pd.to_numeric(df_schools["SzkolaLat"], errors="coerce")
    school_lon = pd.to_numeric(df_schools["SzkolaLon"], errors="coerce")
    distance_sq = (school_lat - lat) ** 2 + (school_lon - lon) ** 2
    distance_sq = distance_sq.dropna()
    if distance_sq.empty:
        return None

    nearby_indices = distance_sq[distance_sq.le(max_distance_degrees**2)].index
    if nearby_indices.empty:
        return None

    popup_school_id = _school_id_from_popup(popup)
    if popup_school_id:
        matched_id = _find_school_id_in_rows(
            df_schools.loc[nearby_indices], popup_school_id
        )
        if matched_id:
            return matched_id

    tooltip_school_id = _school_id_from_tooltip(df_schools, tooltip, nearby_indices)
    if tooltip_school_id:
        return tooltip_school_id

    closest_idx = distance_sq.idxmin()
    return _row_school_id(df_schools.loc[closest_idx])


def display_cell(value: Any, fallback: str = "—") -> str:
    """Czytelny zapis wartości w tabelach użytkowych."""
    if value is None:
        return fallback
    try:
        if pd.isna(value):
            return fallback
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    return text if text and text.lower() not in {"nan", "none"} else fallback


def format_points_display(value: Any) -> str:
    """Formatuje próg punktowy bez technicznych zer."""
    try:
        if pd.isna(value):
            return "—"
        number = float(value)
    except (TypeError, ValueError):
        return "—"
    return str(int(number)) if number.is_integer() else f"{number:.2f}".rstrip("0")


def threshold_certainty_display(value: Any) -> str:
    """Skraca techniczne etykiety progów do tekstu dla rodzica i ucznia."""
    text = display_cell(value, "")
    mapping = {
        "klasowy 2025 - dokładny": "klasowy, dokładny",
        "klasowy 2025 - przybliżony": "klasowy, przybliżony",
        "szkolny 2025 - brak dopasowania klasy": "szkolny, brak klasy",
        "brak progu": "brak danych",
    }
    return mapping.get(text, text or "—")


def profile_or_job_display(row: pd.Series) -> str:
    """Łączy profil ogólny i zawód w jedną kolumnę tabeli oferty."""
    profile = display_cell(row.get("PrzedmiotyRozszerzone"), "")
    job = display_cell(row.get("Zawod"), "")
    if profile and job:
        return f"{profile} | zawód: {job}"
    return profile or job or "—"


def select_school_classes_for_year(
    df_classes: pd.DataFrame,
    school_identifier: Any,
    year: int,
) -> pd.DataFrame:
    """Wybiera wszystkie klasy danej szkoły z konkretnego roku danych."""
    if df_classes.empty:
        return df_classes.iloc[0:0].copy()
    id_columns = [
        column
        for column in ["SzkolaIdentyfikator", "source_school_id"]
        if column in df_classes.columns
    ]
    if not id_columns:
        return df_classes.iloc[0:0].copy()

    identifier = str(school_identifier)
    mask = pd.Series(False, index=df_classes.index)
    for column in id_columns:
        mask = mask | df_classes[column].astype(str).eq(identifier)
    result = df_classes[mask]
    if "year" in result.columns:
        result = result[pd.to_numeric(result["year"], errors="coerce").eq(year)]
    return result.copy()


def threshold_range_display(df_classes: pd.DataFrame) -> str:
    """Zwraca zakres progów klasowych w czytelnym formacie."""
    if df_classes.empty or "Prog_min_klasa" not in df_classes.columns:
        return "—"
    values = pd.to_numeric(df_classes["Prog_min_klasa"], errors="coerce").dropna()
    if values.empty:
        return "—"
    min_value = format_points_display(values.min())
    max_value = format_points_display(values.max())
    return min_value if min_value == max_value else f"{min_value}-{max_value}"


def build_offer_2026_display_table(df_classes: pd.DataFrame) -> pd.DataFrame:
    """Buduje tabelę aktualnej oferty 2026 do panelu szkoły."""
    columns = [
        "Klasa",
        "Rozszerzenia / zawód",
        "Języki",
        "Miejsca",
        "Próg ref. 2025",
        "Pewność",
    ]
    if df_classes.empty:
        return pd.DataFrame(columns=columns)

    classes = df_classes.copy()
    if "Prog_min_klasa" in classes.columns:
        classes["_sort_threshold"] = pd.to_numeric(
            classes["Prog_min_klasa"], errors="coerce"
        )
    else:
        classes["_sort_threshold"] = pd.NA
    classes = classes.sort_values(
        ["_sort_threshold", "OddzialNazwa"],
        ascending=[False, True],
        na_position="last",
    )

    rows = []
    for _, row in classes.iterrows():
        rows.append(
            {
                "Klasa": display_cell(row.get("OddzialNazwa")),
                "Rozszerzenia / zawód": profile_or_job_display(row),
                "Języki": display_cell(row.get("JezykiObce")),
                "Miejsca": format_points_display(row.get("LiczbaMiejsc")),
                "Próg ref. 2025": format_points_display(row.get("Prog_min_klasa")),
                "Pewność": threshold_certainty_display(row.get("ProgUsedLevel")),
            }
        )
    return pd.DataFrame(rows, columns=columns)


def build_legacy_threshold_display_table(df_classes: pd.DataFrame) -> pd.DataFrame:
    """Buduje tabelę wszystkich klas 2025 z progami dla wybranej szkoły."""
    columns = ["Klasa 2025", "Rozszerzenia", "Języki", "Próg 2025"]
    if df_classes.empty:
        return pd.DataFrame(columns=columns)

    classes = df_classes.copy()
    if "Prog_min_klasa" in classes.columns:
        classes["_sort_threshold"] = pd.to_numeric(
            classes["Prog_min_klasa"], errors="coerce"
        )
    else:
        classes["_sort_threshold"] = pd.NA
    classes = classes.sort_values(
        ["_sort_threshold", "OddzialNazwa"],
        ascending=[False, True],
        na_position="last",
    )

    rows = []
    for _, row in classes.iterrows():
        rows.append(
            {
                "Klasa 2025": display_cell(row.get("OddzialNazwa")),
                "Rozszerzenia": display_cell(row.get("PrzedmiotyRozszerzone")),
                "Języki": display_cell(row.get("JezykiObce")),
                "Próg 2025": format_points_display(row.get("Prog_min_klasa")),
            }
        )
    return pd.DataFrame(rows, columns=columns)


def load_metadata(excel_path: Path, year: int | None = None) -> pd.DataFrame:
    try:
        metadata = pd.read_excel(excel_path, sheet_name="metadata")
    except Exception:
        return pd.DataFrame()
    if year is not None and "year" in metadata.columns:
        metadata = metadata[metadata["year"] == year]
    return metadata


def load_quality(excel_path: Path, year: int | None = None) -> pd.DataFrame:
    try:
        quality = pd.read_excel(excel_path, sheet_name="quality")
    except Exception:
        return pd.DataFrame()
    if year is not None and "year" in quality.columns:
        quality = quality[quality["year"] == year]
    return quality


def load_school_data(excel_path: Path, year: int | None = None) -> pd.DataFrame | None:
    """
    Wczytuje dane szkół z arkusza 'szkoly' w podanym pliku Excel.
    Filtruje szkoły bez współrzędnych i sprawdza obecność wymaganych kolumn.
    """
    try:
        sheet = _sheet_name(excel_path, "schools", "szkoly")
        df = pd.read_excel(excel_path, sheet_name=sheet)
        if year is not None and "year" in df.columns:
            df = df[df["year"] == year].copy()

        required_cols = [
            "SzkolaLat",
            "SzkolaLon",
            "NazwaSzkoly",
            "AdresSzkoly",
            "Dzielnica",
            "url",
        ]

        for col in required_cols:
            if col not in df.columns:
                print(
                    f"Brak wymaganej kolumny '{col}' w arkuszu 'szkoly'. Nie można wygenerować mapy."
                )
                return None

        df_filtered = df.dropna(subset=["SzkolaLat", "SzkolaLon"]).copy()

        if df_filtered.empty:
            print(
                "Brak szkół z poprawnymi współrzędnymi w pliku. Mapa nie zostanie wygenerowana."
            )
            return None

        return df_filtered

    except FileNotFoundError:
        print(f"Nie znaleziono pliku: {excel_path}")
        return None
    except ValueError as e:
        print(f"Błąd podczas wczytywania arkusza 'szkoly' z pliku Excel: {e}")
        return None
    except Exception as e:
        print(f"Niespodziewany błąd podczas wczytywania danych: {e}")
        return None


def load_classes_data(excel_path: Path, year: int | None = None) -> pd.DataFrame | None:
    """
    Wczytuje dane klas z arkusza 'klasy' w podanym pliku Excel.
    """
    try:
        sheet = _sheet_name(excel_path, "classes", "klasy")
        df = pd.read_excel(excel_path, sheet_name=sheet)
        if year is not None and "year" in df.columns:
            df = df[df["year"] == year].copy()
        if "TypOddzialu" not in df.columns and "OddzialNazwa" in df.columns:
            df["TypOddzialu"] = df["OddzialNazwa"].apply(extract_class_type)
        return df
    except Exception as e:
        print(f"Błąd podczas wczytywania arkusza 'klasy': {e}")
        return None


def format_ranking_history_for_display(history_value: Any) -> str:
    if pd.isna(history_value) or not str(history_value).strip():
        return ""
    parts = []
    for item in str(history_value).split("; "):
        if ": " not in item:
            continue
        year, ranking = item.split(": ", 1)
        ranking = ranking.strip()
        year = year.strip()
        if ranking and year:
            parts.append(f"{ranking} ({year})")
    return ", ".join(parts)


def get_subjects_from_dataframe(df: pd.DataFrame) -> list[str]:
    """Wyciąga listę przedmiotów rozszerzonych z kolumn DataFrame"""
    potential_subjects = [
        col
        for col in df.columns
        if col
        not in [
            "SzkolaIdentyfikator",
            "OddzialIdentyfikator",
            "OddzialNazwa",
            "UrlGrupy",
            "Prog_min_klasa",
            "Prog_min_szkola",
            "Prog_max_szkola",
            "RankingPoz",
            "RankingPozTekst",
            "RankingPozRokuDanych",
            "RankingPozTekstRokuDanych",
            "RankingPozNajnowszy",
            "RankingPozTekstNajnowszy",
            "RankingRok",
            "Ranking_historyczny_szkola",
            "Ranking_lata",
            "TypOddzialu",
            "year",
            "admission_year",
            "school_year",
            "data_status",
            "status_label",
            "threshold_mode",
            "threshold_label",
            "threshold_years",
            "threshold_year",
            "threshold_kind",
            "Prog_szkola_threshold_year",
            "Prog_szkola_threshold_kind",
            "Prog_szkola_threshold_label",
            "Progi_historyczne_szkola",
            "Progi_historyczne_lata",
            "LiczbaOddzialowPlan",
            "LiczbaMiejscPlan",
        ]
    ]
    subject_cols = []
    for col in potential_subjects:
        values = pd.to_numeric(df[col], errors="coerce")
        non_null_values = set(values.dropna().unique())
        if non_null_values.issubset({0, 1}) and values.fillna(0).sum() > 0:
            subject_cols.append(col)
    return sorted(subject_cols)


def apply_filters_to_classes(
    df_classes_raw: pd.DataFrame,
    wanted_subjects: list[str] | None,
    avoided_subjects: list[str] | None,
    max_ranking_poz: int | None,
    min_class_points: float | None,
    max_class_points: float | None,
    allowed_class_types: list[str] | None = None,
    report_warning_callback: Callable[[str], Any] = print,
) -> pd.DataFrame:
    """
    Filtruje DataFrame klas na podstawie podanych kryteriów.
    """
    df_filtered = df_classes_raw.copy()

    if wanted_subjects:
        for subject in wanted_subjects:
            if subject in df_filtered.columns:
                df_filtered = df_filtered[df_filtered[subject] == 1]
            else:
                report_warning_callback(
                    f"Kolumna wymaganego przedmiotu '{subject}' nie znaleziona w danych."
                )

    if avoided_subjects:
        for subject in avoided_subjects:
            if subject in df_filtered.columns:
                df_filtered = df_filtered[df_filtered[subject] != 1]
            else:
                report_warning_callback(
                    f"Kolumna unikanego przedmiotu '{subject}' nie znaleziona w danych."
                )

    if max_ranking_poz is not None:
        if "RankingPoz" in df_filtered.columns:
            df_filtered = df_filtered[df_filtered["RankingPoz"] <= max_ranking_poz]
        else:
            report_warning_callback(
                "Kolumna 'RankingPoz' nie znaleziona w danych do filtrowania rankingu."
            )

    if min_class_points is not None:
        if "Prog_min_szkola" in df_filtered.columns:
            df_filtered = df_filtered[
                df_filtered["Prog_min_szkola"] >= min_class_points
            ]
        else:
            report_warning_callback(
                "Kolumna 'Prog_min_szkola' nie znaleziona w danych do filtrowania progu min."
            )

    if max_class_points is not None:
        if (
            "Prog_min_szkola" in df_filtered.columns
        ):  # Filtrujemy na podstawie progu minimalnego klasy
            df_filtered = df_filtered[
                df_filtered["Prog_min_szkola"] <= max_class_points
            ]
        else:
            report_warning_callback(
                "Kolumna 'Prog_min_szkola' nie znaleziona w danych do filtrowania progu max."
            )

    if allowed_class_types:
        if "TypOddzialu" in df_filtered.columns:
            df_filtered = df_filtered[
                df_filtered["TypOddzialu"].isin(allowed_class_types)
            ]
        else:
            report_warning_callback(
                "Kolumna 'TypOddzialu' nie znaleziona w danych do filtrowania typu oddziału."
            )

    return df_filtered


def aggregate_filtered_class_data(
    df_filtered_classes: pd.DataFrame,
    df_schools_raw: pd.DataFrame,
    any_filters_applied: bool,
) -> tuple[pd.DataFrame, dict, dict, dict]:
    """
    Agreguje dane po filtrowaniu klas, przygotowując dane do wyświetlenia na mapie.
    """
    if df_filtered_classes.empty and any_filters_applied:
        # print("Żadne klasy nie spełniają podanych kryteriów filtrowania.")
        df_schools_to_display = pd.DataFrame(columns=df_schools_raw.columns)
        count_filtered_classes: dict[str, int] = {}
        detailed_filtered_classes_info: dict[str, list[dict[str, object]]] = {}
        school_summary_from_filtered: dict[str, dict[str, object]] = {}
    elif df_filtered_classes.empty:  # No filters applied, but no classes data
        # print("Brak klas w danych wejściowych.")
        df_schools_to_display = pd.DataFrame(columns=df_schools_raw.columns)
        count_filtered_classes = {}
        detailed_filtered_classes_info = {}
        school_summary_from_filtered = {}
    else:
        schools_with_matching_classes_ids = df_filtered_classes[
            "SzkolaIdentyfikator"
        ].unique()
        df_schools_to_display = df_schools_raw[
            df_schools_raw["SzkolaIdentyfikator"].isin(
                schools_with_matching_classes_ids
            )
        ].copy()

        count_filtered_classes = (
            df_filtered_classes.groupby("SzkolaIdentyfikator").size().to_dict()
        )

        detailed_filtered_classes_info = {}
        for szk_id, group in df_filtered_classes.groupby("SzkolaIdentyfikator"):
            details = []
            for _, class_row in group.iterrows():
                details.append(
                    {
                        "nazwa": class_row.get("OddzialNazwa"),
                        "url": class_row.get("UrlGrupy"),
                        "min_pkt_klasy": class_row.get("Prog_min_klasa"),
                        "threshold_year": class_row.get("threshold_year"),
                    }
                )
            detailed_filtered_classes_info[szk_id] = details

        school_summary_from_filtered = {}
        # Ensure all expected columns for aggregation are present
        required_agg_cols = [
            "SzkolaIdentyfikator",
            "Prog_min_szkola",
            "Prog_max_szkola",
            "RankingPoz",
        ]
        if all(col in df_filtered_classes.columns for col in required_agg_cols):
            agg_dict = {
                "Prog_min_szkola": "min",  # Min próg szkoły z pasujących klas
                "Prog_max_szkola": "max",  # Max próg szkoły (faktycznie klasy) z pasujących klas
                "RankingPoz": "first",  # Ranking szkoły (jest taki sam dla wszystkich jej klas)
            }
            if "RankingRok" in df_filtered_classes.columns:
                agg_dict["RankingRok"] = "first"
            # Drop rows where any of the aggregation keys might be NaN before grouping
            # to avoid issues with groupby if these columns are not fully populated
            # However, typically SzkolaIdentyfikator should always be present.
            # For Prog_min_szkola, Prog_max_szkola, RankingPoz, they might be NaN for some classes.
            # The aggregation functions (min, max, first) handle NaNs appropriately by default.

            grouped_for_summary = df_filtered_classes.groupby(
                "SzkolaIdentyfikator"
            ).agg(agg_dict)
            school_summary_from_filtered = grouped_for_summary.to_dict("index")
        else:
            # print("Ostrzeżenie: Brak wszystkich wymaganych kolumn do agregacji podsumowania szkoły z przefiltrowanych klas.")
            # This will result in school_summary_from_filtered remaining empty or partially filled if some columns were present.
            # Fallback can be to use original school data if filtered summary is not possible.
            pass

    return (
        df_schools_to_display,
        count_filtered_classes,
        detailed_filtered_classes_info,
        school_summary_from_filtered,
    )


def add_school_markers_to_map(
    folium_map_object: folium.Map,
    df_schools_to_display: pd.DataFrame,
    class_count_per_school: dict[str, int],
    filtered_class_details_per_school: dict[str, list[dict]],
    school_summary_from_filtered: dict[str, dict],
    origin_lat: float | None = None,
    origin_lon: float | None = None,
    show_details_hint: bool = False,
) -> None:
    """
    Dodaje markery szkół do obiektu mapy Folium.
    Markery są grupowane w klastry (MarkerCluster) dla lepszej czytelności.

    Gdy podane origin_lat/origin_lon, do popupu każdej szkoły dodawany jest
    link „🚌 Sprawdź dojazd z Twojego punktu" prowadzący do Google Maps z trasą
    transit od punktu startowego użytkownika. Nie wymaga klucza API.
    """
    if df_schools_to_display.empty:
        # print("Brak szkół do wyświetlenia na mapie po zastosowaniu filtrów.") # Handled by caller
        return

    cluster = MarkerCluster()
    cluster.add_to(folium_map_object)

    for _, row in df_schools_to_display.iterrows():
        school_lat = _safe_map_coordinate(row.get("SzkolaLat"))
        school_lon = _safe_map_coordinate(row.get("SzkolaLon"))
        if school_lat is None or school_lon is None:
            continue

        school_name = _safe_popup_text(row.get("NazwaSzkoly"))
        district = _safe_popup_text(row.get("Dzielnica"))
        address = _safe_popup_text(row.get("AdresSzkoly"))
        tooltip_text = f"{school_name} ({district})" if district else school_name
        szk_id = row.get("SzkolaIdentyfikator")
        source_school_id = row.get("source_school_id", szk_id)
        destination = (
            f"{_format_map_coordinate(school_lat)},"
            f"{_format_map_coordinate(school_lon)}"
        )

        popup_html = (
            "<span "
            f"data-source-school-id='{html.escape(str(source_school_id), quote=True)}' "
            "style='display:none'></span>"
            f"<b>{school_name}</b><br>"
        )
        nav_url = "https://www.google.com/maps/dir/?api=1&destination=" f"{destination}"
        popup_html += (
            f"Adres: <a href='{nav_url}' target='_blank' "
            f"rel='noopener noreferrer'>{address}</a><br>"
        )
        origin_lat_safe = _safe_map_coordinate(origin_lat)
        origin_lon_safe = _safe_map_coordinate(origin_lon)
        if origin_lat_safe is not None and origin_lon_safe is not None:
            origin = (
                f"{_format_map_coordinate(origin_lat_safe)},"
                f"{_format_map_coordinate(origin_lon_safe)}"
            )
            commute_url = (
                "https://www.google.com/maps/dir/?api=1"
                f"&origin={origin}"
                f"&destination={destination}"
                "&travelmode=transit"
            )
            popup_html += (
                f"<a href='{commute_url}' target='_blank' rel='noopener noreferrer'>"
                "🚌 Sprawdź dojazd z Twojego punktu</a><br>"
            )
        popup_html += f"Dzielnica: {district}<br>"

        summary = school_summary_from_filtered.get(szk_id, {})

        ranking_history = format_ranking_history_for_display(
            row.get("Ranking_historyczny_szkola")
        )
        if ranking_history:
            popup_html += (
                f"Ranking Perspektywy: {_safe_popup_text(ranking_history)}<br>"
            )
        else:
            # Użyj rankingu z podsumowania przefiltrowanych klas, jeśli dostępne, inaczej z danych ogólnych szkoły.
            ranking_year = summary.get(
                "RankingRok", row.get("RankingRok", row.get("year"))
            )
            ranking_poz = summary.get("RankingPoz", row.get("RankingPoz"))
            if pd.notna(ranking_poz):
                display_ranking = (
                    int(ranking_poz) if float(ranking_poz).is_integer() else ranking_poz
                )
                ranking_suffix = (
                    f" {int(ranking_year)}" if pd.notna(ranking_year) else ""
                )
                popup_html += (
                    f"Ranking Perspektywy{ranking_suffix}: "
                    f"{_safe_popup_text(display_ranking)}<br>"
                )

        historical_thresholds = row.get("Progi_historyczne_szkola")
        if pd.notna(historical_thresholds) and str(historical_thresholds).strip():
            history_html = "<br>".join(
                _safe_popup_text(value)
                for value in str(historical_thresholds).split("; ")
                if _safe_popup_text(value)
            )
            popup_html += f"Progi punktowe:<br>{history_html}<br>"
        else:
            min_prog = summary.get("Prog_min_szkola", row.get("Prog_min_szkola"))
            max_prog = summary.get("Prog_max_szkola", row.get("Prog_max_szkola"))
            if pd.notna(min_prog) and pd.notna(max_prog):
                threshold_year = row.get("Prog_szkola_threshold_year")
                year_prefix = _threshold_year_prefix(threshold_year)
                if min_prog == max_prog:
                    threshold_text = _safe_popup_text(
                        f"{year_prefix}{format_points_display(min_prog)}"
                    )
                    popup_html += f"Progi punktowe:<br>{threshold_text}<br>"
                else:
                    threshold_text = _safe_popup_text(
                        f"{year_prefix}{format_points_display(min_prog)}-"
                        f"{format_points_display(max_prog)}"
                    )
                    popup_html += f"Progi punktowe:<br>{threshold_text}<br>"

        num_matching_classes = class_count_per_school.get(szk_id, 0)
        if num_matching_classes > 0:
            popup_html += (
                f"Liczba klas spełniających kryteria: {num_matching_classes}<br>"
            )
        if show_details_hint:
            popup_html += "Szczegóły szkoły i klas są pod mapą.<br>"

        matching_classes_details = filtered_class_details_per_school.get(szk_id, [])
        if matching_classes_details:
            popup_html += "<u>Pasujące klasy:</u><br>"
            for class_detail in matching_classes_details:
                class_name = class_detail.get("nazwa", "N/A")
                class_url = class_detail.get("url")
                class_min_pkt = class_detail.get("min_pkt_klasy")

                line = "- "
                safe_class_url = _safe_popup_href(class_url)
                safe_class_name = _safe_popup_text(class_name, "N/A")
                if safe_class_url:
                    line += (
                        f"<a href='{safe_class_url}' target='_blank' "
                        f"rel='noopener noreferrer'>{safe_class_name}</a>"
                    )
                else:
                    line += safe_class_name

                if class_min_pkt is not None and pd.notna(class_min_pkt):
                    class_min_pkt_float = float(class_min_pkt)
                    formatted_min_pkt = format_points_display(class_min_pkt_float)
                    threshold_year = class_detail.get("threshold_year")
                    threshold_prefix = _threshold_year_prefix(threshold_year)
                    line += f" ({threshold_prefix}{formatted_min_pkt})"
                popup_html += line + "<br>"

        school_url = _safe_popup_href(row.get("url"))
        if school_url:
            popup_html += (
                f"<a href='{school_url}' target='_blank' "
                "rel='noopener noreferrer'>Strona szkoły</a>"
            )

        popup_html = f"<div style='font-size:14px; line-height:1.2;'>{popup_html}</div>"

        school_type = str(row.get("TypSzkoly", "").lower())
        color_map = {"liceum": "blue", "technikum": "green", "branżowa": "red"}
        marker_color = color_map.get(school_type, "blue")

        folium.Marker(
            location=[school_lat, school_lon],
            popup=folium.Popup(popup_html, max_width=350),
            icon=folium.Icon(color=marker_color, icon="graduation-cap", prefix="fa"),
            tooltip=tooltip_text,
        ).add_to(cluster)


def _add_heatmap_toggle(map_obj: folium.Map, heat_layer: HeatMap) -> None:
    """Dodaje prosty przycisk do włączania i wyłączania warstwy HeatMap."""
    button_html = f"""
    <div id='heatmap-btn' style='position: fixed; top: 10px; right: 10px; z-index:9999;'>
        <button onclick="toggleHeatmap()" style='padding:4px 8px;'>Pokaż heatmapę</button>
    </div>
    <script>
    function toggleHeatmap() {{
        var map = {map_obj.get_name()};
        var layer = {heat_layer.get_name()};
        var btn = document.getElementById('heatmap-btn').children[0];
        if (map.hasLayer(layer)) {{
            map.removeLayer(layer);
            btn.innerHTML = 'Pokaż heatmapę';
        }} else {{
            map.addLayer(layer);
            btn.innerHTML = 'Ukryj heatmapę';
        }}
    }}
    </script>
    """
    from folium import Element

    map_obj.get_root().html.add_child(Element(button_html))  # type: ignore[attr-defined]


def create_schools_map(
    df_schools_to_display: pd.DataFrame,
    output_path: Path,
    class_count_per_school: dict[str, int],
    filtered_class_details_per_school: dict[str, list[dict]],
    school_summary_from_filtered: dict[str, dict],
    filters_info_html: str = "",
    show_heatmap: bool = False,
) -> None:
    """
    Tworzy mapę Folium z lokalizacjami szkół i zapisuje ją do pliku HTML.
    Na mapie zastosowano klastrowanie znaczników, dzięki czemu
    wiele bliskich szkół nie nachodzi na siebie przy oddaleniu.
    """
    m = folium.Map(location=WARSAW_CENTER_COORDS, zoom_start=11)
    Fullscreen().add_to(m)
    LocateControl().add_to(m)

    if filters_info_html:
        legend_html = f"""
        <div style="position: fixed; top: 60px; left: 60px; width: 320px; z-index:9999; background-color: white; border:2px solid grey; border-radius:8px; padding: 10px; font-size: 14px; box-shadow: 2px 2px 8px #888;">
            <b>Zastosowane filtry:</b><br>
            {filters_info_html}
        </div>
        """
        from folium import Element

        m.get_root().html.add_child(Element(legend_html))  # type: ignore[attr-defined]

    if df_schools_to_display.empty:
        print("Brak szkół do wyświetlenia na mapie po zastosowaniu filtrów.")
        # Save empty map anyway
    else:
        add_school_markers_to_map(
            m,
            df_schools_to_display,
            class_count_per_school,
            filtered_class_details_per_school,
            school_summary_from_filtered,
        )

    heat_layer = None
    if show_heatmap and not df_schools_to_display.empty:
        heat_data = df_schools_to_display[["SzkolaLat", "SzkolaLon"]].values.tolist()
        heat_layer = HeatMap(heat_data, name="HeatMap", show=False)
        heat_layer.add_to(m)
        _add_heatmap_toggle(m, heat_layer)
    try:
        m.save(str(output_path))
        print(f"Mapa zapisana jako: {output_path}")
    except Exception as e:
        print(f"Błąd podczas zapisywania mapy: {e}")


def main():
    print("Rozpoczynam generowanie mapy szkół...")

    # --- Definicje filtrów (mogą być modyfikowane lub ustawione na None/puste listy) ---
    wanted_subjects = []  # np. ["matematyka"]
    avoided_subjects = []  # np. ["biologia"]
    max_ranking_poz = None  # np. 50
    min_class_points = None  # np. 140.0
    max_class_points = None  # np. 180.0
    enable_heatmap = False
    # --- Koniec sekcji filtrów ---

    latest_excel_file = get_app_or_latest_xls_file(RESULTS_DIR)
    if not latest_excel_file:
        print("Nie można wygenerować mapy bez pliku danych.")
        return

    df_schools_raw = load_school_data(latest_excel_file)
    df_classes_raw = load_classes_data(latest_excel_file)

    if df_schools_raw is None or df_classes_raw is None:
        print(
            "Nie udało się wczytać danych szkół lub klas. Mapa nie zostanie wygenerowana."
        )
        return

    df_filtered_classes = apply_filters_to_classes(
        df_classes_raw,
        wanted_subjects,
        avoided_subjects,
        max_ranking_poz,
        min_class_points,
        max_class_points,
        report_warning_callback=lambda msg: print(f"Ostrzeżenie: {msg}"),
    )

    any_filters_applied = any(
        [
            wanted_subjects,
            avoided_subjects,
            max_ranking_poz is not None,
            min_class_points is not None,
            max_class_points is not None,
        ]
    )

    if df_filtered_classes.empty and any_filters_applied:
        print("Żadne klasy nie spełniają podanych kryteriów filtrowania.")
    elif (
        df_filtered_classes.empty
        and not any_filters_applied
        and not df_classes_raw.empty
    ):
        # This case might mean all classes were filtered out by default logic in apply_filters if any,
        # or df_classes_raw was already empty (handled by initial check).
        # For now, assume it means no classes to display if df_filtered_classes is empty.
        print(
            "Brak klas do przetworzenia (prawdopodobnie wszystkie odfiltrowane lub brak danych)."
        )

    (
        df_schools_to_display,
        count_filtered_classes,
        detailed_filtered_classes_info,
        school_summary_from_filtered,
    ) = aggregate_filtered_class_data(
        df_filtered_classes, df_schools_raw, any_filters_applied
    )

    if df_schools_to_display.empty and any_filters_applied:
        print("Brak szkół do wyświetlenia po zastosowaniu filtrów.")
    elif df_schools_to_display.empty and not df_schools_raw.empty:
        print(
            "Brak szkół do wyświetlenia (żadne nie mają pasujących klas lub brak danych szkół)."
        )

    filters_info_html_str = ""
    if any_filters_applied:
        map_output_file = RESULTS_DIR / MAP_OUTPUT_FILENAME.replace(
            ".html", "_filtered.html"
        )
        if wanted_subjects:
            filters_info_html_str += (
                f"Rozszerzenia - poszukiwane: {', '.join(wanted_subjects)}<br>"
            )
        if avoided_subjects:
            filters_info_html_str += (
                f"Rozszerzenia - unikane: {', '.join(avoided_subjects)}<br>"
            )
        if max_ranking_poz is not None:
            filters_info_html_str += f"Ranking TOP: {max_ranking_poz}<br>"
        if min_class_points is not None:
            filters_info_html_str += (
                f"Minimalny próg punktowy klasy: {min_class_points}<br>"
            )
        if max_class_points is not None:
            filters_info_html_str += (
                f"Maksymalny próg punktowy klasy: {max_class_points}<br>"
            )
    else:
        map_output_file = RESULTS_DIR / MAP_OUTPUT_FILENAME
        filters_info_html_str = "Brak aktywnych filtrów.<br>"

    create_schools_map(
        df_schools_to_display=df_schools_to_display,
        output_path=map_output_file,
        class_count_per_school=count_filtered_classes,
        filtered_class_details_per_school=detailed_filtered_classes_info,
        school_summary_from_filtered=school_summary_from_filtered,
        filters_info_html=filters_info_html_str if any_filters_applied else "",
        show_heatmap=enable_heatmap,
    )


if __name__ == "__main__":
    main()
