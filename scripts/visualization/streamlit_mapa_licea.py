import streamlit as st

st.set_page_config(
    page_title="Mapa szkół średnich - Warszawa i okolice",
    page_icon="🏫",
    layout="wide",
)

import sys
import os
from pathlib import Path
import numpy as np
import pandas as pd
import folium
from folium.plugins import Fullscreen, LocateControl, HeatMap
from streamlit_folium import st_folium
import io

# Wszystkie etykiety widżetów zapisane w jednym miejscu,
# co ułatwia ewentualne modyfikacje i umożliwia resetowanie
# stanu za pomocą wspólnej listy kluczy.

FILTER_LABELS = {
    "school_type": "Wybierz typ szkoły:",
    "ranking_filter": "Pozycja w rankingu liceów (Perspektywy)",
    "ranking_top": "Pokaż licea z TOP:",
    "school_names": "Wybierz szkoły do wyświetlenia:",
    "class_types": "Wybierz typy oddziałów:",
    "wanted_subjects": "Wybierz poszukiwane przedmioty:",
    "avoided_subjects": "Wybierz unikane przedmioty:",
    "points_range": "Zakres progów minimalnych:",
    "show_heatmap": "Pokaż mapę cieplną szkół",
}

FILTER_HELPS = {
    "school_type": "Ogranicz listę do wybranego typu, np. liceum",
    "ranking_filter": "Filtr używa najnowszego dostępnego rankingu",
    "ranking_top": "Wybierz 'Wszystkie' aby nie ograniczać po rankingu",
    "school_names": "Filtrowanie konkretnych szkół wg ich nazw",
    "class_types": "np. ogólny [O] lub dwujęzyczny [D]/[DW]",
    "wanted_subjects": "Klasa musi je oferować",
    "avoided_subjects": "Klasa nie może ich mieć",
    "points_range": "Wybierz dolny i górny próg",
    "show_heatmap": "Zobacz zagęszczenie placówek",
}

FILTER_DEFAULTS = {
    "school_type": [],
    "school_names": [],
    "class_types": [],
    "wanted_subjects": [],
    "avoided_subjects": [],
    "show_heatmap": False,
    # Uwaga: ranking_top i points_range nie są tutaj — Streamlit nadaje im
    # początkową wartość z konstruktora widgetu (selectbox `index=0`,
    # slider `value=(min, max)`), a reset filtrów po prostu popuje wszystkie
    # klucze widgetów z session_state.
}

# Wykresy tabu Wizualizacje – etykiety i domyślny zestaw widocznych pozycji.
CHART_OPTIONS = {
    "histogram": "Rozkład progów punktowych",
    "bar_district": "Liczba klas w dzielnicach",
    "scatter_rank": "Ranking vs próg punktowy",
    "cooccurrence": "Współwystępowanie rozszerzeń",
    "bubble_commute": "Czas dojazdu vs próg (bąbelkowy)",
}
CHART_DEFAULT_SELECTION = ["histogram", "bar_district", "scatter_rank"]


# Dodaj katalog 'scripts' do sys.path, aby umożliwić importy z generate_map.py i innych modułów
scripts_dir = Path(__file__).resolve().parent.parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

# Import funkcji z generate_map.py
from visualization.generate_map import (
    RESULTS_DIR,
    WARSAW_CENTER_COORDS,
    get_app_or_latest_xls_file,
    get_available_years,
    get_default_year,
    load_metadata,
    load_quality,
    load_school_data,
    load_classes_data,
    get_subjects_from_dataframe,
    apply_filters_to_classes,
    aggregate_filtered_class_data,
    add_school_markers_to_map,
    build_legacy_threshold_display_table,
    build_offer_2026_display_table,
    display_cell,
    find_school_by_map_point,
    format_points_display,
    select_school_classes_for_year,
    threshold_certainty_display,
    threshold_range_display,
)
from visualization import plots
from visualization.release_notes import load_latest_release_notes
from analysis.score import (
    add_distance_from_point,
    haversine_km,
    score_personalized_classes,
    select_start_point,
    shortlist_schools_by_distance,
)
from api_clients.googlemaps_api import build_gmaps_client, geocode_address

RELEASE_NOTES_URL = (
    "https://github.com/pszanser/licea-warszawa/blob/main/HISTORIA_ZMIAN.md"
)

FIT_DISPLAY_COLUMNS = {
    "FitScore": "Dopasowanie",
    "RankingScore": "Ranking pkt",
    "AdmissionScore": "Próg pkt",
    "DistanceScore": "Bliskość pkt",
    "ProfileScore": "Profil pkt",
    "BrakiDanych": "Braki danych",
    "Dlaczego": "Dlaczego",
    "NazwaSzkoly": "Szkoła",
    "OddzialNazwa": "Klasa",
    "OdlegloscKm": "Odległość km",
    "AdmitMargin": "Margines pkt",
    "RyzykoProgu": "Ryzyko progu",
    "RankingPoz": "Ranking",
    "MinProg": "Próg",
    "Dzielnica": "Dzielnica",
    "PrzedmiotyRozszerzone": "Rozszerzenia",
    "Zawod": "Zawód",
    "JezykiObce": "Języki",
    "LiczbaMiejsc": "Miejsca",
    "ProgUsedLevel": "Pewność progu",
}


def render_release_notes_expander() -> None:
    """Pokazuje w sidebarze najnowszy wpis z historii zmian."""
    latest_release_notes = load_latest_release_notes()
    with st.expander("🆕 Co nowego?", expanded=False):
        if latest_release_notes:
            st.markdown(latest_release_notes)
        else:
            st.caption("Historia zmian będzie dostępna po opublikowaniu aktualizacji.")
        st.link_button("Pełna historia zmian", RELEASE_NOTES_URL)


FIT_START_POINT_KEY = "fit_start_point"
FIT_START_POINT_HINT_KEY = "fit_start_point_hint_shown"
FIT_LAST_MAP_CLICK_KEY = "fit_last_map_click"
FIT_START_POINT_FEEDBACK_KEY = "fit_start_point_feedback"
PZO_MAP_SELECTED_SCHOOL_KEY = "pzo_map_selected_school_id"
FIT_SCHOOL_SUMMARY_COLUMNS = [
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
    "SzkolaLat",
    "SzkolaLon",
]

# Centrum Warszawy używane do walidacji zgeokodowanych adresów.
WARSAW_VALIDATION_CENTER = (52.2297, 21.0122)
WARSAW_VALIDATION_RADIUS_KM = 40.0


def _remember_start_point(
    point: tuple[float, float], source: str, label: str | None = None
) -> None:
    """Zapisuje punkt startowy do session_state w jednej, ujednoliconej strukturze."""
    st.session_state[FIT_START_POINT_KEY] = {
        "lat": float(point[0]),
        "lon": float(point[1]),
        "source": source,
        "label": label,
    }


def _point_event_key(point: tuple[float, float] | None) -> tuple[float, float] | None:
    """Stabilny klucz zdarzenia kliknięcia, żeby nie obsługiwać starego kliku ponownie."""
    if point is None:
        return None
    try:
        return (round(float(point[0]), 6), round(float(point[1]), 6))
    except (TypeError, ValueError, IndexError):
        return None


def _get_last_map_click_key() -> tuple[float, float] | None:
    value = st.session_state.get(FIT_LAST_MAP_CLICK_KEY)
    if not isinstance(value, (tuple, list)) or len(value) != 2:
        return None
    try:
        return (float(value[0]), float(value[1]))
    except (TypeError, ValueError):
        return None


def _mark_map_click_as_handled(point: tuple[float, float] | None) -> None:
    point_key = _point_event_key(point)
    if point_key is not None:
        st.session_state[FIT_LAST_MAP_CLICK_KEY] = point_key


def _clear_start_point() -> None:
    """Czyści punkt bez odtwarzania ostatniego zapamiętanego kliku z mapy."""
    current_click = select_start_point(
        st.session_state.get("schools_map") or {}, allow_center=False
    )
    _mark_map_click_as_handled(current_click)
    st.session_state.pop(FIT_START_POINT_KEY, None)


def _push_start_point_feedback(kind: str, text: str) -> None:
    messages = st.session_state.get(FIT_START_POINT_FEEDBACK_KEY, [])
    if not isinstance(messages, list):
        messages = []
    messages.append({"kind": kind, "text": text})
    st.session_state[FIT_START_POINT_FEEDBACK_KEY] = messages


def _render_start_point_feedback() -> None:
    messages = st.session_state.pop(FIT_START_POINT_FEEDBACK_KEY, [])
    if not isinstance(messages, list):
        return
    for message in messages:
        kind = message.get("kind")
        text = message.get("text")
        if not text:
            continue
        if kind == "success":
            st.success(text)
        elif kind == "warning":
            st.warning(text)
        else:
            st.info(text)


def _get_remembered_start_point() -> dict | None:
    value = st.session_state.get(FIT_START_POINT_KEY)
    if not isinstance(value, dict):
        return None
    try:
        lat = float(value.get("lat"))  # type: ignore[arg-type]
        lon = float(value.get("lon"))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return {
        "lat": lat,
        "lon": lon,
        "source": value.get("source") or "nieznane",
        "label": value.get("label"),
    }


def _format_start_point(lat: float, lon: float) -> str:
    return f"{lat:.5f}, {lon:.5f}"


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def _geocode_address_cached(address: str) -> tuple[float, float] | None:
    """Geokoduje adres przez Google Maps z cache 24h. Zwraca None gdy brak klucza/wyniku."""
    gmaps = build_gmaps_client()
    if gmaps is None:
        return None
    return geocode_address(
        gmaps,
        address,
        region="pl",
        components={"administrative_area": "mazowieckie"},
    )


def _normalize_address(address: str) -> str:
    """Dodaje ', Warszawa' jeśli adres nie wskazuje miasta – poprawia trafność geokodowania."""
    cleaned = " ".join(address.strip().split())
    if not cleaned:
        return cleaned
    lower = cleaned.lower()
    if "warszaw" in lower or "warsaw" in lower:
        return cleaned
    return f"{cleaned}, Warszawa"


def _summarize_best_schools_for_display(fit_results: pd.DataFrame) -> pd.DataFrame:
    """Buduje tabelę szkół bez zależności od świeżo przeładowanego modułu score."""
    if fit_results.empty:
        return fit_results.iloc[0:0].copy()

    required = {"SzkolaIdentyfikator", "FitScore"}
    missing = required.difference(fit_results.columns)
    if missing:
        missing_text = ", ".join(sorted(missing))
        raise ValueError(f"Brak kolumn do podsumowania szkół: {missing_text}")

    counts = (
        fit_results.groupby("SzkolaIdentyfikator")
        .size()
        .rename("Liczba pasujących klas")
        .reset_index()
    )
    # Helper zostaje lokalny, żeby fragment Streamlit nie był wrażliwy na hot reload
    # modułu score; logika wyboru najlepszego wiersza pozostaje taka sama.
    best_schools = (
        fit_results.sort_values("FitScore", ascending=False, na_position="last")
        .groupby("SzkolaIdentyfikator", sort=False, group_keys=False)
        .head(1)
        .copy()
    )
    best_schools = best_schools.merge(counts, on="SzkolaIdentyfikator", how="left")
    best_schools = best_schools.sort_values(
        "FitScore", ascending=False, na_position="last"
    )
    summary_cols = [
        col for col in FIT_SCHOOL_SUMMARY_COLUMNS if col in best_schools.columns
    ]
    return best_schools[summary_cols].copy()


def create_schools_map_streamlit(
    df_schools_to_display: pd.DataFrame,
    class_count_per_school: dict,
    filtered_class_details_per_school: dict,
    school_summary_from_filtered: dict,
    show_heatmap: bool = False,
    start_point: tuple[float, float] | None = None,
):
    """
    Tworzy i zwraca mapę Folium z lokalizacjami szkół, korzystając z add_school_markers_to_map.

    Gdy podano start_point (lat, lon), rysuje na mapie dodatkową pinezkę reprezentującą
    punkt startowy użytkownika z zakładki "Moje dopasowanie" oraz dodaje do popupów
    szkół link „🚌 Sprawdź dojazd z Twojego punktu" kierujący do Google Maps transit.
    """
    m = folium.Map(location=WARSAW_CENTER_COORDS, zoom_start=11)
    Fullscreen().add_to(m)
    LocateControl().add_to(m)

    origin_lat: float | None = None
    origin_lon: float | None = None
    if start_point is not None:
        try:
            origin_lat = float(start_point[0])
            origin_lon = float(start_point[1])
        except (TypeError, ValueError, IndexError):
            origin_lat = origin_lon = None

    if df_schools_to_display.empty:
        st.warning("Brak szkół do wyświetlenia na mapie po zastosowaniu filtrów.")
        # Return empty map
    else:
        add_school_markers_to_map(
            folium_map_object=m,
            df_schools_to_display=df_schools_to_display,
            class_count_per_school=class_count_per_school,
            filtered_class_details_per_school=filtered_class_details_per_school,
            school_summary_from_filtered=school_summary_from_filtered,
            origin_lat=origin_lat,
            origin_lon=origin_lon,
            show_details_hint=True,
        )

    if show_heatmap and not df_schools_to_display.empty:
        heat_data = df_schools_to_display[["SzkolaLat", "SzkolaLon"]].values.tolist()
        HeatMap(heat_data, name="HeatMap").add_to(m)

    if start_point is not None:
        if origin_lat is not None and origin_lon is not None:
            folium.Marker(
                location=[origin_lat, origin_lon],
                tooltip="Twój punkt startowy",
                popup="Punkt startowy do dopasowania",
                icon=folium.Icon(color="purple", icon="home", prefix="fa"),
            ).add_to(m)
    return m


@st.cache_data(show_spinner=False)
def get_unique_school_names(df_schools):
    """
    Get sorted unique school names from the dataframe.
    This function is cached by Streamlit to avoid recomputing on every rerun.
    """
    return sorted(df_schools["NazwaSzkoly"].unique())


def get_filter_ranking_year(df_schools: pd.DataFrame, fallback_year: int) -> int:
    if "RankingRok" not in df_schools.columns:
        return int(fallback_year)
    years = pd.to_numeric(df_schools["RankingRok"], errors="coerce").dropna()
    return int(years.max()) if not years.empty else int(fallback_year)


@st.cache_data(ttl=60, show_spinner=False)
def get_app_or_latest_xls_file_cached(directory: Path) -> Path | None:
    return get_app_or_latest_xls_file(directory)


@st.cache_data(show_spinner=False)
def get_available_years_cached(excel_file: Path, data_version: int) -> list[int]:
    _ = data_version
    return get_available_years(excel_file)


@st.cache_data(show_spinner=False)
def get_default_year_cached(
    excel_file: Path, data_version: int, available_years: tuple[int, ...]
) -> int:
    _ = data_version
    return get_default_year(excel_file, list(available_years))


@st.cache_data(show_spinner=False)
def load_metadata_cached(
    excel_file: Path, selected_year: int | None, data_version: int
) -> pd.DataFrame:
    _ = data_version
    return load_metadata(excel_file, selected_year)


@st.cache_data(show_spinner=False)
def load_quality_cached(
    excel_file: Path, selected_year: int | None, data_version: int
) -> pd.DataFrame:
    _ = data_version
    return load_quality(excel_file, selected_year)


@st.cache_data(show_spinner=False)
def load_year_sheet_cached(
    excel_file: Path,
    sheet_name: str,
    selected_year: int | None,
    data_version: int,
) -> pd.DataFrame:
    _ = data_version
    try:
        df = pd.read_excel(excel_file, sheet_name=sheet_name)
    except Exception:
        return pd.DataFrame()
    if selected_year is not None and "year" in df.columns:
        df = df[df["year"] == selected_year].copy()
    return df


@st.cache_data(show_spinner=False)
def load_all_data(
    excel_file: Path, selected_year: int | None, data_version: int
) -> tuple[pd.DataFrame | None, pd.DataFrame | None]:
    """Wczytuje dane szkół i klas z pliku Excel tylko raz.

    Użycie dekoratora ``st.cache_data`` sprawia, że podczas kolejnych
    uruchomień skryptu Streamlit ponowne wczytywanie pliku z dysku nie
    będzie konieczne, dopóki ścieżka lub wersja pliku się nie zmieni.
    """
    _ = data_version
    df_schools = load_school_data(excel_file, year=selected_year)
    df_classes = load_classes_data(excel_file, year=selected_year)
    return df_schools, df_classes


def _build_fit_dataframe_column_config() -> dict:
    """Konfiguracja kolumn dla tabeli wyników dopasowania (FitScore jako pasek postępu,
    spójne formatowanie liczb)."""
    return {
        "Dopasowanie": st.column_config.ProgressColumn(
            "Dopasowanie",
            help="Łączna ocena dopasowania klasy do Twoich preferencji (0–100).",
            format="%.1f",
            min_value=0,
            max_value=100,
        ),
        "Ranking pkt": st.column_config.NumberColumn(
            "Ranking pkt",
            help="Składowa oceny: pozycja w rankingu Perspektyw (0–100).",
            format="%.1f",
        ),
        "Próg pkt": st.column_config.NumberColumn(
            "Próg pkt",
            help="Składowa oceny: szansa dostania się względem progu (0–100).",
            format="%.1f",
        ),
        "Bliskość pkt": st.column_config.NumberColumn(
            "Bliskość pkt",
            help="Składowa oceny: bliskość punktu startowego (0–100).",
            format="%.1f",
        ),
        "Odległość km": st.column_config.NumberColumn(
            "Odległość km",
            format="%.1f km",
        ),
        "Próg": st.column_config.NumberColumn(
            "Próg",
            help="Próg punktowy klasy z poprzedniego roku.",
            format="%.0f pkt",
        ),
        "Margines pkt": st.column_config.NumberColumn(
            "Margines pkt",
            help="Twoje punkty minus próg klasy. Dodatnie = bezpieczniej.",
            format="%+.0f",
        ),
        "Ranking": st.column_config.NumberColumn(
            "Ranking",
            help="Pozycja szkoły w rankingu Perspektyw.",
            format="%.0f",
        ),
        "Dojazd": st.column_config.LinkColumn(
            "🚌 Dojazd",
            help="Otwiera trasę komunikacją miejską od Twojego punktu startowego w Google Maps.",
            display_text="Sprawdź",
        ),
        "Braki danych": st.column_config.TextColumn(
            "Braki danych",
            help=(
                "Które ważone składowe nie miały danych i dlatego liczyły się jako 0."
            ),
        ),
    }


def _display_value(value, fallback: str = "—") -> str:
    if value is None:
        return fallback
    try:
        if pd.isna(value):
            return fallback
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    return text if text and text.lower() != "nan" else fallback


def _first_detail_row(df: pd.DataFrame, key: str, value) -> pd.Series | None:
    if df.empty or key not in df.columns:
        return None
    value_text = str(value)
    matches = df[df[key].astype(str).eq(value_text)]
    if matches.empty:
        return None
    return matches.iloc[0]


def _format_class_option(row: pd.Series) -> str:
    return f"{row.get('NazwaSzkoly', '')} — {row.get('OddzialNazwa', '')}"


def _rows_for_school_id(df: pd.DataFrame, school_id: str | None) -> pd.DataFrame:
    if df.empty or not school_id:
        return df.iloc[0:0].copy()
    for id_col in ["source_school_id", "SzkolaIdentyfikator"]:
        if id_col not in df.columns:
            continue
        matches = df[df[id_col].astype(str).eq(str(school_id))]
        if not matches.empty:
            return matches.copy()
    return df.iloc[0:0].copy()


def _school_id_from_map_state(
    map_state: dict | None, df_schools_to_display: pd.DataFrame
) -> str | None:
    if not isinstance(map_state, dict):
        return None
    return find_school_by_map_point(
        df_schools_to_display,
        map_state.get("last_object_clicked"),
        tooltip=map_state.get("last_object_clicked_tooltip"),
        popup=map_state.get("last_object_clicked_popup"),
    )


def _detail_metric_grid(items: list[tuple[str, object]]) -> None:
    rows = [
        {"Pole": label, "Wartość": _display_value(value)}
        for label, value in items
        if _display_value(value) != "—"
    ]
    if rows:
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    else:
        st.caption("Brak szczegółów w danych źródłowych.")


def _render_text_block(preview: object, full_text: object, label: str) -> None:
    preview_text = _display_value(preview, "")
    full = _display_value(full_text, "")
    if preview_text:
        st.write(preview_text)
    if full and full != preview_text:
        with st.expander(label, expanded=False):
            st.markdown(full)
    elif not preview_text and full:
        st.markdown(full)
    elif not preview_text and not full:
        st.caption("Brak opisu w danych źródłowych.")


def _sort_school_classes_for_details(df_classes: pd.DataFrame) -> pd.DataFrame:
    if df_classes.empty:
        return df_classes.copy()
    classes = df_classes.copy()
    classes["_sort_threshold"] = pd.to_numeric(
        classes.get("Prog_min_klasa"), errors="coerce"
    )
    return classes.sort_values(
        ["_sort_threshold", "OddzialNazwa"],
        ascending=[False, True],
        na_position="last",
    ).drop(columns=["_sort_threshold"], errors="ignore")


def _selected_dataframe_position(table_state, row_count: int) -> int:
    selected_rows = []
    selection = getattr(table_state, "selection", None)
    if selection is not None:
        selected_rows = list(getattr(selection, "rows", []))
    elif isinstance(table_state, dict):
        selected_rows = table_state.get("selection", {}).get("rows", [])
    selected_position = selected_rows[0] if selected_rows else 0
    if row_count <= 0:
        return 0
    return min(int(selected_position), row_count - 1)


def _render_summary_value(label: str, value: object) -> None:
    st.caption(label)
    st.markdown(f"**{display_cell(value)}**")


def _render_pzo_class_summary(detail: pd.Series, class_row: pd.Series) -> None:
    profile_value = display_cell(
        detail.get("PrzedmiotyRozszerzone"), ""
    ) or display_cell(detail.get("Zawod"), "")
    language_value = display_cell(detail.get("JezykiObce"), "") or display_cell(
        detail.get("JezykiObceIkonyOpis"), ""
    )
    summary_cols = st.columns([1, 2, 2, 1.2, 1.8])
    with summary_cols[0]:
        _render_summary_value(
            "Miejsca", format_points_display(detail.get("LiczbaMiejsc"))
        )
    with summary_cols[1]:
        _render_summary_value("Rozszerzenia / zawód", profile_value)
    with summary_cols[2]:
        _render_summary_value("Języki", language_value)
    with summary_cols[3]:
        _render_summary_value(
            "Próg ref. 2025",
            format_points_display(
                class_row.get("MinProg", class_row.get("Prog_min_klasa"))
            ),
        )
    with summary_cols[4]:
        _render_summary_value(
            "Pewność",
            threshold_certainty_display(
                detail.get("ProgUsedLevel", class_row.get("ProgUsedLevel"))
            ),
        )


def _render_pzo_class_details(
    class_row: pd.Series,
    *,
    class_details: pd.DataFrame,
    school_details: pd.DataFrame,
    threshold_matches: pd.DataFrame,
) -> None:
    class_id = class_row.get("source_class_id")
    school_id = class_row.get("source_school_id")
    detail = _first_detail_row(class_details, "source_class_id", class_id)
    school_detail = _first_detail_row(school_details, "source_school_id", school_id)
    if detail is None:
        detail = class_row

    st.markdown("**Szczegóły wybranej klasy 2026**")
    st.markdown(f"#### {display_cell(detail.get('OddzialNazwa'))}")
    _render_pzo_class_summary(detail, class_row)

    tab_offer, tab_profile, tab_criteria, tab_thresholds, tab_school = st.tabs(
        [
            "Oferta klasy",
            "Opis profilu",
            "Kryteria punktowane",
            "Progi z 2025",
            "Szkoła",
        ]
    )

    with tab_offer:
        _detail_metric_grid(
            [
                ("Szkoła", detail.get("NazwaSzkoly")),
                ("Klasa", detail.get("OddzialNazwa")),
                ("Liczba miejsc", detail.get("LiczbaMiejsc")),
                ("Typ grupy", detail.get("TypOddzialu")),
                ("Identyfikator", detail.get("OddzialKod")),
                ("Liczba oddziałów", detail.get("LiczbaOddzialow")),
                ("Rozszerzenia", detail.get("PrzedmiotyRozszerzone")),
                ("Zawód", detail.get("Zawod")),
                ("Dyscyplina sportowa", detail.get("DyscyplinaSportowa")),
                (
                    "Języki",
                    display_cell(detail.get("JezykiObce"), "")
                    or display_cell(detail.get("JezykiObceIkonyOpis"), ""),
                ),
            ]
        )

    with tab_profile:
        _render_text_block(
            detail.get("OpisOddzialuPreview"),
            detail.get("OpisOddzialuMarkdown"),
            "Pełny opis profilu",
        )

    with tab_criteria:
        _detail_metric_grid(
            [
                ("Pierwszy punktowany przedmiot", detail.get("Punktowany1")),
                ("Drugi punktowany przedmiot", detail.get("Punktowany2")),
                ("Trzeci punktowany przedmiot", detail.get("Punktowany3")),
                ("Czwarty punktowany przedmiot", detail.get("Punktowany4")),
            ]
        )
        criteria_text = _display_value(detail.get("KryteriaPunktowane"), "")
        if criteria_text:
            with st.expander("Pełny tekst kryteriów", expanded=False):
                st.write(criteria_text)

    with tab_thresholds:
        _detail_metric_grid(
            [
                (
                    "Próg referencyjny 2025",
                    format_points_display(
                        class_row.get("MinProg", class_row.get("Prog_min_klasa"))
                    ),
                ),
                (
                    "Status progu",
                    threshold_certainty_display(
                        detail.get("ProgUsedLevel", class_row.get("ProgUsedLevel"))
                    ),
                ),
                ("Dopasowana klasa 2025", detail.get("ProgMatchOldClass")),
            ]
        )
        technical_rows = [
            ("Metoda dopasowania", detail.get("ProgMatchMethod")),
            ("Wynik dopasowania", detail.get("ProgMatchScore")),
        ]
        if any(display_cell(value, "") for _, value in technical_rows):
            with st.expander("Szczegóły techniczne dopasowania", expanded=False):
                _detail_metric_grid(technical_rows)
        if (
            not threshold_matches.empty
            and "source_class_id" in threshold_matches.columns
        ):
            candidates = threshold_matches[
                threshold_matches["source_class_id"].astype(str).eq(str(class_id))
            ].copy()
            if not candidates.empty:
                display_cols = [
                    "candidate_rank",
                    "OldOddzialNazwa",
                    "Prog_min_klasa",
                    "match_status",
                    "match_score",
                ]
                candidate_display = candidates[
                    [col for col in display_cols if col in candidates.columns]
                ].rename(
                    columns={
                        "candidate_rank": "Kandydat",
                        "OldOddzialNazwa": "Klasa 2025",
                        "Prog_min_klasa": "Próg 2025",
                        "match_status": "Status",
                        "match_score": "Wynik",
                    }
                )
                if "Próg 2025" in candidate_display.columns:
                    candidate_display["Próg 2025"] = candidate_display[
                        "Próg 2025"
                    ].apply(format_points_display)
                if "Status" in candidate_display.columns:
                    candidate_display["Status"] = (
                        candidate_display["Status"]
                        .map(
                            {
                                "trusted": "dokładny",
                                "approximate": "przybliżony",
                                "candidate_only": "kandydat",
                            }
                        )
                        .fillna(candidate_display["Status"])
                    )
                with st.expander("Podobne klasy z 2025", expanded=False):
                    st.dataframe(
                        candidate_display.fillna("—"),
                        width="stretch",
                        hide_index=True,
                    )

    with tab_school:
        source = school_detail if school_detail is not None else detail
        _detail_metric_grid(
            [
                ("Nazwa", source.get("NazwaSzkoly")),
                ("Adres", source.get("AdresSzkoly")),
                ("Dzielnica", source.get("Dzielnica")),
                ("Telefon", source.get("Telefon")),
                ("E-mail", source.get("Email")),
            ]
        )
        www = _display_value(source.get("WWW"), "")
        pzo_url = _display_value(source.get("OfertaPzoUrl"), "")
        link_col1, link_col2 = st.columns(2)
        if www:
            with link_col1:
                st.link_button("Strona szkoły", www, width="stretch")
        if pzo_url:
            with link_col2:
                st.link_button("Wyszukiwarka PZO", pzo_url, width="stretch")
        _render_text_block(
            source.get("OpisSzkolyPreview"),
            source.get("OpisSzkolyMarkdown"),
            "Pełny opis placówki",
        )


def _render_pzo_map_school_details(
    school_row: pd.Series,
    *,
    df_filtered_classes: pd.DataFrame,
    legacy_classes: pd.DataFrame,
    class_details: pd.DataFrame,
    school_details: pd.DataFrame,
    threshold_matches: pd.DataFrame,
) -> None:
    school_id = school_row.get("source_school_id") or school_row.get(
        "SzkolaIdentyfikator"
    )
    legacy_school_id = school_row.get("SzkolaIdentyfikator")
    school_detail = _first_detail_row(school_details, "source_school_id", school_id)
    school_source = school_detail if school_detail is not None else school_row
    school_classes = _sort_school_classes_for_details(
        _rows_for_school_id(df_filtered_classes, str(school_id))
    )
    legacy_school_classes = select_school_classes_for_year(
        legacy_classes, legacy_school_id, 2025
    )

    st.markdown("**Szczegóły szkoły z mapy**")
    st.markdown(f"### {_display_value(school_source.get('NazwaSzkoly'))}")
    st.caption(
        f"{display_cell(school_source.get('Dzielnica'))} · "
        f"{display_cell(school_source.get('AdresSzkoly'))}"
    )

    ranking_value = school_row.get("RankingPoz")
    if display_cell(ranking_value, ""):
        ranking_display = format_points_display(ranking_value)
    else:
        ranking_display = format_points_display(school_source.get("RankingPoz"))
    legacy_threshold_count = 0
    if not legacy_school_classes.empty and "Prog_min_klasa" in legacy_school_classes:
        legacy_threshold_count = int(
            pd.to_numeric(legacy_school_classes["Prog_min_klasa"], errors="coerce")
            .notna()
            .sum()
        )
    metric_cols = st.columns(4)
    with metric_cols[0]:
        st.metric("Oferta 2026", f"{len(school_classes)} klas")
    with metric_cols[1]:
        st.metric("Klasy 2025", f"{legacy_threshold_count} z progami")
    with metric_cols[2]:
        st.metric("Zakres progów 2025", threshold_range_display(legacy_school_classes))
    with metric_cols[3]:
        st.metric("Ranking", ranking_display)

    info_col, links_col = st.columns([2, 1], vertical_alignment="top")
    with info_col:
        _detail_metric_grid(
            [
                ("Adres", school_source.get("AdresSzkoly")),
                ("Dzielnica", school_source.get("Dzielnica")),
                ("Telefon", school_source.get("Telefon")),
                ("E-mail", school_source.get("Email")),
            ]
        )
    with links_col:
        www = _display_value(school_source.get("WWW"), "")
        pzo_url = _display_value(school_source.get("OfertaPzoUrl"), "")
        if www:
            st.link_button("Strona szkoły", www, width="stretch")
        if pzo_url:
            st.link_button("Wyszukiwarka PZO", pzo_url, width="stretch")

    _render_text_block(
        school_source.get("OpisSzkolyPreview"),
        school_source.get("OpisSzkolyMarkdown"),
        "Pełny opis placówki",
    )

    selected_class_row = None
    st.markdown("**Oferta 2026**")
    st.caption("Aktualna oficjalna oferta PZO, zawężona aktywnymi filtrami.")
    if school_classes.empty:
        st.info("Ta szkoła nie ma klas spełniających aktualne filtry.")
    else:
        offer_display = build_offer_2026_display_table(school_classes)
        offer_state = st.dataframe(
            offer_display,
            width="stretch",
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            key=f"pzo_school_offer_2026_{school_id}",
        )
        selected_position = _selected_dataframe_position(
            offer_state, len(school_classes)
        )
        selected_class_row = school_classes.iloc[selected_position]

    st.markdown("**Klasy 2025 z progami**")
    st.caption(
        "Pełna historia klas tej szkoły z poprzedniego naboru, bez filtrów 2026."
    )
    if legacy_school_classes.empty:
        st.info("Brak klas 2025 dla tej szkoły w danych historycznych.")
    else:
        st.dataframe(
            build_legacy_threshold_display_table(legacy_school_classes),
            width="stretch",
            hide_index=True,
        )

    if selected_class_row is not None:
        _render_pzo_class_details(
            selected_class_row,
            class_details=class_details,
            school_details=school_details,
            threshold_matches=threshold_matches,
        )


@st.fragment
def _render_fit_results(
    *,
    remembered: dict,
    df_filtered_classes: pd.DataFrame,
    df_schools_to_display: pd.DataFrame,
    wanted_subjects_filter: list,
    selected_year,
    export_filter_entries: list,
    ranking_max_reference: float | None = None,
    class_details: pd.DataFrame | None = None,
    school_details: pd.DataFrame | None = None,
    threshold_matches: pd.DataFrame | None = None,
    enable_pzo_details: bool = False,
) -> None:
    """Renderuje sekcję obliczeń FitScore wewnątrz fragmentu Streamlit.

    Dzięki ``@st.fragment`` zmiany suwaków wag/punktów/odległości przeliczają
    tylko ten blok – nie powodują ponownego budowania mapy ani filtrów w sidebarze.
    """
    start_lat = remembered["lat"]
    start_lon = remembered["lon"]
    source_label = remembered["source"]
    label_text = remembered.get("label")
    coords_str = _format_start_point(start_lat, start_lon)
    if label_text:
        chip = f"📍 {label_text} — {coords_str} (źródło: {source_label})"
    else:
        chip = f"📍 {coords_str} (źródło: {source_label})"
    st.caption(chip)

    settings_col, weights_col = st.columns([1, 2])
    with settings_col:
        predicted_points = st.number_input(
            "Twoje przewidywane punkty",
            min_value=0.0,
            max_value=300.0,
            value=170.0,
            step=5.0,
            help=(
                "Maks. 300 pkt (200 z egzaminu ósmoklasisty + 100 ze świadectwa "
                "i osiągnięć). Średnie progi w warszawskich liceach to ~170–180 pkt. "
                "Wpisz swój wynik z egzaminu próbnego lub szacunek."
            ),
        )
        max_distance_km = st.slider(
            "Maks. odległość od domu (km)",
            min_value=3,
            max_value=25,
            value=8,
            step=1,
            help=(
                "Szkoły położone dalej niż ten promień (w linii prostej) "
                "nie będą brane pod uwagę."
            ),
        )
        shortlist_limit = st.slider(
            "Maks. szkół do oceny",
            min_value=10,
            max_value=100,
            value=40,
            step=5,
            help=(
                "Spośród szkół w zadanym promieniu weźmiemy aż tyle "
                "najbliższych. Więcej = wolniej, ale szerszy wybór."
            ),
        )
        top_classes_to_show = st.number_input(
            "Ile klas pokazać w tabeli",
            min_value=10,
            max_value=200,
            value=50,
            step=10,
            help="Ograniczenie tabeli wyników — same najlepiej pasujące.",
        )

    with weights_col:
        st.markdown("**Co jest dla Ciebie najważniejsze?**")
        st.caption("Przesuń suwaki: 0 = mało ważne, 10 = bardzo ważne.")
        w_col1, w_col2, w_col3 = st.columns(3)
        with w_col1:
            weight_ranking = st.slider(
                "Renoma szkoły",
                0,
                10,
                6,
                key="fit_weight_ranking",
                help="Im wyżej, tym ważniejsza pozycja w rankingu Perspektyw.",
            )
        with w_col2:
            weight_admission = st.slider(
                "Szansa dostania się",
                0,
                10,
                8,
                key="fit_weight_admission",
                help="Im wyżej, tym ważniejszy zapas między Twoimi punktami a progiem klasy.",
            )
        with w_col3:
            weight_distance = st.slider(
                "Bliskość",
                0,
                10,
                7,
                key="fit_weight_distance",
                help="Im wyżej, tym ważniejsza mała odległość od Twojego punktu startowego. Odległość liczona w linii prostej (nie czas dojazdu).",
            )
        st.caption(
            "Wybrane rozszerzenia (z lewego paska) działają jako filtr "
            "— nie mają osobnej wagi."
        )

    with st.expander("ℹ️ Jak liczymy dopasowanie?", expanded=False):
        st.markdown("""
**Co robimy?** Każdej klasie dajemy ocenę dopasowania od 0 do 100. Im więcej, tym lepiej pasuje do Ciebie.

Ocena to mieszanka **trzech rzeczy** (proporcja zależy od suwaków po prawej):

- **Renoma szkoły** — im wyżej w rankingu Perspektyw, tym więcej punktów. Numer 1 = 100, ostatnia szkoła = ok. 0.
- **Szansa dostania się** — porównujemy Twoje punkty z progiem klasy z poprzedniego roku.
  - Twoje 175 pkt, klasa wymagała 160 → zapas +15 pkt → ocena ok. 90 (bardzo bezpiecznie).
  - Twoje 160 pkt, klasa wymagała 160 → zapas 0 pkt → ocena ok. 50 (na styk).
  - Twoje 145 pkt, klasa wymagała 160 → zapas −15 pkt → ocena ok. 10 (raczej za nisko).
- **Bliskość** — odległość w linii prostej od Twojego punktu startowego.
  - 0 km → 100, 7 km → ok. 50, 15 km i dalej → 0.
  - żeby sprawdzić **rzeczywisty czas dojazdu** komunikacją miejską, kliknij kolumnę **🚌 Dojazd** przy danej klasie — otworzy Google Maps z gotową trasą.

**Ryzyko progu** w tabeli wynika ze wspomnianego zapasu punktów:

- 🟢 **bezpiecznie** — zapas co najmniej 15 pkt
- 🟡 **realnie** — zapas 0–14 pkt
- 🟠 **ryzykownie** — brakuje 1–10 pkt
- 🔴 **bardzo ryzykownie** — brakuje więcej niż 10 pkt

Wybrane rozszerzenia (np. matematyka) traktujemy jako filtr — klasy bez nich w ogóle nie wchodzą do oceny.
Jeśli brakuje danych dla ważonej składowej (np. rankingu albo progu), ta składowa liczy się jako 0 i pokazujemy to w kolumnie **Braki danych**.

*Uwaga:* progi z poprzedniego roku to tylko wskazówka — w nowym naborze mogą być inne.
            """)

    weights = {
        "ranking": weight_ranking,
        "admission": weight_admission,
        "distance": weight_distance,
        "profile": 0,
    }
    weight_labels = {
        "ranking": "ranking",
        "admission": "próg",
        "distance": "bliskość",
    }
    active_weights = {
        key: value for key, value in weights.items() if value > 0 and key != "profile"
    }
    active_weight_sum = sum(active_weights.values())
    if active_weight_sum <= 0:
        st.warning("Ustaw co najmniej jedną wagę większą od zera.")
        return

    weight_parts = [
        f"{weight_labels[key]} {value / active_weight_sum:.0%}"
        for key, value in active_weights.items()
    ]
    st.caption("Aktywne wagi: " + ", ".join(weight_parts))
    if wanted_subjects_filter:
        st.caption("Profil traktowany jako filtr: " + ", ".join(wanted_subjects_filter))
    schools_with_distance = add_distance_from_point(
        df_schools_to_display, start_lat, start_lon
    )
    shortlisted_schools = shortlist_schools_by_distance(
        schools_with_distance,
        limit=shortlist_limit,
        max_distance_km=max_distance_km,
    )

    if shortlisted_schools.empty:
        st.warning(
            "Brak szkół ze współrzędnymi w aktualnym zestawie filtrów "
            f"i promieniu do {max_distance_km} km."
        )
        return

    shortlisted_ids = shortlisted_schools["SzkolaIdentyfikator"].tolist()
    distance_cols = shortlisted_schools[
        ["SzkolaIdentyfikator", "OdlegloscKm"]
    ].drop_duplicates("SzkolaIdentyfikator")
    classes_for_fit = df_filtered_classes[
        df_filtered_classes["SzkolaIdentyfikator"].isin(shortlisted_ids)
    ].copy()
    classes_for_fit = classes_for_fit.drop(
        columns=["OdlegloscKm"], errors="ignore"
    ).merge(
        distance_cols,
        on="SzkolaIdentyfikator",
        how="left",
    )

    fit_results = score_personalized_classes(
        classes_for_fit,
        points=predicted_points,
        weights=weights,
        profile_subjects=wanted_subjects_filter,
        ranking_max_reference=ranking_max_reference,
    )

    st.metric(
        "Szkoły w okolicy",
        f"{len(shortlisted_schools)} / {len(df_schools_to_display)}",
    )
    st.caption(
        f"Uwzględniono szkoły do {max_distance_km} km od punktu "
        f"startowego, maksymalnie {shortlist_limit} najbliższych."
    )

    total_matches = len(fit_results)
    top_n = min(int(top_classes_to_show), total_matches)
    top_results = fit_results.head(top_n).copy()
    display_cols = [col for col in FIT_DISPLAY_COLUMNS if col in top_results.columns]
    display_df = top_results[display_cols].rename(columns=FIT_DISPLAY_COLUMNS)
    for col in ["Ranking", "Próg", "Margines pkt"]:
        if col in display_df.columns:
            display_df[col] = pd.to_numeric(display_df[col], errors="coerce").round(0)
    score_cols = [
        "Odległość km",
        "Dopasowanie",
        "Ranking pkt",
        "Próg pkt",
        "Bliskość pkt",
        "Profil pkt",
    ]
    for col in score_cols:
        if col in display_df.columns:
            display_df[col] = pd.to_numeric(display_df[col], errors="coerce").round(1)

    # Kolumna z linkiem do Google Maps transit od punktu startowego użytkownika.
    # Nie wymaga klucza API – użytkownik otwiera trasę bezpośrednio w Google Maps.
    if "SzkolaLat" in top_results.columns and "SzkolaLon" in top_results.columns:
        display_df["Dojazd"] = (
            "https://www.google.com/maps/dir/?api=1"
            f"&origin={start_lat},{start_lon}"
            "&destination="
            + top_results["SzkolaLat"].astype(str)
            + ","
            + top_results["SzkolaLon"].astype(str)
            + "&travelmode=transit"
        )
    else:
        display_df["Dojazd"] = None

    column_config = _build_fit_dataframe_column_config()

    st.markdown("**Najlepsze klasy dla mnie**")
    st.caption(f"Pokazano top {top_n} z {total_matches} dopasowanych klas.")
    details_enabled = (
        enable_pzo_details and class_details is not None and not class_details.empty
    )
    table_state = None
    if details_enabled:
        table_state = st.dataframe(
            display_df,
            width="stretch",
            hide_index=True,
            column_config=column_config,
            on_select="rerun",
            selection_mode="single-row",
            key="fit_results_2026",
        )
    else:
        st.dataframe(
            display_df,
            width="stretch",
            hide_index=True,
            column_config=column_config,
        )
    st.caption(
        "Ryzyko progu: 🟢 bezpiecznie (zapas ≥15 pkt) · "
        "🟡 realnie (0–14 pkt) · 🟠 ryzykownie (brak 1–10 pkt) · "
        "🔴 bardzo ryzykownie (brak >10 pkt)."
    )
    if details_enabled and not top_results.empty:
        selected_rows = []
        selection = getattr(table_state, "selection", None)
        if selection is not None:
            selected_rows = list(getattr(selection, "rows", []))
        elif isinstance(table_state, dict):
            selected_rows = table_state.get("selection", {}).get("rows", [])
        selected_position = selected_rows[0] if selected_rows else 0
        selected_position = min(int(selected_position), len(top_results) - 1)
        _render_pzo_class_details(
            top_results.iloc[selected_position],
            class_details=(
                class_details if class_details is not None else pd.DataFrame()
            ),
            school_details=(
                school_details if school_details is not None else pd.DataFrame()
            ),
            threshold_matches=(
                threshold_matches if threshold_matches is not None else pd.DataFrame()
            ),
        )

    school_summary = pd.DataFrame()
    if not fit_results.empty:
        school_summary = _summarize_best_schools_for_display(fit_results).rename(
            columns={
                "FitScore": "Dopasowanie",
                "NazwaSzkoly": "Szkoła",
                "Dzielnica": "Dzielnica",
                "OddzialNazwa": "Najlepsza klasa",
                "Liczba pasujących klas": "Pasujące klasy",
                "OdlegloscKm": "Odległość km",
                "RankingScore": "Ranking pkt",
                "AdmissionScore": "Próg pkt",
                "DistanceScore": "Bliskość pkt",
                "ProfileScore": "Profil pkt",
                "RankingPoz": "Ranking",
                "MinProg": "Próg",
                "AdmitMargin": "Margines pkt",
                "RyzykoProgu": "Ryzyko progu",
                "BrakiDanych": "Braki danych",
                "PrzedmiotyRozszerzone": "Rozszerzenia",
                "Dlaczego": "Dlaczego",
            }
        )
        for col in ["Ranking", "Próg", "Margines pkt"]:
            if col in school_summary.columns:
                school_summary[col] = pd.to_numeric(
                    school_summary[col], errors="coerce"
                ).round(0)
        for col in score_cols:
            if col in school_summary.columns:
                school_summary[col] = pd.to_numeric(
                    school_summary[col], errors="coerce"
                ).round(1)

        if (
            "SzkolaLat" in school_summary.columns
            and "SzkolaLon" in school_summary.columns
        ):
            school_summary["Dojazd"] = (
                "https://www.google.com/maps/dir/?api=1"
                f"&origin={start_lat},{start_lon}"
                "&destination="
                + school_summary["SzkolaLat"].astype(str)
                + ","
                + school_summary["SzkolaLon"].astype(str)
                + "&travelmode=transit"
            )
        school_summary = school_summary.drop(
            columns=[
                c for c in ["SzkolaLat", "SzkolaLon"] if c in school_summary.columns
            ]
        )

        with st.expander("Najlepsze szkoły", expanded=False):
            st.dataframe(
                school_summary.head(20),
                width="stretch",
                hide_index=True,
                column_config=column_config,
            )

    export_params = export_filter_entries + [
        ("Punkt startowy", f"{start_lat:.6f}, {start_lon:.6f}"),
        ("Źródło punktu", source_label),
        ("Etykieta punktu", label_text or "—"),
        ("Przewidywane punkty", predicted_points),
        ("Maksymalna odległość km", max_distance_km),
        ("Limit shortlisty szkół", shortlist_limit),
        ("Top N klas (UI)", top_n),
        ("Waga ranking", weight_ranking),
        ("Waga próg", weight_admission),
        ("Waga bliskość", weight_distance),
        (
            "Rozszerzenia dla profilu",
            ", ".join(wanted_subjects_filter) or "brak",
        ),
    ]
    fit_buf = io.BytesIO()
    with pd.ExcelWriter(fit_buf, engine="openpyxl") as writer:
        fit_results.to_excel(writer, index=False, sheet_name="Klasy")
        if not school_summary.empty:
            school_summary.to_excel(writer, index=False, sheet_name="Szkoly")
        shortlisted_schools.to_excel(
            writer, index=False, sheet_name="Szkoly_shortlista"
        )
        pd.DataFrame(export_params, columns=["Parametr", "Wartość"]).to_excel(
            writer, index=False, sheet_name="Parametry"
        )
    fit_buf.seek(0)
    st.download_button(
        label="📥 Pobierz moje dopasowanie (Excel)",
        data=fit_buf,
        file_name=f"moje_dopasowanie_{selected_year}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=f"download_fit_{selected_year}",
        on_click="ignore",
    )


def main():
    st.title("🏫 Mapa szkół średnich - Warszawa i okolice")
    st.markdown("""
    Aplikacja umożliwia interaktywne przeglądanie szkół średnich w Warszawie i okolicach oraz filtrowanie ich według różnych kryteriów.
    """)

    # Initialize session state for filters if not already set
    # Używamy globalnego FILTER_DEFAULTS
    for key, value in FILTER_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = value

    latest_excel_file = get_app_or_latest_xls_file_cached(RESULTS_DIR)
    if not latest_excel_file:
        st.error("Nie można wygenerować mapy bez pliku danych.")
        return

    data_version = latest_excel_file.stat().st_mtime_ns
    available_years = get_available_years_cached(latest_excel_file, data_version)
    default_year = get_default_year_cached(
        latest_excel_file, data_version, tuple(available_years)
    )
    selected_year_state = st.session_state.get("selected_year")
    if selected_year_state not in available_years:
        st.session_state.pop("selected_year", None)
        selected_year_state = default_year
    default_index = available_years.index(selected_year_state)
    with st.sidebar:
        st.header("Dane")
        selected_year = st.selectbox(
            "Rok danych:",
            available_years,
            index=default_index,
            key="selected_year",
            help="Domyślnie pokazywany jest najnowszy kompletny rok danych.",
        )
        render_release_notes_expander()

    metadata = load_metadata_cached(latest_excel_file, selected_year, data_version)
    quality = load_quality_cached(latest_excel_file, selected_year, data_version)
    meta_row = metadata.iloc[0].to_dict() if not metadata.empty else {}
    status_label = meta_row.get("status_label") or "dane historyczne"
    threshold_label = meta_row.get("threshold_label")

    # Dane wczytujemy z cache'em zależnym od czasu modyfikacji pliku.
    df_schools_raw, df_classes_raw = load_all_data(
        latest_excel_file, selected_year, data_version
    )
    df_school_details = load_year_sheet_cached(
        latest_excel_file, "school_details", selected_year, data_version
    )
    df_class_details = load_year_sheet_cached(
        latest_excel_file, "class_details", selected_year, data_version
    )
    df_threshold_matches = load_year_sheet_cached(
        latest_excel_file, "threshold_matches", selected_year, data_version
    )
    df_classes_2025 = load_year_sheet_cached(
        latest_excel_file, "classes", 2025, data_version
    )

    if df_schools_raw is None or df_classes_raw is None:
        st.error(
            "Nie udało się wczytać danych szkół lub klas. Mapa nie zostanie wygenerowana."
        )
        return
    enable_pzo_details = (
        selected_year == 2026
        and meta_row.get("data_status") == "official_offer"
        and not df_class_details.empty
    )
    ranking_year = get_filter_ranking_year(df_schools_raw, selected_year)
    ranking_max_reference = None
    if "RankingPoz" in df_classes_raw.columns:
        ranking_values = pd.to_numeric(df_classes_raw["RankingPoz"], errors="coerce")
        if not ranking_values.dropna().empty:
            ranking_max_reference = float(ranking_values.max())

    # Przewodnik jest zawsze dostępny, ale domyślnie zwinięty.
    onboarding_container = st.expander(
        "👋 Pierwszy raz tutaj? Zobacz przewodnik po aplikacji",
        expanded=False,
    )

    with onboarding_container:
        st.markdown("""
**Aplikacja pomaga wybrać szkołę średnią w 4 krokach:**

1. **⬅️ Filtry (lewy pasek)** — zacznij od ograniczenia listy: typ szkoły,
   ranking, poszukiwane lub unikane przedmioty rozszerzone, zakres progów
   punktowych. Liczby u góry (Szkoły, Klasy, Średni próg) reagują na bieżąco.
2. **🗺️ Mapa** — zobacz lokalizacje szkół. **Kliknij znacznik szkoły**,
   żeby wybrać ją na mapie — pod mapą pojawią się dane szkoły, oferta 2026,
   klasy 2025 z progami i szczegóły wybranej klasy. **Kliknij pusty fragment mapy**,
   żeby zaznaczyć swój punkt startowy (np. dom). Pojawi się fioletowa pinezka 🏠.
   Po ustawieniu punktu, dymek każdej szkoły pokazuje link
   **🚌 Sprawdź dojazd z Twojego punktu** — otwiera Google Maps z trasą komunikacją miejską.
3. **🎯 Moje dopasowanie** — policzymy ranking klas dopasowanych do Ciebie
   na podstawie Twoich punktów, ważności kryteriów (renoma / szansa / bliskość)
   i odległości **w linii prostej** od Twojego punktu startowego. Punkt startowy możesz też wpisać jako adres.
   W tabeli wyników kliknij **🚌 Dojazd**, żeby sprawdzić rzeczywisty czas dojazdu w Google Maps.
4. **📊 Wizualizacje** — wykresy pomagające porównać szkoły (rozkład progów,
   liczba klas w dzielnicach, ranking vs próg).

💡 **Wskazówka:** przycisk **Resetuj filtry** w lewym pasku przywraca stan
początkowy. Wyniki możesz pobrać do Excela (przyciski pod mapą i pod tabelą
dopasowania).
            """)
        st.caption("Możesz wrócić do tego przewodnika w każdej chwili.")

    # prezentujemy nazwę tylko przy lokalnym uruchomieniu
    # (w przypadku uruchomienia w chmurze Streamlit nazwa pliku zawiera "_SL")
    if "_SL" not in latest_excel_file.name:
        with st.expander("ℹ️ Informacje o danych", expanded=False):
            st.write(f"Plik źródłowy: `{latest_excel_file.name}`")
            st.write(f"Rok danych: **{selected_year}** | status: **{status_label}**")
            if not quality.empty:
                q = quality.iloc[0]
                st.caption(
                    "Kontrola danych: "
                    f"szkoły {int(q.get('schools_count', 0))}, "
                    f"klasy/wiersze {int(q.get('classes_count', 0))}, "
                    f"progi klasowe w {int(q.get('classes_with_threshold', 0))} wierszach, "
                    f"progi szkolne w {int(q.get('classes_with_school_threshold', 0))} wierszach."
                )
    else:
        st.caption(f"Rok danych: **{selected_year}** · status: **{status_label}**")

    available_subjects = get_subjects_from_dataframe(df_classes_raw)
    available_class_types = (
        sorted(df_classes_raw["TypOddzialu"].dropna().unique())
        if "TypOddzialu" in df_classes_raw.columns
        else []
    )

    with st.sidebar:
        st.header("Filtry")

        if st.button("Resetuj filtry"):
            # Bezwarunkowo czyścimy wszystkie klucze widgetów filtrów. Po `pop`
            # i `st.rerun()` widgety odbudują się z domyślnych wartości
            # przekazanych w konstruktorze (np. selectbox `index=0`,
            # slider `value=(min, max)`, multiselect bez `default=` → []).
            filter_widget_keys = [
                "school_type",
                "school_names",
                "class_types",
                "wanted_subjects",
                "avoided_subjects",
                "show_heatmap",
                "points_range",
                "viz_selected_charts",
            ]
            # Plus stan zakładki „Moje dopasowanie", który zależy od filtrów.
            fit_widget_keys = [
                "fit_start_source",
                "fit_address_input",
                "fit_weight_ranking",
                "fit_weight_admission",
                "fit_weight_distance",
                FIT_START_POINT_KEY,
                FIT_START_POINT_HINT_KEY,
                FIT_LAST_MAP_CLICK_KEY,
                FIT_START_POINT_FEEDBACK_KEY,
                PZO_MAP_SELECTED_SCHOOL_KEY,
                "schools_map",
            ]
            for k in filter_widget_keys + fit_widget_keys:
                st.session_state.pop(k, None)
            # selectbox z None jako wartością domyślną wymaga jawnego ustawienia
            # (samo pop nie zawsze resetuje do index=0 w Streamlit)
            st.session_state["ranking_top"] = None
            st.rerun()

        st.subheader("Typ szkoły")
        school_type_options = ["liceum", "technikum", "branżowa"]
        selected_school_types = st.multiselect(
            FILTER_LABELS["school_type"],
            school_type_options,
            placeholder="Wybierz...",
            key="school_type",
            help=FILTER_HELPS["school_type"],
        )

        st.subheader(f"Ranking Perspektyw {int(ranking_year)}")
        ranking_options = [None, 10, 20, 30, 40, 50, 75, 100]

        def _format_ranking_option(value):
            return "Wszystkie" if value is None else f"TOP {value}"

        max_ranking_poz_filter = st.selectbox(
            FILTER_LABELS["ranking_filter"],
            ranking_options,
            index=0,
            format_func=_format_ranking_option,
            key="ranking_top",
            help=FILTER_HELPS["ranking_top"],
        )

        st.subheader("Nazwa szkoły")
        # Lista nazw szkół zależy od wybranych typów
        if selected_school_types:
            df_for_names = df_schools_raw[
                df_schools_raw["TypSzkoly"].isin(selected_school_types)
            ]
        else:
            df_for_names = df_schools_raw

        # Dodatkowe ograniczenie listy nazw na podstawie rankingu (TOP)
        if max_ranking_poz_filter is not None and "RankingPoz" in df_for_names.columns:
            df_for_names = df_for_names[
                df_for_names["RankingPoz"] <= max_ranking_poz_filter
            ]

        school_names = get_unique_school_names(df_for_names)
        selected_school_names = st.multiselect(
            FILTER_LABELS["school_names"],
            school_names,
            placeholder="Wybierz...",
            key="school_names",
            help=FILTER_HELPS["school_names"],
        )

        st.subheader("Typ oddziału")
        selected_class_types = st.multiselect(
            FILTER_LABELS["class_types"],
            available_class_types,
            placeholder="Wybierz...",
            key="class_types",
            help=FILTER_HELPS["class_types"],
        )

        st.subheader("Filtr przedmiotów rozszerzonych")
        st.markdown("**Poszukiwane rozszerzenia**")
        wanted_subjects_filter = st.multiselect(
            FILTER_LABELS["wanted_subjects"],
            available_subjects,
            placeholder="Wybierz...",
            key="wanted_subjects",
            help=FILTER_HELPS["wanted_subjects"],
        )

        st.markdown("**Unikane rozszerzenia**")
        avoided_subjects_filter = st.multiselect(
            FILTER_LABELS["avoided_subjects"],
            available_subjects,
            placeholder="Wybierz...",
            key="avoided_subjects",
            help=FILTER_HELPS["avoided_subjects"],
        )

        progi_label = "Progi punktowe szkoły"
        if pd.notna(threshold_label) and str(threshold_label).strip():
            progi_label = f"{progi_label} ({threshold_label})"
        st.subheader(progi_label)

        progi_series = (
            pd.to_numeric(df_classes_raw.get("Prog_min_szkola"), errors="coerce")
            if "Prog_min_szkola" in df_classes_raw.columns
            else pd.Series(dtype=float)
        )
        progi_valid = progi_series.dropna()
        if not progi_valid.empty:
            min_pts = float(np.floor(progi_valid.min()))
            max_pts = float(np.ceil(progi_valid.max()))
        else:
            min_pts, max_pts = 100.0, 200.0
        if max_pts <= min_pts:
            max_pts = min_pts + 1.0

        points_range = st.slider(
            FILTER_LABELS["points_range"],
            min_value=min_pts,
            max_value=max_pts,
            value=(min_pts, max_pts),
            step=1.0,
            key="points_range",
            help=(
                f"{FILTER_HELPS['points_range']} "
                f"(pełny zakres {int(min_pts)}–{int(max_pts)} pkt = brak filtra)."
            ),
        )
        # Filtr aktywny tylko gdy zakres został zawężony (porównujemy z marginesem na float).
        if points_range[0] > min_pts + 0.5:
            min_class_points_filter = points_range[0]
        else:
            min_class_points_filter = None
        if points_range[1] < max_pts - 0.5:
            max_class_points_filter = points_range[1]
        else:
            max_class_points_filter = None

        st.divider()

        show_heatmap = st.checkbox(
            FILTER_LABELS["show_heatmap"],
            key="show_heatmap",
            help=FILTER_HELPS["show_heatmap"],
        )

    # Filtrowanie po typie szkoły; brak wyboru oznacza wszystkie typy
    if selected_school_types:
        df_classes_by_type = df_classes_raw[
            df_classes_raw["TypSzkoly"].isin(selected_school_types)
        ]
        df_schools_by_type = df_schools_raw[
            df_schools_raw["TypSzkoly"].isin(selected_school_types)
        ]
    else:
        df_classes_by_type = df_classes_raw
        df_schools_by_type = df_schools_raw

    if selected_school_names:
        df_classes_by_type = df_classes_by_type[
            df_classes_by_type["NazwaSzkoly"].isin(selected_school_names)
        ]
        df_schools_by_type = df_schools_by_type[
            df_schools_by_type["NazwaSzkoly"].isin(selected_school_names)
        ]

    df_filtered_classes = apply_filters_to_classes(
        df_classes_by_type,
        wanted_subjects=wanted_subjects_filter,
        avoided_subjects=avoided_subjects_filter,
        max_ranking_poz=max_ranking_poz_filter,
        min_class_points=min_class_points_filter,
        max_class_points=max_class_points_filter,
        allowed_class_types=selected_class_types,
        report_warning_callback=st.warning,
    )

    any_filters_active = any(
        [
            wanted_subjects_filter,
            avoided_subjects_filter,
            max_ranking_poz_filter is not None,
            min_class_points_filter is not None,
            max_class_points_filter is not None,
            bool(selected_school_types),
            bool(selected_class_types),
            bool(selected_school_names),
        ]
    )

    if df_filtered_classes.empty and any_filters_active:
        st.warning("Żadne klasy nie spełniają podanych kryteriów filtrowania.")
    elif df_filtered_classes.empty and not df_classes_raw.empty:
        st.warning("Brak klas w danych wejściowych lub wszystkie zostały odfiltrowane.")

    (
        df_schools_to_display,
        count_filtered_classes,
        detailed_filtered_classes_info,
        school_summary_from_filtered,
    ) = aggregate_filtered_class_data(
        df_filtered_classes, df_schools_by_type, any_filters_active
    )

    filter_entries = []
    if selected_school_types:
        filter_entries.append(("Typ szkoły", ", ".join(selected_school_types)))
    if selected_class_types:
        filter_entries.append(("Typ oddziału", ", ".join(selected_class_types)))
    if selected_school_names:
        filter_entries.append(("Wybrane szkoły", ", ".join(selected_school_names)))
    if wanted_subjects_filter:
        filter_entries.append(
            ("Rozszerzenia - poszukiwane", ", ".join(wanted_subjects_filter))
        )
    if avoided_subjects_filter:
        filter_entries.append(
            ("Rozszerzenia - unikane", ", ".join(avoided_subjects_filter))
        )
    if max_ranking_poz_filter is not None:
        filter_entries.append(
            (f"Ranking Perspektyw {int(ranking_year)} TOP", max_ranking_poz_filter)
        )
    if min_class_points_filter is not None:
        filter_entries.append(
            ("Minimalny próg punktowy klasy", min_class_points_filter)
        )
    if max_class_points_filter is not None:
        filter_entries.append(
            ("Maksymalny próg punktowy klasy", max_class_points_filter)
        )
    export_filter_entries = [
        ("Rok danych", selected_year),
        ("Status danych", status_label),
    ] + filter_entries

    if filter_entries:
        with st.expander(f"🔎 Aktywne filtry ({len(filter_entries)})", expanded=True):
            for label, value in filter_entries:
                st.markdown(f"- **{label}:** {value}")

    # Najpierw odczytujemy klik z poprzedniego renderu zapisany przez st_folium
    # w session_state["schools_map"]. Dzięki temu możemy zaktualizować punkt startowy
    # ZANIM zbudujemy nowy obiekt mapy (jeden render zamiast dwóch).
    prev_map_state = st.session_state.get("schools_map") or {}
    prev_clicked_school_id = (
        _school_id_from_map_state(prev_map_state, df_schools_to_display)
        if enable_pzo_details
        else None
    )
    pre_clicked_point = select_start_point(prev_map_state, allow_center=False)
    pre_clicked_key = _point_event_key(pre_clicked_point)
    active_start_source = st.session_state.get("fit_start_source") or "Klik na mapie"
    if pre_clicked_point is not None and pre_clicked_key != _get_last_map_click_key():
        if prev_clicked_school_id:
            st.session_state[PZO_MAP_SELECTED_SCHOOL_KEY] = prev_clicked_school_id
        elif active_start_source == "Klik na mapie":
            _remember_start_point(pre_clicked_point, source="klik na mapie")
            if not st.session_state.get(FIT_START_POINT_HINT_KEY):
                st.toast(
                    "Punkt startowy zapamiętany. Sprawdź zakładkę 🎯 Moje dopasowanie.",
                    icon="📍",
                )
                st.session_state[FIT_START_POINT_HINT_KEY] = True
        _mark_map_click_as_handled(pre_clicked_point)

    # Punkt startowy z poprzedniego renderu (potrzebny do narysowania pinezki na mapie).
    remembered_start = _get_remembered_start_point()
    start_point_for_map = (
        (remembered_start["lat"], remembered_start["lon"])
        if remembered_start is not None
        else None
    )

    map_object = create_schools_map_streamlit(
        df_schools_to_display=df_schools_to_display,
        class_count_per_school=count_filtered_classes,
        filtered_class_details_per_school=detailed_filtered_classes_info,
        school_summary_from_filtered=school_summary_from_filtered,
        show_heatmap=show_heatmap,
        start_point=start_point_for_map,
    )

    total_schools = len(df_schools_raw)
    total_classes = len(df_classes_raw)
    matching_schools = len(df_schools_to_display)
    matching_classes = (
        sum(count_filtered_classes.values()) if count_filtered_classes else 0
    )

    avg_points = None
    if not df_filtered_classes.empty:
        serie = df_filtered_classes.apply(
            lambda r: (
                r["Prog_min_klasa"]
                if pd.notna(r["Prog_min_klasa"])
                else r["Prog_min_szkola"]
            ),
            axis=1,
        )
        avg_points_calc = serie.mean()
        if pd.notna(avg_points_calc):
            avg_points = float(avg_points_calc)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Szkoły", f"{matching_schools} / {total_schools}")
    with col2:
        st.metric("Klasy", f"{matching_classes} / {total_classes}")
    with col3:
        if avg_points is not None:
            st.metric("Średni próg (pasujące klasy)", f"{avg_points:.1f} pkt")
        else:
            st.metric("Średni próg (pasujące klasy)", "—")

    tab_map, tab_fit, tab_viz = st.tabs(
        ["🗺️ Mapa", "🎯 Moje dopasowanie", "📊 Wizualizacje"]
    )

    with tab_map:
        st.subheader("Mapa szkół")
        map_state = st_folium(
            map_object,
            width=None,
            height=600,
            returned_objects=[
                "last_clicked",
                "last_object_clicked",
                "last_object_clicked_tooltip",
                "last_object_clicked_popup",
                "center",
                "zoom",
            ],
            key="schools_map",
        )
        if enable_pzo_details and not df_schools_to_display.empty:
            clicked_school_id = _school_id_from_map_state(
                map_state, df_schools_to_display
            )
            if clicked_school_id:
                st.session_state[PZO_MAP_SELECTED_SCHOOL_KEY] = clicked_school_id

            selected_school_id = st.session_state.get(PZO_MAP_SELECTED_SCHOOL_KEY)
            selected_school_rows = _rows_for_school_id(
                df_schools_to_display, selected_school_id
            )
            if selected_school_rows.empty:
                st.info(
                    "Kliknij znacznik szkoły na mapie, żeby zobaczyć jej ofertę i klasy."
                )
                st.session_state.pop(PZO_MAP_SELECTED_SCHOOL_KEY, None)
            else:
                _render_pzo_map_school_details(
                    selected_school_rows.iloc[0],
                    df_filtered_classes=df_filtered_classes,
                    legacy_classes=df_classes_2025,
                    class_details=df_class_details,
                    school_details=df_school_details,
                    threshold_matches=df_threshold_matches,
                )

        if not df_filtered_classes.empty:
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                df_filtered_classes.to_excel(writer, index=False, sheet_name="Klasy")
                if export_filter_entries:
                    filters_df = pd.DataFrame(
                        export_filter_entries, columns=["Filtr", "Wartość"]
                    )
                    filters_df.to_excel(writer, index=False, sheet_name="Parametry")
            buf.seek(0)
            st.download_button(
                label="📥 Pobierz dane klas (Excel)",
                data=buf,
                file_name=f"moje_klasy_{selected_year}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key=f"download_classes_{selected_year}",
                on_click="ignore",
            )

        if not df_schools_to_display.empty:
            with st.expander("Pokaż listę pasujących szkół", expanded=False):
                schools_summary_list = []
                for _, school_row in df_schools_to_display.iterrows():
                    szk_id = school_row["SzkolaIdentyfikator"]
                    class_count = count_filtered_classes.get(szk_id, 0)

                    min_threshold_from_filtered_classes = None
                    if (
                        szk_id in school_summary_from_filtered
                        and "Prog_min_szkola" in school_summary_from_filtered[szk_id]
                    ):
                        min_threshold_from_filtered_classes = (
                            school_summary_from_filtered[szk_id]["Prog_min_szkola"]
                        )
                    elif szk_id in detailed_filtered_classes_info:
                        thresholds = [
                            class_info.get("min_pkt_klasy")
                            for class_info in detailed_filtered_classes_info[szk_id]
                            if class_info.get("min_pkt_klasy") is not None
                        ]
                        if thresholds:
                            min_threshold_from_filtered_classes = min(thresholds)

                    display_ranking = school_row.get("RankingPoz")
                    if pd.notna(display_ranking):
                        display_ranking = (
                            int(display_ranking)
                            if display_ranking == display_ranking // 1
                            else float(display_ranking)
                        )
                    else:
                        display_ranking = None

                    schools_summary_list.append(
                        {
                            "Nazwa szkoły": school_row["NazwaSzkoly"],
                            "Dzielnica": school_row["Dzielnica"],
                            "Ranking": display_ranking,
                            "Liczba pasujących klas": class_count,
                            "Min. próg pkt. (z pasujących klas)": (
                                min_threshold_from_filtered_classes
                                if pd.notna(min_threshold_from_filtered_classes)
                                else None
                            ),
                        }
                    )

                schools_summary_df = pd.DataFrame(schools_summary_list)

                if "Min. próg pkt. (z pasujących klas)" in schools_summary_df.columns:
                    schools_summary_df["Min. próg pkt. (z pasujących klas)"] = (
                        pd.to_numeric(
                            schools_summary_df["Min. próg pkt. (z pasujących klas)"],
                            errors="coerce",
                        )
                    )

                if "Ranking" in schools_summary_df.columns:
                    schools_summary_df["Ranking"] = pd.to_numeric(
                        schools_summary_df["Ranking"], errors="coerce"
                    )

                st.dataframe(schools_summary_df, width="stretch")

    with tab_fit:
        st.subheader("Moje dopasowanie")
        st.caption(
            "Porównujemy szkoły po trzech rzeczach: pozycji w rankingu Perspektyw, "
            "szansie dostania się (Twoje punkty vs próg klasy) i odległości od "
            "wybranego miejsca."
        )

        if df_filtered_classes.empty or df_schools_to_display.empty:
            st.info("Najpierw dobierz filtry tak, aby zostały pasujące klasy.")
        else:
            current_map_state = st.session_state.get("schools_map") or {}
            current_center_point = select_start_point(
                {"center": current_map_state.get("center")},
                allow_center=True,
            )

            geocoding_available = bool(os.environ.get("GOOGLE_MAPS_API_KEY"))
            center_source_label = "Moja lokalizacja / środek mapy"
            source_options = ["Klik na mapie", center_source_label, "Adres"]
            start_source = st.segmented_control(
                "Skąd brać punkt startowy?",
                options=source_options,
                default="Klik na mapie",
                key="fit_start_source",
                help=(
                    "Klik na mapie zapamiętuje pinezkę z zakładki Mapa. "
                    "Moja lokalizacja używa środka aktualnego widoku - "
                    "najpierw możesz kliknąć ikonę lokalizacji na mapie. "
                    "Adres pozwala wpisać punkt startowy ręcznie."
                ),
            )
            # segmented_control zwraca None gdy nic nie wybrane – traktujemy jak domyślny wybór.
            if start_source is None:
                start_source = "Klik na mapie"
            _render_start_point_feedback()

            if start_source == center_source_label:
                col_use, col_clear = st.columns([3, 2], vertical_alignment="bottom")
                with col_use:
                    if st.button(
                        "Użyj aktualnego środka mapy",
                        disabled=current_center_point is None,
                        width="stretch",
                        help=(
                            None
                            if current_center_point is not None
                            else "Otwórz zakładkę Mapa i przesuń widok."
                        ),
                    ):
                        if current_center_point is not None:
                            _remember_start_point(
                                current_center_point,
                                source="moja lokalizacja / środek mapy",
                            )
                            _push_start_point_feedback(
                                "success",
                                "Ustawiono punkt startowy z aktualnego środka mapy.",
                            )
                            st.rerun()
                with col_clear:
                    if st.button(
                        "Wyczyść punkt",
                        key="fit_clear_center",
                        width="stretch",
                    ):
                        _clear_start_point()
                        st.rerun()
            elif start_source == "Adres":
                if not geocoding_available:
                    st.warning(
                        "Wyszukiwanie adresu jest chwilowo niedostępne. "
                        "Użyj kliku na mapie albo środka aktualnego widoku."
                    )
                # Form sprawia, że Enter w polu adresu od razu uruchamia szukanie
                # (bez dodatkowego kroku „Press Enter to apply" + klik „Znajdź").
                with st.form("fit_address_form", clear_on_submit=False, border=False):
                    col_addr, col_btn, col_clear = st.columns(
                        [5, 2, 2], vertical_alignment="bottom"
                    )
                    with col_addr:
                        address_input = st.text_input(
                            "Adres",
                            key="fit_address_input",
                            placeholder="np. ul. Marszałkowska 1, Warszawa",
                            disabled=not geocoding_available,
                        )
                    with col_btn:
                        geocode_clicked = st.form_submit_button(
                            "Znajdź",
                            type="primary",
                            width="stretch",
                            disabled=not geocoding_available,
                        )
                    with col_clear:
                        clear_clicked = st.form_submit_button(
                            "Wyczyść punkt",
                            width="stretch",
                        )
                if clear_clicked:
                    _clear_start_point()
                    st.rerun()
                if geocode_clicked and address_input.strip():
                    normalized = _normalize_address(address_input)
                    with st.spinner("Szukam adresu…"):
                        coords = _geocode_address_cached(normalized)
                    if coords is None:
                        st.error(
                            "Nie udało się znaleźć adresu. Sprawdź pisownię "
                            "lub kliknij punkt na mapie."
                        )
                    else:
                        distance_to_center = float(
                            haversine_km(
                                WARSAW_VALIDATION_CENTER[0],
                                WARSAW_VALIDATION_CENTER[1],
                                coords[0],
                                coords[1],
                            )
                        )
                        if distance_to_center > WARSAW_VALIDATION_RADIUS_KM:
                            _push_start_point_feedback(
                                "warning",
                                "Adres wygląda na spoza obszaru Warszawy "
                                f"(~{distance_to_center:.0f} km od centrum). "
                                "Sprawdź pisownię lub potwierdź wynik.",
                            )
                        _remember_start_point(
                            coords,
                            source="adres",
                            label=address_input.strip(),
                        )
                        _push_start_point_feedback(
                            "success",
                            f"Znaleziono: {_format_start_point(coords[0], coords[1])}",
                        )
                        st.rerun()
            else:  # Klik na mapie
                col_clear, _ = st.columns([2, 5])
                with col_clear:
                    if st.button(
                        "Wyczyść punkt",
                        key="fit_clear_clicked",
                        width="stretch",
                    ):
                        _clear_start_point()
                        st.rerun()

            remembered = _get_remembered_start_point()
            if remembered is None:
                if start_source == center_source_label:
                    st.info(
                        "Otwórz zakładkę 🗺️ Mapa, kliknij ikonę lokalizacji albo ustaw "
                        "widok ręcznie, wróć tutaj i kliknij „Użyj aktualnego środka mapy”."
                    )
                elif start_source == "Adres":
                    st.info("Wpisz adres i naciśnij Enter (lub kliknij „Znajdź”).")
                else:
                    st.info("Otwórz zakładkę 🗺️ Mapa i kliknij punkt startowy.")
            else:
                _render_fit_results(
                    remembered=remembered,
                    df_filtered_classes=df_filtered_classes,
                    df_schools_to_display=df_schools_to_display,
                    wanted_subjects_filter=wanted_subjects_filter,
                    selected_year=selected_year,
                    export_filter_entries=export_filter_entries,
                    ranking_max_reference=ranking_max_reference,
                    class_details=df_class_details,
                    school_details=df_school_details,
                    threshold_matches=df_threshold_matches,
                    enable_pzo_details=enable_pzo_details,
                )

    with tab_viz:
        st.subheader("Wizualizacje")
        selected_charts = st.multiselect(
            "Wykresy do pokazania",
            options=list(CHART_OPTIONS.keys()),
            default=CHART_DEFAULT_SELECTION,
            format_func=lambda key: CHART_OPTIONS[key],
            key="viz_selected_charts",
            help="Wybierz wykresy do wygenerowania na podstawie aktualnych filtrów.",
        )

        if not selected_charts:
            st.info("Wybierz przynajmniej jeden wykres z listy powyżej.")

        if "histogram" in selected_charts:
            fig = plots.histogram_threshold_distribution(df_filtered_classes)
            if fig:
                st.pyplot(fig)
                st.caption(
                    "Rozkład minimalnych progów punktowych w klasach. Przerywana linia oznacza średnią wartości."
                )

        if "bar_district" in selected_charts:
            fig = plots.bar_classes_per_district(
                df_filtered_classes, df_schools_to_display
            )
            if fig:
                st.pyplot(fig)
                st.caption(
                    "Liczba klas licealnych w poszczególnych dzielnicach. Dłuższy słupek to więcej klas."
                )

        if "scatter_rank" in selected_charts:
            fig = plots.scatter_rank_vs_threshold(df_schools_to_display)
            if fig:
                st.pyplot(fig)
                st.caption(
                    "Zależność pozycji w rankingu od minimalnego progu punktowego. Linia trendu pokazuje ogólną korelację."
                )

        if "cooccurrence" in selected_charts:
            fig = plots.heatmap_subject_cooccurrence(df_filtered_classes)
            if fig:
                st.pyplot(fig)
                st.caption(
                    "Im intensywniejszy kolor, tym częściej dane przedmioty występują razem."
                )

        if "bubble_commute" in selected_charts:
            fig = plots.bubble_prog_vs_dojazd(df_schools_to_display)
            if fig:
                st.pyplot(fig)
                st.caption(
                    "Czas dojazdu a próg punktowy szkoły. Wielkość bąbelka zależy od miejsca w rankingu, kolor od dzielnicy."
                )


if __name__ == "__main__":
    main()

st.markdown(
    """
    <div style='text-align: right; margin-top: 40px; font-size: 15px;'>
        Trzymam kciuki za wszystkich uczniów klas 8 i ich rodziców. Pozdrawiam, Piotr Szanser
        <a href="https://www.linkedin.com/in/pszanser/" target="_blank" style="text-decoration: none;">
            <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/linkedin/linkedin-original.svg" alt="LinkedIn" style="height: 20px; vertical-align: middle; margin-bottom: 2px;" />
        </a>
    </div>
    """,
    unsafe_allow_html=True,
)
