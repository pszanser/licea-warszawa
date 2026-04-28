import streamlit as st

st.set_page_config(
    page_title="Mapa szkół średnich - Warszawa i okolice",
    page_icon="🏫",
    layout="wide",
)

import sys
from pathlib import Path
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
    "ranking_filter": "Filtruj według pozycji w rankingu liceów",
    "ranking_top": "Pokaż licea z TOP:",
    "school_names": "Wybierz szkoły do wyświetlenia:",
    "class_types": "Wybierz typy oddziałów:",
    "wanted_subjects": "Wybierz poszukiwane przedmioty:",
    "avoided_subjects": "Wybierz unikane przedmioty:",
    "points_filter": "Filtruj według progów punktowych",
    "points_range": "Zakres progów minimalnych:",
    "show_heatmap": "Pokaż mapę cieplną szkół",
    "histogram": "Rozkład progów punktowych",
    "bar_district": "Liczba klas w dzielnicach",
    "scatter_rank": "Ranking vs próg punktowy",
    "cooccurrence": "Współwystępowanie rozszerzeń",
    "bubble_commute": "Czas dojazdu vs próg (bąbelkowy)",
}

FILTER_HELPS = {
    "school_type": "Ogranicz listę do wybranego typu, np. liceum",
    "ranking_filter": "Filtr używa najnowszego dostępnego rankingu",
    "ranking_top": "Tylko licea z pierwszych pozycji najnowszego rankingu",
    "school_names": "Filtrowanie konkretnych szkół wg ich nazw",
    "class_types": "np. ogólny [O] lub dwujęzyczny [D]/[DW]",
    "wanted_subjects": "Klasa musi je oferować",
    "avoided_subjects": "Klasa nie może ich mieć",
    "points_filter": "Włącz, by określić minimalne progi",
    "points_range": "Wybierz dolny i górny próg",
    "show_heatmap": "Zobacz zagęszczenie placówek",
    "histogram": "Histogram progów w klasach",
    "bar_district": "Porównanie dzielnic",
    "scatter_rank": "Zależność progu od rankingu",
    "cooccurrence": "Które rozszerzenia występują razem",
    "bubble_commute": "Próg szkoły a czas dojazdu",
}

FILTER_DEFAULTS = {
    "school_type": [],
    "ranking_filter": False,
    "school_names": [],
    "class_types": [],
    "wanted_subjects": [],
    "avoided_subjects": [],
    "points_filter": False,
    "show_heatmap": False,
    "histogram": True,
    "bar_district": True,
    "scatter_rank": True,
    "cooccurrence": False,
    "bubble_commute": False,
    # Uwaga: ranking_top i points_range nie są tutaj,
    # ponieważ ich istnienie w session_state jest warunkowe
    # i są obsługiwane przez 'del' podczas resetu,
    # aby widgety mogły użyć swoich parametrów 'index'/'value'.
}

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
)
from visualization import plots
from analysis.score import (
    add_distance_from_point,
    score_personalized_classes,
    select_start_point,
    shortlist_schools_by_distance,
)

FIT_DISPLAY_COLUMNS = {
    "FitScore": "Dopasowanie",
    "RankingScore": "Ranking pkt",
    "AdmissionScore": "Próg pkt",
    "DistanceScore": "Bliskość pkt",
    "ProfileScore": "Profil pkt",
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
}
FIT_CLICKED_START_POINT_KEY = "fit_clicked_start_point"
FIT_CENTER_START_POINT_KEY = "fit_center_start_point"
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
    "PrzedmiotyRozszerzone",
    "Dlaczego",
]


def _remember_start_point(key: str, point: tuple[float, float]) -> None:
    st.session_state[key] = (float(point[0]), float(point[1]))


def _get_remembered_start_point(key: str) -> tuple[float, float] | None:
    value = st.session_state.get(key)
    if not isinstance(value, (tuple, list)) or len(value) != 2:
        return None
    try:
        return float(value[0]), float(value[1])
    except (TypeError, ValueError):
        return None


def _format_start_point(point: tuple[float, float]) -> str:
    return f"{point[0]:.5f}, {point[1]:.5f}"


def _summarize_best_schools_for_display(fit_results: pd.DataFrame) -> pd.DataFrame:
    """Buduje tabelę szkół bez zależności od świeżo przeładowanego modułu score."""
    if fit_results.empty:
        return fit_results.iloc[0:0].copy()

    counts = (
        fit_results.groupby("SzkolaIdentyfikator")
        .size()
        .rename("Liczba pasujących klas")
        .reset_index()
    )
    best_schools = (
        fit_results.sort_values("FitScore", ascending=False, na_position="last")
        .groupby("SzkolaIdentyfikator", as_index=False)
        .first()
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
):
    """
    Tworzy i zwraca mapę Folium z lokalizacjami szkół, korzystając z add_school_markers_to_map.
    """
    m = folium.Map(location=WARSAW_CENTER_COORDS, zoom_start=11)
    Fullscreen().add_to(m)
    LocateControl().add_to(m)

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
        )

    if show_heatmap and not df_schools_to_display.empty:
        heat_data = df_schools_to_display[["SzkolaLat", "SzkolaLon"]].values.tolist()
        HeatMap(heat_data, name="HeatMap").add_to(m)
    return m


@st.cache_data
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


@st.cache_data
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


def main():
    st.title("🏫 Mapa szkół średnich - Warszawa i okolice")
    st.markdown(
        """
    Aplikacja umożliwia interaktywne przeglądanie szkół średnich w Warszawie i okolicach oraz filtrowanie ich według różnych kryteriów.
    """
    )

    # Initialize session state for filters if not already set
    # Używamy globalnego FILTER_DEFAULTS
    for key, value in FILTER_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = value

    latest_excel_file = get_app_or_latest_xls_file(RESULTS_DIR)
    if not latest_excel_file:
        st.error("Nie można wygenerować mapy bez pliku danych.")
        return

    available_years = get_available_years(latest_excel_file)
    default_year = get_default_year(latest_excel_file, available_years)
    if (
        "selected_year" not in st.session_state
        or st.session_state["selected_year"] not in available_years
    ):
        st.session_state["selected_year"] = default_year
    default_index = available_years.index(st.session_state["selected_year"])
    with st.sidebar:
        st.header("Dane")
        selected_year = st.selectbox(
            "Rok danych:",
            available_years,
            index=default_index,
            key="selected_year",
            help="Domyślnie pokazywany jest najnowszy kompletny rok danych.",
        )

    metadata = load_metadata(latest_excel_file, selected_year)
    quality = load_quality(latest_excel_file, selected_year)
    meta_row = metadata.iloc[0].to_dict() if not metadata.empty else {}
    status_label = meta_row.get("status_label") or "dane historyczne"
    threshold_label = meta_row.get("threshold_label")

    # Dane wczytujemy z cache'em zależnym od czasu modyfikacji pliku.
    data_version = latest_excel_file.stat().st_mtime_ns
    df_schools_raw, df_classes_raw = load_all_data(
        latest_excel_file, selected_year, data_version
    )

    if df_schools_raw is None or df_classes_raw is None:
        st.error(
            "Nie udało się wczytać danych szkół lub klas. Mapa nie zostanie wygenerowana."
        )
        return
    ranking_year = get_filter_ranking_year(df_schools_raw, selected_year)

    # prezentujemy nazwę tylko przy lokalnym uruchomieniu
    # (w przypadku uruchomienia w chmurze Streamlit nazwa pliku zawiera "_SL")
    if "_SL" not in latest_excel_file.name:
        st.write(f"Załadowano dane z pliku: **{latest_excel_file.name}**")
    st.info(f"Rok danych: **{selected_year}** | status: **{status_label}**")
    if not quality.empty:
        q = quality.iloc[0]
        st.caption(
            "Kontrola danych: "
            f"szkoły {int(q.get('schools_count', 0))}, "
            f"klasy/wiersze {int(q.get('classes_count', 0))}, "
            f"progi klasowe w {int(q.get('classes_with_threshold', 0))} wierszach, "
            f"progi szkolne w {int(q.get('classes_with_school_threshold', 0))} wierszach."
        )

    available_subjects = get_subjects_from_dataframe(df_classes_raw)
    available_class_types = (
        sorted(df_classes_raw["TypOddzialu"].dropna().unique())
        if "TypOddzialu" in df_classes_raw.columns
        else []
    )

    with st.sidebar:
        st.header("Filtry")

        if st.button("Resetuj filtry"):
            # Używamy globalnego FILTER_DEFAULTS
            # Iterujemy po kluczach z FILTER_LABELS, ponieważ zawiera wszystkie klucze filtrów
            for key_to_clear in FILTER_LABELS.keys():
                if key_to_clear in st.session_state:
                    if key_to_clear in FILTER_DEFAULTS:
                        st.session_state[key_to_clear] = FILTER_DEFAULTS[key_to_clear]
                    # Specjalna obsługa dla kluczy, które nie są w FILTER_DEFAULTS,
                    # ale są kontrolowane przez inne widgety (np. checkbox)
                    # i powinny zostać usunięte, aby widgety użyły swoich domyślnych wartości.
                    elif key_to_clear in ["ranking_top", "points_range"]:
                        del st.session_state[key_to_clear]
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
        use_ranking_filter = st.checkbox(
            FILTER_LABELS["ranking_filter"],
            key="ranking_filter",
            help=FILTER_HELPS["ranking_filter"],
        )
        max_ranking_poz_filter = None
        if use_ranking_filter:
            max_ranking_positions = [10, 20, 30, 40, 50, 75, 100]
            max_ranking_poz_filter = st.selectbox(
                FILTER_LABELS["ranking_top"],
                max_ranking_positions,
                index=2,
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
        # checkbox, domyślnie False – filtr wyłączony
        use_points_filter = st.checkbox(
            FILTER_LABELS["points_filter"],
            key="points_filter",
            help=FILTER_HELPS["points_filter"],
        )
        if use_points_filter:
            min_pts = (
                df_classes_raw["Prog_min_szkola"].min()
                if "Prog_min_szkola" in df_classes_raw.columns
                and not df_classes_raw["Prog_min_szkola"].empty
                else 100.0
            )
            max_pts_raw = (
                df_classes_raw["Prog_min_szkola"].max()
                if "Prog_min_szkola" in df_classes_raw.columns
                and not df_classes_raw["Prog_min_szkola"].empty
                else 200.0
            )
            default_max = min(max_pts_raw, 300.0)

            points_range = st.slider(
                FILTER_LABELS["points_range"],
                min_value=min_pts,
                max_value=300.0,
                value=(min_pts, default_max),
                step=1.0,
                key="points_range",
                help=FILTER_HELPS["points_range"],
            )
            min_class_points_filter, max_class_points_filter = points_range
        else:
            # filtr nieaktywny – nie przekazujemy ograniczeń
            min_class_points_filter, max_class_points_filter = None, None

        st.markdown("---")

        show_heatmap = st.checkbox(
            FILTER_LABELS["show_heatmap"],
            key="show_heatmap",
            help=FILTER_HELPS["show_heatmap"],
        )

        st.subheader("Wykresy")
        show_histogram = st.checkbox(
            FILTER_LABELS["histogram"],
            key="histogram",
            help=FILTER_HELPS["histogram"],
        )
        show_bar_district = st.checkbox(
            FILTER_LABELS["bar_district"],
            key="bar_district",
            help=FILTER_HELPS["bar_district"],
        )
        show_scatter_rank = st.checkbox(
            FILTER_LABELS["scatter_rank"],
            key="scatter_rank",
            help=FILTER_HELPS["scatter_rank"],
        )
        show_cooccurrence = st.checkbox(
            FILTER_LABELS["cooccurrence"],
            key="cooccurrence",
            help=FILTER_HELPS["cooccurrence"],
        )
        show_bubble_commute = st.checkbox(
            FILTER_LABELS["bubble_commute"],
            key="bubble_commute",
            help=FILTER_HELPS["bubble_commute"],
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

    filters_info_html = ""
    if filter_entries:
        active_filters_list = [
            f"<b>{label}:</b> {value}" for label, value in filter_entries
        ]
        filters_info_html = "<br>".join(active_filters_list)
        st.markdown(
            f"""
            <div style='background-color:#fff3e0; border:2px solid #d32f2f; border-radius:8px; padding:12px; margin-bottom:10px; font-size:16px;'>
                <span style='color:#d32f2f; font-size:18px;'><b>Zastosowane filtry:</b></span><br>
                {filters_info_html}
            </div>
            """,
            unsafe_allow_html=True,
        )

    map_object = create_schools_map_streamlit(
        df_schools_to_display=df_schools_to_display,
        class_count_per_school=count_filtered_classes,
        filtered_class_details_per_school=detailed_filtered_classes_info,
        school_summary_from_filtered=school_summary_from_filtered,
        show_heatmap=show_heatmap,
    )

    if not df_schools_to_display.empty:
        total_schools = len(df_schools_raw)
        total_classes = len(df_classes_raw)
        matching_schools = len(df_schools_to_display)
        matching_classes = (
            sum(count_filtered_classes.values()) if count_filtered_classes else 0
        )

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("**Szkoły**", f"{matching_schools} / {total_schools}")
        with col2:
            st.metric("**Klasy**", f"{matching_classes} / {total_classes}")
        with col3:
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
                avg_points = serie.mean()

            if avg_points is not None:
                st.metric("**Średni próg (pasujące klasy)**", f"{avg_points:.1f}")
            else:
                st.metric("**Średni próg (pasujące klasy)**", "N/A")

    tab_map, tab_fit, tab_viz = st.tabs(
        ["🗺️Mapa", "🎯Moje dopasowanie", "📊Wizualizacje"]
    )

    with tab_map:
        st.subheader("Mapa szkół")
        map_state = st_folium(
            map_object,
            width=None,
            height=600,
            returned_objects=["last_clicked", "center", "zoom"],
            key="schools_map",
        )
        clicked_start_point = select_start_point(map_state, allow_center=False)
        if clicked_start_point is not None:
            _remember_start_point(FIT_CLICKED_START_POINT_KEY, clicked_start_point)

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
                label="📥Pobierz dane klas (Excel)",
                data=buf,
                file_name=f"moje_klasy_{selected_year}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
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
            "Pierwsza wersja używa odległości w linii prostej od wybranego punktu. "
            "Nie jest to jeszcze dokładny czas dojazdu."
        )

        if df_filtered_classes.empty or df_schools_to_display.empty:
            st.info("Najpierw dobierz filtry tak, aby zostały pasujące klasy.")
        else:
            start_source = st.radio(
                "Punkt startowy",
                ["Kliknięty punkt na mapie", "Środek aktualnego widoku mapy"],
                horizontal=True,
            )
            allow_center = start_source == "Środek aktualnego widoku mapy"
            current_center_point = select_start_point(
                {"center": (map_state or {}).get("center")},
                allow_center=True,
            )
            if allow_center:
                center_col, clear_col = st.columns([2, 1])
                with center_col:
                    if st.button(
                        "Użyj aktualnego środka mapy",
                        disabled=current_center_point is None,
                    ):
                        if current_center_point is not None:
                            _remember_start_point(
                                FIT_CENTER_START_POINT_KEY, current_center_point
                            )
                            st.rerun()
                with clear_col:
                    if st.button("Wyczyść punkt", key="clear_center_start_point"):
                        st.session_state.pop(FIT_CENTER_START_POINT_KEY, None)
                        st.rerun()
                start_point = _get_remembered_start_point(FIT_CENTER_START_POINT_KEY)
            else:
                clear_col, _ = st.columns([1, 3])
                with clear_col:
                    if st.button("Wyczyść punkt", key="clear_clicked_start_point"):
                        st.session_state.pop(FIT_CLICKED_START_POINT_KEY, None)
                        st.rerun()
                start_point = _get_remembered_start_point(FIT_CLICKED_START_POINT_KEY)

            if start_point is None:
                if allow_center:
                    st.info(
                        "Przejdź do mapy, ustaw widok lub użyj kontrolki lokalizacji, "
                        "a potem wróć tutaj i kliknij „Użyj aktualnego środka mapy”."
                    )
                else:
                    st.info("Przejdź do mapy i kliknij punkt startowy.")
            else:
                start_lat, start_lon = start_point
                st.caption(
                    f"Zapamiętany punkt startowy: {_format_start_point(start_point)}. "
                    "Odległość liczona jest lokalnie po współrzędnych szkół."
                )

                settings_col, weights_col = st.columns([1, 2])
                with settings_col:
                    predicted_points = st.number_input(
                        "Przewidywana liczba punktów",
                        min_value=0.0,
                        max_value=300.0,
                        value=170.0,
                        step=1.0,
                    )
                    max_distance_km = st.select_slider(
                        "Maksymalna odległość km",
                        options=[3, 5, 8, 12, 15, 20, 25],
                        value=8,
                        help=(
                            "Twardy filtr: szkoły dalej od punktu startowego "
                            "nie wchodzą do dopasowania."
                        ),
                    )
                    shortlist_limit = st.slider(
                        "Liczba najbliższych szkół",
                        min_value=10,
                        max_value=100,
                        value=40,
                        step=5,
                        help=(
                            "Dodatkowy limit po zastosowaniu maksymalnej odległości."
                        ),
                    )

                with weights_col:
                    st.markdown("**Ważność kryteriów**")
                    w_col1, w_col2, w_col3, w_col4 = st.columns(4)
                    with w_col1:
                        weight_ranking = st.slider(
                            "Ranking",
                            0,
                            10,
                            6,
                            key="fit_weight_ranking",
                            help="Im wyżej, tym mocniej liczy się pozycja szkoły w rankingu.",
                        )
                    with w_col2:
                        weight_admission = st.slider(
                            "Próg",
                            0,
                            10,
                            8,
                            key="fit_weight_admission",
                            help="Im wyżej, tym mocniej liczy się margines między punktami ucznia a progiem klasy.",
                        )
                    with w_col3:
                        weight_distance = st.slider(
                            "Bliskość",
                            0,
                            10,
                            7,
                            key="fit_weight_distance",
                            help="Im wyżej, tym mocniej liczy się odległość w linii prostej od punktu startowego.",
                        )
                    with w_col4:
                        weight_profile = st.slider(
                            "Profil",
                            0,
                            10,
                            0,
                            key="fit_weight_profile_disabled",
                            disabled=True,
                            help="Profil jest już uwzględniany przez filtr rozszerzeń po lewej.",
                        )

                weights = {
                    "ranking": weight_ranking,
                    "admission": weight_admission,
                    "distance": weight_distance,
                    "profile": weight_profile,
                }
                weight_labels = {
                    "ranking": "ranking",
                    "admission": "próg",
                    "distance": "bliskość",
                    "profile": "profil",
                }
                active_weights = {
                    key: value
                    for key, value in weights.items()
                    if value > 0 and key != "profile"
                }
                active_weight_sum = sum(active_weights.values())
                if active_weight_sum <= 0:
                    st.warning("Ustaw co najmniej jedną wagę większą od zera.")
                else:
                    weight_parts = [
                        f"{weight_labels[key]} {value / active_weight_sum:.0%}"
                        for key, value in active_weights.items()
                    ]
                    st.caption("Aktywne wagi w tym widoku: " + ", ".join(weight_parts))
                    if wanted_subjects_filter:
                        st.caption(
                            "Profil jest traktowany jako filtr: "
                            + ", ".join(wanted_subjects_filter)
                        )
                    else:
                        st.caption(
                            "Profil jest wyłączony, bo nie wybrano poszukiwanych "
                            "rozszerzeń w filtrach głównych."
                        )
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
                    else:
                        shortlisted_ids = shortlisted_schools[
                            "SzkolaIdentyfikator"
                        ].tolist()
                        distance_cols = shortlisted_schools[
                            ["SzkolaIdentyfikator", "OdlegloscKm"]
                        ].drop_duplicates("SzkolaIdentyfikator")
                        classes_for_fit = df_filtered_classes[
                            df_filtered_classes["SzkolaIdentyfikator"].isin(
                                shortlisted_ids
                            )
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
                        )

                        st.metric(
                            "Szkoły w shortliście",
                            f"{len(shortlisted_schools)} / {len(df_schools_to_display)}",
                        )
                        st.caption(
                            f"Uwzględniono szkoły do {max_distance_km} km od punktu "
                            f"startowego, maksymalnie {shortlist_limit} najbliższych."
                        )

                        top_results = fit_results.head(50).copy()
                        display_cols = [
                            col
                            for col in FIT_DISPLAY_COLUMNS
                            if col in top_results.columns
                        ]
                        display_df = top_results[display_cols].rename(
                            columns=FIT_DISPLAY_COLUMNS
                        )
                        for col in ["Ranking", "Próg", "Margines pkt"]:
                            if col in display_df.columns:
                                display_df[col] = pd.to_numeric(
                                    display_df[col], errors="coerce"
                                ).round(0)
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
                                display_df[col] = pd.to_numeric(
                                    display_df[col], errors="coerce"
                                ).round(1)

                        st.markdown("**Najlepsze klasy dla mnie**")
                        st.dataframe(display_df, width="stretch", hide_index=True)

                        school_summary = pd.DataFrame()
                        if not fit_results.empty:
                            school_summary = _summarize_best_schools_for_display(
                                fit_results
                            ).rename(
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

                            with st.expander("Najlepsze szkoły", expanded=False):
                                st.dataframe(
                                    school_summary.head(20),
                                    width="stretch",
                                    hide_index=True,
                                )

                        export_params = export_filter_entries + [
                            (
                                "Punkt startowy",
                                f"{start_lat:.6f}, {start_lon:.6f}",
                            ),
                            ("Źródło punktu", start_source),
                            ("Przewidywane punkty", predicted_points),
                            ("Maksymalna odległość km", max_distance_km),
                            ("Limit shortlisty szkół", shortlist_limit),
                            ("Waga ranking", weight_ranking),
                            ("Waga próg", weight_admission),
                            ("Waga bliskość", weight_distance),
                            ("Waga profil", weight_profile),
                            (
                                "Rozszerzenia dla profilu",
                                ", ".join(wanted_subjects_filter) or "brak",
                            ),
                        ]
                        fit_buf = io.BytesIO()
                        with pd.ExcelWriter(fit_buf, engine="openpyxl") as writer:
                            fit_results.to_excel(
                                writer, index=False, sheet_name="Klasy"
                            )
                            if not school_summary.empty:
                                school_summary.to_excel(
                                    writer, index=False, sheet_name="Szkoly"
                                )
                            shortlisted_schools.to_excel(
                                writer, index=False, sheet_name="Szkoly_shortlista"
                            )
                            pd.DataFrame(
                                export_params, columns=["Parametr", "Wartość"]
                            ).to_excel(writer, index=False, sheet_name="Parametry")
                        fit_buf.seek(0)
                        st.download_button(
                            label="📥Pobierz moje dopasowanie (Excel)",
                            data=fit_buf,
                            file_name=f"moje_dopasowanie_{selected_year}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        )

    with tab_viz:
        if show_histogram:
            fig = plots.histogram_threshold_distribution(df_filtered_classes)
            if fig:
                st.pyplot(fig)
                st.caption(
                    "Rozkład minimalnych progów punktowych w klasach. Przerywana linia oznacza średnią wartości."
                )

        if show_bar_district:
            fig = plots.bar_classes_per_district(
                df_filtered_classes, df_schools_to_display
            )
            if fig:
                st.pyplot(fig)
                st.caption(
                    "Liczba klas licealnych w poszczególnych dzielnicach. Dłuższy słupek to więcej klas."
                )

        if show_scatter_rank:
            fig = plots.scatter_rank_vs_threshold(df_schools_to_display)
            if fig:
                st.pyplot(fig)
                st.caption(
                    "Zależność pozycji w rankingu od minimalnego progu punktowego. Linia trendu pokazuje ogólną korelację."
                )

        if show_cooccurrence:
            fig = plots.heatmap_subject_cooccurrence(df_filtered_classes)
            if fig:
                st.pyplot(fig)
                st.caption(
                    "Im intensywniejszy kolor, tym częściej dane przedmioty występują razem."
                )

        if show_bubble_commute:
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
