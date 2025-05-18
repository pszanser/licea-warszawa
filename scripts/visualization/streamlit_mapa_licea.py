import streamlit as st

# Ustawienie konfiguracji strony musi być pierwszym poleceniem Streamlit
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

# Dodaj katalog 'scripts' do sys.path, aby umożliwić importy z generate_map.py i innych modułów
scripts_dir = Path(__file__).resolve().parent.parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

# Import funkcji z generate_map.py
from visualization.generate_map import (
    RESULTS_DIR, DATA_PATTERN, WARSAW_CENTER_COORDS,
    get_latest_xls_file, load_school_data, load_classes_data,
    get_subjects_from_dataframe, apply_filters_to_classes,
    aggregate_filtered_class_data, add_school_markers_to_map
)
from visualization import plots

def create_schools_map_streamlit(
    df_schools_to_display: pd.DataFrame,
    class_count_per_school: dict,
    filtered_class_details_per_school: dict,
    school_summary_from_filtered: dict,
    show_heatmap: bool = False
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
            school_summary_from_filtered=school_summary_from_filtered
        )

    if show_heatmap and not df_schools_to_display.empty:
        heat_data = df_schools_to_display[["SzkolaLat", "SzkolaLon"]].values.tolist()
        HeatMap(heat_data, name="HeatMap").add_to(m)
    return m

def main():
    st.title("🏫 Mapa szkół średnich - Warszawa i okolice (2025)")
    st.markdown("""
    Aplikacja umożliwia interaktywne przeglądanie szkół średnich w Warszawie i okolicach oraz filtrowanie ich według różnych kryteriów.
    """)
    
    latest_excel_file = get_latest_xls_file(RESULTS_DIR, DATA_PATTERN)
    if not latest_excel_file:
        st.error("Nie można wygenerować mapy bez pliku danych.")
        return

    df_schools_raw = load_school_data(latest_excel_file)
    df_classes_raw = load_classes_data(latest_excel_file)

    if df_schools_raw is None or df_classes_raw is None:
        st.error("Nie udało się wczytać danych szkół lub klas. Mapa nie zostanie wygenerowana.")
        return
    
    st.write(f"Załadowano dane z pliku: **{latest_excel_file.name}**")
    
    available_subjects = get_subjects_from_dataframe(df_classes_raw)
    
    with st.sidebar:
        st.header("Filtry")

        st.subheader("Typ szkoły")
        school_type_options = ["liceum", "technikum", "branżowa"]
        selected_school_types = st.multiselect(
            "Wybierz typ szkoły:",
            school_type_options
        )

        st.subheader("Ranking Perspektyw 2025")
        use_ranking_filter = st.checkbox("Filtruj według pozycji w rankingu liceów", value=False)
        max_ranking_poz_filter = None
        if use_ranking_filter:
            max_ranking_positions = [10, 20, 30, 40, 50, 100]
            max_ranking_poz_filter = st.selectbox(
                "Pokaż licea z TOP:",
                max_ranking_positions,
                index=2
            )
        
        st.subheader("Filtr przedmiotów rozszerzonych")
        st.markdown("**Poszukiwane rozszerzenia** (klasa musi je mieć)")
        wanted_subjects_filter = st.multiselect(
            "Wybierz poszukiwane przedmioty:",
            available_subjects,
            default=[]
        )
        
        st.markdown("**Unikane rozszerzenia** (klasa nie może ich mieć)")
        avoided_subjects_filter = st.multiselect(
            "Wybierz unikane przedmioty:",
            available_subjects,
            default=[]
        )
        
        st.subheader("Progi punktowe szkoły")
        # checkbox, domyślnie False – filtr wyłączony
        use_points_filter = st.checkbox("Filtruj według progów punktowych", value=False)
        if use_points_filter:
            min_pts = df_classes_raw["Prog_min_szkola"].min() \
                if "Prog_min_szkola" in df_classes_raw.columns and not df_classes_raw["Prog_min_szkola"].empty else 100.0
            max_pts_raw = df_classes_raw["Prog_min_szkola"].max() \
                if "Prog_min_szkola" in df_classes_raw.columns and not df_classes_raw["Prog_min_szkola"].empty else 200.0
            default_max = min(max_pts_raw, 300.0)

            points_range = st.slider(
                "Zakres progów minimalnych:",
                min_value=min_pts,
                max_value=300.0,
                value=(min_pts, default_max),
                step=1.0
            )
            min_class_points_filter, max_class_points_filter = points_range
        else:
            # filtr nieaktywny – nie przekazujemy ograniczeń
            min_class_points_filter, max_class_points_filter = None, None

        st.markdown("---")

        show_heatmap = st.checkbox("Pokaż mapę cieplną szkół", value=False)
        
        st.subheader("Wykresy")
        show_histogram = st.checkbox("Rozkład progów punktowych", value=True)
        show_bar_district = st.checkbox("Liczba klas w dzielnicach", value=True)
        show_scatter_rank = st.checkbox("Ranking vs próg punktowy", value=True)
        
    # Filtrowanie po typie szkoły; brak wyboru oznacza wszystkie typy
    if selected_school_types:
        df_classes_by_type = df_classes_raw[df_classes_raw["TypSzkoly"].isin(selected_school_types)]
        df_schools_by_type = df_schools_raw[df_schools_raw["TypSzkoly"].isin(selected_school_types)]
    else:
        df_classes_by_type = df_classes_raw
        df_schools_by_type = df_schools_raw

    df_filtered_classes = apply_filters_to_classes(
        df_classes_by_type,
        wanted_subjects=wanted_subjects_filter,
        avoided_subjects=avoided_subjects_filter,
        max_ranking_poz=max_ranking_poz_filter,
        min_class_points=min_class_points_filter,
        max_class_points=max_class_points_filter,
        report_warning_callback=st.warning
    )

    any_filters_active = any([
        wanted_subjects_filter,
        avoided_subjects_filter,
        max_ranking_poz_filter is not None,
        min_class_points_filter is not None,
        max_class_points_filter is not None,
        len(selected_school_types) != len(school_type_options)
    ])

    if df_filtered_classes.empty and any_filters_active:
        st.warning("Żadne klasy nie spełniają podanych kryteriów filtrowania.")
    elif df_filtered_classes.empty and not df_classes_raw.empty:
         st.warning("Brak klas w danych wejściowych lub wszystkie zostały odfiltrowane.")


    df_schools_to_display, count_filtered_classes, \
    detailed_filtered_classes_info, school_summary_from_filtered = \
        aggregate_filtered_class_data(df_filtered_classes, df_schools_by_type, any_filters_active)
    
    filter_entries = []
    if selected_school_types:
        filter_entries.append(("Typ szkoły", ", ".join(selected_school_types)))
    if wanted_subjects_filter:
        filter_entries.append(("Rozszerzenia - poszukiwane", ", ".join(wanted_subjects_filter)))
    if avoided_subjects_filter:
        filter_entries.append(("Rozszerzenia - unikane", ", ".join(avoided_subjects_filter)))
    if max_ranking_poz_filter is not None:
        filter_entries.append(("Ranking TOP", max_ranking_poz_filter))
    if min_class_points_filter is not None:
        filter_entries.append(("Minimalny próg punktowy klasy", min_class_points_filter))
    if max_class_points_filter is not None:
        filter_entries.append(("Maksymalny próg punktowy klasy", max_class_points_filter))

    filters_info_html = ""
    if filter_entries:
        active_filters_list = [f"<b>{label}:</b> {value}" for label, value in filter_entries]
        filters_info_html = "<br>".join(active_filters_list)
        st.markdown(
            f"""
            <div style='background-color:#fff3e0; border:2px solid #d32f2f; border-radius:8px; padding:12px; margin-bottom:10px; font-size:16px;'>
                <span style='color:#d32f2f; font-size:18px;'><b>Zastosowane filtry:</b></span><br>
                {filters_info_html}
            </div>
            """,
            unsafe_allow_html=True
        )

    map_object = create_schools_map_streamlit(
        df_schools_to_display=df_schools_to_display,
        class_count_per_school=count_filtered_classes,
        filtered_class_details_per_school=detailed_filtered_classes_info,
        school_summary_from_filtered=school_summary_from_filtered,
        show_heatmap=show_heatmap
    )

    tab_map, tab_viz = st.tabs(["🗺️Mapa", "📊Wizualizacje"])

    with tab_map:
        if not df_schools_to_display.empty:
            total_schools = len(df_schools_raw)
            total_classes = len(df_classes_raw)
            matching_schools = len(df_schools_to_display)
            matching_classes = sum(count_filtered_classes.values()) if count_filtered_classes else 0

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("**Szkoły**", f"{matching_schools} / {total_schools}")
            with col2:
                st.metric("**Klasy**", f"{matching_classes} / {total_classes}")
            with col3:
                avg_points = None
                if not df_filtered_classes.empty:
                    serie = df_filtered_classes.apply(
                        lambda r: r["Prog_min_klasa"] if pd.notna(r["Prog_min_klasa"]) else r["Prog_min_szkola"],
                        axis=1,
                    )
                    avg_points = serie.mean()

                if avg_points is not None:
                    st.metric("**Średni próg (pasujące klasy)**", f"{avg_points:.1f}")
                else:
                    st.metric("**Średni próg (pasujące klasy)**", "N/A")

        st.subheader("Mapa szkół")
        st_folium(map_object, width=None, height=600, returned_objects=[])

        if not df_filtered_classes.empty:
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                df_filtered_classes.to_excel(writer, index=False, sheet_name="Klasy")
                if filter_entries:
                    filters_df = pd.DataFrame(filter_entries, columns=["Filtr", "Wartość"])
                    filters_df.to_excel(writer, index=False, sheet_name="Parametry")
            buf.seek(0)
            st.download_button(
                label="📥Pobierz dane klas (Excel)",
                data=buf,
                file_name="moje_klasy.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        if not df_schools_to_display.empty:
            with st.expander("Pokaż listę pasujących szkół", expanded=False):
                schools_summary_list = []
                for _, school_row in df_schools_to_display.iterrows():
                    szk_id = school_row["SzkolaIdentyfikator"]
                    class_count = count_filtered_classes.get(szk_id, 0)

                    min_threshold_from_filtered_classes = None
                    if szk_id in school_summary_from_filtered and 'Prog_min_szkola' in school_summary_from_filtered[szk_id]:
                        min_threshold_from_filtered_classes = school_summary_from_filtered[szk_id]['Prog_min_szkola']
                    elif szk_id in detailed_filtered_classes_info:
                        thresholds = [
                            class_info.get("min_pkt_klasy")
                            for class_info in detailed_filtered_classes_info[szk_id]
                            if class_info.get("min_pkt_klasy") is not None
                        ]
                        if thresholds:
                            min_threshold_from_filtered_classes = min(thresholds)

                    display_ranking = school_row.get("RankingPoz", "-")
                    if pd.notna(display_ranking) and display_ranking != "-":
                        display_ranking = int(display_ranking) if display_ranking == display_ranking // 1 else display_ranking

                    schools_summary_list.append({
                        "Nazwa szkoły": school_row["NazwaSzkoly"],
                        "Dzielnica": school_row["Dzielnica"],
                        "Ranking": display_ranking,
                        "Liczba pasujących klas": class_count,
                        "Min. próg pkt. (z pasujących klas)": min_threshold_from_filtered_classes if pd.notna(min_threshold_from_filtered_classes) else "-",
                    })

                schools_summary_df = pd.DataFrame(schools_summary_list)
                if "Min. próg pkt. (z pasujących klas)" in schools_summary_df.columns:
                    schools_summary_df["Min. próg pkt. (z pasujących klas)"] = schools_summary_df["Min. próg pkt. (z pasujących klas)"].apply(
                        lambda x: int(x) if pd.notna(x) and isinstance(x, numbers.Number) and x == x // 1 else (f"{x:.1f}" if pd.notna(x) and isinstance(x, numbers.Number) else (x if isinstance(x, str) else "-"))
                    )

                if "Min. próg pkt. (z pasujących klas)" in schools_summary_df.columns:
                    schools_summary_df["Min. próg pkt. (z pasujących klas)"] = schools_summary_df["Min. próg pkt. (z pasujących klas)"].astype(str)
                if "Ranking" in schools_summary_df.columns:
                    schools_summary_df["Ranking"] = schools_summary_df["Ranking"].astype(str)

                st.dataframe(schools_summary_df, use_container_width=True)

    with tab_viz:
        if show_histogram:
            fig = plots.histogram_threshold_distribution(df_filtered_classes)
            if fig:
                st.pyplot(fig)

        if show_bar_district:
            fig = plots.bar_classes_per_district(df_filtered_classes, df_schools_to_display)
            if fig:
                st.pyplot(fig)

        if show_scatter_rank:
            fig = plots.scatter_rank_vs_threshold(df_schools_to_display)
            if fig:
                st.pyplot(fig)

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
    unsafe_allow_html=True
)
