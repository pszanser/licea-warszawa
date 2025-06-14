import streamlit as st

st.set_page_config(
    page_title="Mapa szkół średnich - Warszawa i okolice (2025)",
    page_icon="🏫",
    layout="wide",
)

import sys
from pathlib import Path
import pandas as pd
import folium
from folium.plugins import Fullscreen, LocateControl, HeatMap
from streamlit_folium import st_folium
import numbers
import io
# Zapewniamy, że katalog `scripts` (z plikiem geo.py) jest w sys.path
_scripts_dir = Path(__file__).resolve().parent.parent
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

import importlib
geo = importlib.import_module("geo")

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
    "ranking_filter": "Włącz, jeśli liczy się miejsce w rankingu",
    "ranking_top": "Tylko licea z pierwszych pozycji",
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
    DATA_PATTERN,
    WARSAW_CENTER_COORDS,
    get_latest_xls_file,
    load_school_data,
    load_classes_data,
    get_subjects_from_dataframe,
    apply_filters_to_classes,
    aggregate_filtered_class_data,
    add_school_markers_to_map,
)
from visualization import plots


def create_schools_map_streamlit(
    df_schools_to_display: pd.DataFrame,
    class_count_per_school: dict,
    filtered_class_details_per_school: dict,
    school_summary_from_filtered: dict,
    show_heatmap: bool = False,
    user_marker_location: tuple[float, float] | None = None,
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

    # Dodaj pinezkę użytkownika, jeśli jest lokalizacja
    if user_marker_location is not None:
        folium.Marker(
            location=user_marker_location,
            icon=folium.Icon(color="red", icon="user", prefix="fa"),
            popup="Twój punkt odniesienia"
        ).add_to(m)

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


@st.cache_data
def load_all_data(excel_file: Path) -> tuple[pd.DataFrame | None, pd.DataFrame | None]:
    """Wczytuje dane szkół i klas z pliku Excel tylko raz.

    Użycie dekoratora ``st.cache_data`` sprawia, że podczas kolejnych
    uruchomień skryptu Streamlit ponowne wczytywanie pliku z dysku nie
    będzie konieczne, dopóki ścieżka ``excel_file`` się nie zmieni.
    """
    df_schools = load_school_data(excel_file)
    df_classes = load_classes_data(excel_file)
    return df_schools, df_classes


def main():
    st.title("🏫 Mapa szkół średnich - Warszawa i okolice (2025)")
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

    latest_excel_file = get_latest_xls_file(RESULTS_DIR, DATA_PATTERN)
    if not latest_excel_file:
        st.error("Nie można wygenerować mapy bez pliku danych.")
        return

    # Dane wczytujemy tylko raz dzięki cache'u Streamlit.
    df_schools_raw, df_classes_raw = load_all_data(latest_excel_file)

    if df_schools_raw is None or df_classes_raw is None:
        st.error(
            "Nie udało się wczytać danych szkół lub klas. Mapa nie zostanie wygenerowana."
        )
        return

    # prezentujemy nazwę tylko przy lokalnym uruchomieniu
    # (w przypadku uruchomienia w chmurze Streamlit nazwa pliku zawiera "_SL")
    if "_SL" not in latest_excel_file.name:
        st.write(f"Załadowano dane z pliku: **{latest_excel_file.name}**")

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

        st.subheader("Ranking Perspektyw 2025")
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

        st.subheader("Progi punktowe szkoły")
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
        filter_entries.append(("Ranking TOP", max_ranking_poz_filter))
    if min_class_points_filter is not None:
        filter_entries.append(
            ("Minimalny próg punktowy klasy", min_class_points_filter)
        )
    if max_class_points_filter is not None:
        filter_entries.append(
            ("Maksymalny próg punktowy klasy", max_class_points_filter)
        )

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
        )    # Sprawdź, czy jest lokalizacja użytkownika do zaznaczenia pinezką
    user_marker_location = None
    if "_user_location" in st.session_state:
        loc = st.session_state["_user_location"]
        if loc and "lat" in loc and "lng" in loc:
            user_marker_location = (loc["lat"], loc["lng"])

    map_object = create_schools_map_streamlit(
        df_schools_to_display=df_schools_to_display,
        class_count_per_school=count_filtered_classes,
        filtered_class_details_per_school=detailed_filtered_classes_info,
        school_summary_from_filtered=school_summary_from_filtered,
        show_heatmap=show_heatmap,
        user_marker_location=user_marker_location,
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

    tab_map, tab_viz = st.tabs(["🗺️Mapa", "📊Wizualizacje"])

    with tab_map:
        st.subheader("Mapa szkół")
        
        # Wyświetl mapę i pobierz dane o interakcji
        loc_data = st_folium(
            map_object, width=None, height=600, 
            returned_objects=["last_clicked", "last_object_clicked", "location"]
        )

        # Przechowuj ostatnią znaną lokalizację użytkownika w session_state
        def get_new_user_location(loc_data):
            if not loc_data:
                return None
            if loc_data.get("last_clicked"):
                return loc_data["last_clicked"]
            if loc_data.get("location") and isinstance(loc_data["location"], dict):
                return loc_data["location"]
            if loc_data.get("last_object_clicked"):
                return loc_data["last_object_clicked"]
            return None

        user_location = get_new_user_location(loc_data)
        prev_location = st.session_state.get("_user_location")        # Przeliczaj tylko jeśli lokalizacja się zmieniła
        if user_location and "lat" in user_location and "lng" in user_location:
            if (
                not prev_location
                or user_location["lat"] != prev_location.get("lat")
                or user_location["lng"] != prev_location.get("lng")
            ):
                st.session_state["_user_location"] = user_location
                lat = user_location["lat"]
                lon = user_location["lng"]
                
                # Przeliczy najbliższe szkoły (do wyświetlenia listy)
                nearest_df = geo.find_nearest_schools(
                    (
                        df_schools_to_display
                        if not df_schools_to_display.empty
                        else df_schools_raw
                    ),
                    lat,
                    lon,
                    top_n=10,
                )
                st.session_state["_nearest_schools"] = nearest_df
                
                # Przeliczy odległości dla wszystkich szkół i zapisz w session_state
                all_schools_with_distance = df_schools_raw.dropna(subset=["SzkolaLat", "SzkolaLon"]).copy()
                if not all_schools_with_distance.empty:
                    all_schools_with_distance["OdlegloscOdUzytkownika_km"] = geo.haversine_distance(
                        lat, lon,
                        all_schools_with_distance["SzkolaLat"].to_numpy(),
                        all_schools_with_distance["SzkolaLon"].to_numpy()
                    )
                    st.session_state["_schools_with_distances"] = all_schools_with_distance
                  # Wymuś odświeżenie, żeby mapa się przerysowała z pinezką od razu
                st.rerun()

        # Wyświetl listę najbliższych szkół jeśli jest zapamiętana
        nearest_df = st.session_state.get("_nearest_schools")
        if nearest_df is not None:
            # Dodaj kolumnę z numerem porządkowym i ukryj indeks
            display_df = nearest_df.reset_index(drop=True)
            display_df.index = range(1, len(display_df) + 1)
            display_df.index.name = "Lp."
            
            st.write("Najbliższe szkoły:")
            st.caption("*Odległości podane w linii prostej (dystans rzeczywisty może być większy)")
            st.dataframe(
                display_df[["NazwaSzkoly", "AdresSzkoly", "Dzielnica", "DistanceKm"]]
                .rename(columns={"DistanceKm": "Dystans [km]"}), 
                use_container_width=True
            )

        if not df_filtered_classes.empty:
            buf = io.BytesIO()
            
            # Przygotuj dane klas z odległością od użytkownika
            df_classes_export = df_filtered_classes.copy()
            schools_with_distances = st.session_state.get("_schools_with_distances")
            if schools_with_distances is not None:
                # Join z danymi o odległościach
                distance_data = schools_with_distances[["SzkolaIdentyfikator", "OdlegloscOdUzytkownika_km"]].copy()
                df_classes_export = df_classes_export.merge(
                    distance_data, 
                    on="SzkolaIdentyfikator", 
                    how="left"
                )
            
            # Przygotuj dane szkół z odległością od użytkownika
            df_schools_export = df_schools_to_display.copy()
            if schools_with_distances is not None:
                distance_data = schools_with_distances[["SzkolaIdentyfikator", "OdlegloscOdUzytkownika_km"]].copy()
                df_schools_export = df_schools_export.merge(
                    distance_data, 
                    on="SzkolaIdentyfikator", 
                    how="left"
                )
            
            with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                df_classes_export.to_excel(writer, index=False, sheet_name="Klasy")
                df_schools_export.to_excel(writer, index=False, sheet_name="Szkoły")
                if filter_entries:
                    filters_df = pd.DataFrame(
                        filter_entries, columns=["Filtr", "Wartość"]
                    )
                    filters_df.to_excel(writer, index=False, sheet_name="Parametry")
            buf.seek(0)
            st.download_button(
                label="📥Pobierz dane klas i szkół (Excel)",
                data=buf,
                file_name="moje_szkoly_i_klasy.xlsx",                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        if not df_schools_to_display.empty:
            with st.expander("Pokaż listę pasujących szkół", expanded=False):
                schools_summary_list = []
                schools_with_distances = st.session_state.get("_schools_with_distances")
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
                            int(display_ranking)                            if display_ranking == display_ranking // 1
                            else float(display_ranking)
                        )
                    else:
                        display_ranking = None

                    # Pobierz odległość od użytkownika, jeśli dostępna
                    distance_from_user = None
                    if schools_with_distances is not None:
                        distance_row = schools_with_distances[
                            schools_with_distances["SzkolaIdentyfikator"] == szk_id
                        ]
                        if not distance_row.empty:
                            distance_from_user = distance_row.iloc[0]["OdlegloscOdUzytkownika_km"]

                    school_dict = {
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
                    
                    # Dodaj odległość tylko jeśli jest dostępna
                    if distance_from_user is not None:
                        school_dict["Odległość od użytkownika [km]"] = round(distance_from_user, 2)
                    
                    schools_summary_list.append(school_dict)

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

                st.dataframe(schools_summary_df, use_container_width=True)

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
