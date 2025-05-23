import reflex as rx
import pandas as pd
from pathlib import Path

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
)
from visualization.streamlit_mapa_licea import create_schools_map_streamlit

latest_excel_file = get_latest_xls_file(RESULTS_DIR, DATA_PATTERN)
if latest_excel_file:
    df_schools_raw = load_school_data(latest_excel_file)
    df_classes_raw = load_classes_data(latest_excel_file)
else:
    df_schools_raw = None
    df_classes_raw = None

available_subjects = (
    get_subjects_from_dataframe(df_classes_raw) if df_classes_raw is not None else []
)

class MapState(rx.State):
    school_types: list[str] = []
    ranking_top: int | None = None
    selected_school_names: list[str] = []
    wanted_subjects: list[str] = []
    avoided_subjects: list[str] = []
    use_points_filter: bool = False
    points_range: tuple[float, float] = (0.0, 300.0)
    show_heatmap: bool = False
    map_html: str = ""

    def apply_filters(self):
        if df_schools_raw is None or df_classes_raw is None:
            self.map_html = "Brak danych do wyświetlenia."
            return

        df_classes = df_classes_raw
        df_schools = df_schools_raw

        if self.school_types:
            df_classes = df_classes[df_classes["TypSzkoly"].isin(self.school_types)]
            df_schools = df_schools[df_schools["TypSzkoly"].isin(self.school_types)]

        if self.selected_school_names:
            df_classes = df_classes[df_classes["NazwaSzkoly"].isin(self.selected_school_names)]
            df_schools = df_schools[df_schools["NazwaSzkoly"].isin(self.selected_school_names)]

        min_pt = self.points_range[0] if self.use_points_filter else None
        max_pt = self.points_range[1] if self.use_points_filter else None

        df_filtered_classes = apply_filters_to_classes(
            df_classes_raw=df_classes,
            wanted_subjects=self.wanted_subjects,
            avoided_subjects=self.avoided_subjects,
            max_ranking_poz=self.ranking_top,
            min_class_points=min_pt,
            max_class_points=max_pt,
            report_warning_callback=lambda m: None,
        )

        any_filters = any([
            self.wanted_subjects,
            self.avoided_subjects,
            self.ranking_top is not None,
            min_pt is not None,
            max_pt is not None,
            bool(self.school_types),
            bool(self.selected_school_names),
        ])

        (
            df_schools_to_display,
            count_filtered_classes,
            detailed_filtered_classes_info,
            school_summary_from_filtered,
        ) = aggregate_filtered_class_data(
            df_filtered_classes,
            df_schools,
            any_filters,
        )

        map_obj = create_schools_map_streamlit(
            df_schools_to_display=df_schools_to_display,
            class_count_per_school=count_filtered_classes,
            filtered_class_details_per_school=detailed_filtered_classes_info,
            school_summary_from_filtered=school_summary_from_filtered,
            show_heatmap=self.show_heatmap,
        )
        self.map_html = map_obj._repr_html_()


def map_page() -> rx.Component:
    if df_schools_raw is None:
        return rx.text("Brak danych do wyświetlenia.")

    school_name_options = sorted(df_schools_raw["NazwaSzkoly"].unique())
    return rx.vstack(
        rx.heading("Mapa szkół średnich - Reflex"),
        rx.box(
            rx.checkbox_group(
                options=["liceum", "technikum", "branżowa"],
                value=MapState.school_types,
                on_change=MapState.set_school_types,
            ),
            rx.text("Filtruj typ szkoły"),
        ),
        rx.box(
            rx.select(
                ["", "10", "20", "30", "40", "50", "100"],
                value=str(MapState.ranking_top or ""),
                on_change=lambda v: MapState.set_ranking_top(int(v) if v else None),
            ),
            rx.text("Ranking Perspektyw TOP"),
        ),
        rx.box(
            rx.select_multi(
                school_name_options,
                value=MapState.selected_school_names,
                on_change=MapState.set_selected_school_names,
            ),
            rx.text("Wybierz szkoły"),
        ),
        rx.box(
            rx.select_multi(
                available_subjects,
                value=MapState.wanted_subjects,
                on_change=MapState.set_wanted_subjects,
            ),
            rx.text("Poszukiwane rozszerzenia"),
        ),
        rx.box(
            rx.select_multi(
                available_subjects,
                value=MapState.avoided_subjects,
                on_change=MapState.set_avoided_subjects,
            ),
            rx.text("Unikane rozszerzenia"),
        ),
        rx.checkbox(
            "Filtruj według progów punktowych",
            value=MapState.use_points_filter,
            on_change=MapState.set_use_points_filter,
        ),
        rx.slider(
            min_=0,
            max_=300,
            value=list(MapState.points_range),
            on_change=lambda v: MapState.set_points_range((float(v[0]), float(v[1]))),
        ),
        rx.checkbox(
            "Pokaż mapę cieplną",
            value=MapState.show_heatmap,
            on_change=MapState.set_show_heatmap,
        ),
        rx.button("Zastosuj filtry", on_click=MapState.apply_filters),
        rx.box(rx.html(MapState.map_html), width="100%"),
    )

app = rx.App()
app.add_page(map_page)
app.compile()

