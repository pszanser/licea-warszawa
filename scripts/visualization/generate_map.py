import folium
from folium.plugins import MarkerCluster, Fullscreen, LocateControl, HeatMap
import os
from pathlib import Path
import pandas as pd
from typing import Callable, Any

ROOT = Path(__file__).resolve().parent.parent.parent
RESULTS_DIR = ROOT / "results"
DATA_PATTERN = "LO_Warszawa_2025_*.xlsx"
MAP_OUTPUT_FILENAME = "mapa_licea_warszawa.html"
WARSAW_CENTER_COORDS = [52.2297, 21.0122] # Współrzędne centrum Warszawy

def get_latest_xls_file(directory: Path, pattern: str) -> Path | None:
    """
    Znajduje najnowszy plik Excel w danym katalogu pasujący do wzorca.
    """
    files = list(directory.glob(pattern))
    if not files:
        print(f"Nie znaleziono plików pasujących do wzorca '{pattern}' w '{directory}'.")
        return None
    latest_file = max(files, key=os.path.getmtime)
    print(f"Używam pliku danych: {latest_file}")
    return latest_file

def load_school_data(excel_path: Path) -> pd.DataFrame | None:
    """
    Wczytuje dane szkół z arkusza 'szkoly' w podanym pliku Excel.
    Filtruje szkoły bez współrzędnych i sprawdza obecność wymaganych kolumn.
    """
    try:
        df = pd.read_excel(excel_path, sheet_name="szkoly")
        
        required_cols = ["SzkolaLat", "SzkolaLon", "NazwaSzkoly", "AdresSzkoly", "Dzielnica", "url"]
        
        for col in required_cols:
            if col not in df.columns:
                print(f"Brak wymaganej kolumny '{col}' w arkuszu 'szkoly'. Nie można wygenerować mapy.")
                return None
        
        df_filtered = df.dropna(subset=["SzkolaLat", "SzkolaLon"]).copy()
        
        if df_filtered.empty:
            print("Brak szkół z poprawnymi współrzędnymi w pliku. Mapa nie zostanie wygenerowana.")
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

def load_classes_data(excel_path: Path) -> pd.DataFrame | None:
    """
    Wczytuje dane klas z arkusza 'klasy' w podanym pliku Excel.
    """
    try:
        df = pd.read_excel(excel_path, sheet_name="klasy")
        return df
    except Exception as e:
        print(f"Błąd podczas wczytywania arkusza 'klasy': {e}")
        return None

def get_subjects_from_dataframe(df: pd.DataFrame) -> list[str]:
    """Wyciąga listę przedmiotów rozszerzonych z kolumn DataFrame"""
    potential_subjects = [col for col in df.columns if col not in [
        'SzkolaIdentyfikator', 'OddzialIdentyfikator', 'OddzialNazwa', 'UrlGrupy',
        'Prog_min_klasa', 'Prog_min_szkola', 'Prog_max_szkola', 'RankingPoz'
    ]]
    subject_cols = []
    for col in potential_subjects:
        if df[col].dtype in ['int64', 'float64'] and set(df[col].dropna().unique()).issubset({0, 1}):
            subject_cols.append(col)
    return sorted(subject_cols)

def apply_filters_to_classes(
    df_classes_raw: pd.DataFrame,
    wanted_subjects: list[str] | None,
    avoided_subjects: list[str] | None,
    max_ranking_poz: int | None,
    min_class_points: float | None,
    max_class_points: float | None,
    report_warning_callback: Callable[[str], Any] = print
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
                report_warning_callback(f"Kolumna wymaganego przedmiotu '{subject}' nie znaleziona w danych.")
    
    if avoided_subjects:
        for subject in avoided_subjects:
            if subject in df_filtered.columns:
                df_filtered = df_filtered[df_filtered[subject] != 1]
            else:
                report_warning_callback(f"Kolumna unikanego przedmiotu '{subject}' nie znaleziona w danych.")

    if max_ranking_poz is not None:
        if "RankingPoz" in df_filtered.columns:
            df_filtered = df_filtered[df_filtered["RankingPoz"] <= max_ranking_poz]
        else:
            report_warning_callback("Kolumna 'RankingPoz' nie znaleziona w danych do filtrowania rankingu.")

    if min_class_points is not None:
        if "Prog_min_szkola" in df_filtered.columns:
            df_filtered = df_filtered[df_filtered["Prog_min_szkola"] >= min_class_points]
        else:
            report_warning_callback("Kolumna 'Prog_min_szkola' nie znaleziona w danych do filtrowania progu min.")
    
    if max_class_points is not None:
        if "Prog_min_szkola" in df_filtered.columns: # Filtrujemy na podstawie progu minimalnego klasy
            df_filtered = df_filtered[df_filtered["Prog_min_szkola"] <= max_class_points]
        else:
            report_warning_callback("Kolumna 'Prog_min_szkola' nie znaleziona w danych do filtrowania progu max.")
            
    return df_filtered

def aggregate_filtered_class_data(
    df_filtered_classes: pd.DataFrame,
    df_schools_raw: pd.DataFrame,
    any_filters_applied: bool
) -> tuple[pd.DataFrame, dict, dict, dict]:
    """
    Agreguje dane po filtrowaniu klas, przygotowując dane do wyświetlenia na mapie.
    """
    if df_filtered_classes.empty and any_filters_applied:
        # print("Żadne klasy nie spełniają podanych kryteriów filtrowania.")
        df_schools_to_display = pd.DataFrame(columns=df_schools_raw.columns)
        count_filtered_classes = {}
        detailed_filtered_classes_info = {}
        school_summary_from_filtered = {}
    elif df_filtered_classes.empty: # No filters applied, but no classes data
        # print("Brak klas w danych wejściowych.")
        df_schools_to_display = pd.DataFrame(columns=df_schools_raw.columns)
        count_filtered_classes = {}
        detailed_filtered_classes_info = {}
        school_summary_from_filtered = {}
    else:
        schools_with_matching_classes_ids = df_filtered_classes["SzkolaIdentyfikator"].unique()
        df_schools_to_display = df_schools_raw[df_schools_raw["SzkolaIdentyfikator"].isin(schools_with_matching_classes_ids)].copy()

        count_filtered_classes = df_filtered_classes.groupby("SzkolaIdentyfikator").size().to_dict()
        
        detailed_filtered_classes_info = {}
        for szk_id, group in df_filtered_classes.groupby("SzkolaIdentyfikator"):
            details = []
            for _, class_row in group.iterrows():
                details.append({
                    "nazwa": class_row.get("OddzialNazwa"),
                    "url": class_row.get("UrlGrupy"),
                    "min_pkt_klasy": class_row.get("Prog_min_klasa"),
                })
            detailed_filtered_classes_info[szk_id] = details

        school_summary_from_filtered = {}
        # Ensure all expected columns for aggregation are present
        required_agg_cols = ["SzkolaIdentyfikator", "Prog_min_szkola", "Prog_max_szkola", "RankingPoz"]
        if all(col in df_filtered_classes.columns for col in required_agg_cols):
            agg_dict = {
                "Prog_min_szkola": "min", # Min próg szkoły z pasujących klas
                "Prog_max_szkola": "max", # Max próg szkoły (faktycznie klasy) z pasujących klas
                "RankingPoz": "first"      # Ranking szkoły (jest taki sam dla wszystkich jej klas)
            }
            # Drop rows where any of the aggregation keys might be NaN before grouping
            # to avoid issues with groupby if these columns are not fully populated
            # However, typically SzkolaIdentyfikator should always be present.
            # For Prog_min_szkola, Prog_max_szkola, RankingPoz, they might be NaN for some classes.
            # The aggregation functions (min, max, first) handle NaNs appropriately by default.
            
            grouped_for_summary = df_filtered_classes.groupby("SzkolaIdentyfikator").agg(agg_dict)
            school_summary_from_filtered = grouped_for_summary.to_dict('index')
        else:
            # print("Ostrzeżenie: Brak wszystkich wymaganych kolumn do agregacji podsumowania szkoły z przefiltrowanych klas.")
            # This will result in school_summary_from_filtered remaining empty or partially filled if some columns were present.
            # Fallback can be to use original school data if filtered summary is not possible.
            pass
            
    return df_schools_to_display, count_filtered_classes, detailed_filtered_classes_info, school_summary_from_filtered

def add_school_markers_to_map(
    folium_map_object: folium.Map,
    df_schools_to_display: pd.DataFrame,
    class_count_per_school: dict[str, int],
    filtered_class_details_per_school: dict[str, list[dict]],
    school_summary_from_filtered: dict[str, dict]
) -> None:
    """
    Dodaje markery szkół do obiektu mapy Folium.
    Markery są grupowane w klastry (MarkerCluster) dla lepszej czytelności.
    """
    if df_schools_to_display.empty:
        # print("Brak szkół do wyświetlenia na mapie po zastosowaniu filtrów.") # Handled by caller
        return

    cluster = MarkerCluster()
    cluster.add_to(folium_map_object)

    for _, row in df_schools_to_display.iterrows():
        tooltip_text = f"{row['NazwaSzkoly']} ({row['Dzielnica']})"
        szk_id = row.get("SzkolaIdentyfikator")

        popup_html = f"<b>{row['NazwaSzkoly']}</b><br>"
        nav_url = (
            "https://www.google.com/maps/dir/?api=1&destination="
            f"{row['SzkolaLat']},{row['SzkolaLon']}"
        )
        popup_html += (
            f"Adres: <a href='{nav_url}' target='_blank'>{row['AdresSzkoly']}</a><br>"
        )
        popup_html += f"Dzielnica: {row['Dzielnica']}<br>"

        summary = school_summary_from_filtered.get(szk_id, {})

        # Użyj rankingu z podsumowania przefiltrowanych klas, jeśli dostępne, inaczej z danych ogólnych szkoły
        ranking_poz = summary.get('RankingPoz', row.get('RankingPoz'))
        if pd.notna(ranking_poz):
            display_ranking = int(ranking_poz) if ranking_poz == ranking_poz // 1 else ranking_poz
            popup_html += f"Ranking Perspektywy 2025: {display_ranking}<br>"
        
        # Progi punktowe z przefiltrowanych klas
        min_prog_filtered = summary.get('Prog_min_szkola')
        max_prog_filtered = summary.get('Prog_max_szkola')
        
        if pd.notna(min_prog_filtered) and pd.notna(max_prog_filtered):
            popup_html += f"Przedział pkt. szkoły (dla filtr. klas) 2024: {(min_prog_filtered)}–{(max_prog_filtered)}<br>"
        else:
            # Jeśli brak danych z przefiltrowanych, użyj ogólnych progów szkoły
            min_prog_general = row.get('Prog_min_szkola')
            max_prog_general = row.get('Prog_max_szkola')
            if pd.notna(min_prog_general) and pd.notna(max_prog_general):
                if min_prog_general == max_prog_general: # np. gdy tylko jedna klasa lub wszystkie mają ten sam próg
                    popup_html += f"Próg punktowy szkoły (ogólny) 2024: {(min_prog_general)}<br>"
                else:
                    popup_html += f"Przedział pkt. szkoły (ogólny) 2024: {(min_prog_general)}–{(max_prog_general)}<br>"

        num_matching_classes = class_count_per_school.get(szk_id, 0)
        if num_matching_classes > 0:
            popup_html += f"Liczba klas spełniających kryteria: {num_matching_classes}<br>"

        matching_classes_details = filtered_class_details_per_school.get(szk_id, [])
        if matching_classes_details:
            popup_html += "<u>Pasujące klasy:</u><br>"
            for class_detail in matching_classes_details:
                class_name = class_detail.get("nazwa", "N/A")
                class_url = class_detail.get("url")
                class_min_pkt = class_detail.get("min_pkt_klasy")

                line = "- "
                if pd.notna(class_url):
                    line += f"<a href='{class_url}' target='_blank'>{class_name}</a>"
                else:
                    line += class_name
                
                if pd.notna(class_min_pkt):
                    line += f" (próg: {int(class_min_pkt) if class_min_pkt == class_min_pkt // 1 else class_min_pkt} pkt)"
                popup_html += line + "<br>"
        
        if 'url' in row and pd.notna(row['url']):
            popup_html += f"<a href='{row['url']}' target='_blank'>Zobacz ofertę szkoły (ogólnie)</a>"

        popup_html = f"<div style='font-size:14px; line-height:1.2;'>{popup_html}</div>"

        school_type = str(row.get("TypSzkoly", "").lower())
        color_map = {"liceum": "blue", "technikum": "green", "branżowa": "red"}
        marker_color = color_map.get(school_type, "blue")

        folium.Marker(
            location=[row["SzkolaLat"], row["SzkolaLon"]],
            tooltip=tooltip_text,
            popup=folium.Popup(popup_html, max_width=350),
            icon=folium.Icon(color=marker_color, icon="graduation-cap", prefix="fa")
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
    map_obj.get_root().html.add_child(Element(button_html))

def create_schools_map(
    df_schools_to_display: pd.DataFrame,
    output_path: Path,
    class_count_per_school: dict[str, int],
    filtered_class_details_per_school: dict[str, list[dict]],
    school_summary_from_filtered: dict[str, dict],
    filters_info_html: str = "",
    show_heatmap: bool = False
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
        legend_html = f'''
        <div style="position: fixed; top: 60px; left: 60px; width: 320px; z-index:9999; background-color: white; border:2px solid grey; border-radius:8px; padding: 10px; font-size: 14px; box-shadow: 2px 2px 8px #888;">
            <b>Zastosowane filtry:</b><br>
            {filters_info_html}
        </div>
        '''
        from folium import Element
        m.get_root().html.add_child(Element(legend_html))

    if df_schools_to_display.empty:
        print("Brak szkół do wyświetlenia na mapie po zastosowaniu filtrów.")
        # Save empty map anyway
    else:
         add_school_markers_to_map(
            m,
            df_schools_to_display,
            class_count_per_school,
            filtered_class_details_per_school,
            school_summary_from_filtered
        )

    heat_layer = None
    if show_heatmap and not df_schools_to_display.empty:
        heat_data = df_schools_to_display[["SzkolaLat", "SzkolaLon"]].values.tolist()
        heat_layer = HeatMap(heat_data, name="HeatMap", show=False)
        heat_layer.add_to(m)
        _add_heatmap_toggle(m, heat_layer)
    try:
        m.save(str(output_path))
        print(f"✔ Mapa zapisana jako: {output_path}")
    except Exception as e:
        print(f"Błąd podczas zapisywania mapy: {e}")


def main():
    print("Rozpoczynam generowanie mapy szkół...")
    
    # --- Definicje filtrów (mogą być modyfikowane lub ustawione na None/puste listy) ---
    wanted_subjects = [] # np. ["matematyka"]
    avoided_subjects = [] # np. ["biologia"]
    max_ranking_poz = None   # np. 50
    min_class_points = None  # np. 140.0
    max_class_points = None  # np. 180.0
    enable_heatmap = False
    # --- Koniec sekcji filtrów ---

    latest_excel_file = get_latest_xls_file(RESULTS_DIR, DATA_PATTERN)
    if not latest_excel_file:
        print("Nie można wygenerować mapy bez pliku danych.")
        return

    df_schools_raw = load_school_data(latest_excel_file)
    df_classes_raw = load_classes_data(latest_excel_file)

    if df_schools_raw is None or df_classes_raw is None:
        print("Nie udało się wczytać danych szkół lub klas. Mapa nie zostanie wygenerowana.")
        return

    df_filtered_classes = apply_filters_to_classes(
        df_classes_raw,
        wanted_subjects,
        avoided_subjects,
        max_ranking_poz,
        min_class_points,
        max_class_points,
        report_warning_callback=lambda msg: print(f"Ostrzeżenie: {msg}")
    )
    
    any_filters_applied = any([
        wanted_subjects,
        avoided_subjects,
        max_ranking_poz is not None,
        min_class_points is not None,
        max_class_points is not None
    ])

    if df_filtered_classes.empty and any_filters_applied:
        print("Żadne klasy nie spełniają podanych kryteriów filtrowania.")
    elif df_filtered_classes.empty and not any_filters_applied and not df_classes_raw.empty:
        # This case might mean all classes were filtered out by default logic in apply_filters if any,
        # or df_classes_raw was already empty (handled by initial check).
        # For now, assume it means no classes to display if df_filtered_classes is empty.
        print("Brak klas do przetworzenia (prawdopodobnie wszystkie odfiltrowane lub brak danych).")


    df_schools_to_display, count_filtered_classes, \
    detailed_filtered_classes_info, school_summary_from_filtered = \
        aggregate_filtered_class_data(df_filtered_classes, df_schools_raw, any_filters_applied)

    if df_schools_to_display.empty and any_filters_applied:
        print("Brak szkół do wyświetlenia po zastosowaniu filtrów.")
    elif df_schools_to_display.empty and not df_schools_raw.empty:
         print("Brak szkół do wyświetlenia (żadne nie mają pasujących klas lub brak danych szkół).")


    filters_info_html_str = ""
    if any_filters_applied:
        map_output_file = RESULTS_DIR / MAP_OUTPUT_FILENAME.replace('.html', '_filtered.html')
        if wanted_subjects:
            filters_info_html_str += f"Rozszerzenia - poszukiwane: {', '.join(wanted_subjects)}<br>"
        if avoided_subjects:
            filters_info_html_str += f"Rozszerzenia - unikane: {', '.join(avoided_subjects)}<br>"
        if max_ranking_poz is not None:
            filters_info_html_str += f"Ranking TOP: {max_ranking_poz}<br>"
        if min_class_points is not None:
            filters_info_html_str += f"Minimalny próg punktowy klasy: {min_class_points}<br>"
        if max_class_points is not None:
            filters_info_html_str += f"Maksymalny próg punktowy klasy: {max_class_points}<br>"
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
        show_heatmap=enable_heatmap
    )

if __name__ == "__main__":
    main()
