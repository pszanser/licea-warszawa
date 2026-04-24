"""Skrypt zapisujący wykresy do plików w katalogu `results`."""

import argparse
from pathlib import Path
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sys

# Import funkcji generujących wykresy
from plots import (
    heat_pairs,
    lollipop_diff_top30,
    heatmap_profiles_by_district,
    heatmap_subjects_by_district,
    bubble_prog_vs_dojazd,
    heatmap_rank_commute,
    stripplot_commute_district,
    histogram_threshold_distribution,
    bar_classes_per_district,
    heatmap_subject_cooccurrence,
    scatter_rank_vs_threshold,
    scatter_rank_vs_distance,
    scatter_density_vs_rank,
    scatter_hidden_gems,
)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.constants import ALL_SUBJECTS as SUBJECTS

ROOT = Path(__file__).resolve().parent.parent.parent
RESULTS = ROOT / "results"
APP_DATA_FILE = RESULTS / "app" / "licea_warszawa.xlsx"
LEGACY_PATTERN = "LO_Warszawa_2025_*.xlsx"
OUT_DIR = RESULTS


def save_fig(fig, filename, dpi: int = 150):
    """Zapisuje wykres do OUT_DIR i zamyka go."""
    out = OUT_DIR / filename
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=dpi)
    plt.close(fig)
    print(f"Zapisano {out.name}")


def get_latest_xls(results_dir: Path, pattern: str) -> Path:
    files = list(results_dir.glob(pattern))
    if not files:
        raise FileNotFoundError(
            f"Nie znaleziono plików pasujących do wzorca {pattern} w katalogu {results_dir}"
        )
    return max(files, key=os.path.getmtime)


def get_input_xls() -> Path:
    if APP_DATA_FILE.exists():
        return APP_DATA_FILE
    return get_latest_xls(RESULTS, LEGACY_PATTERN)


def select_default_year(excel_file_handle: pd.ExcelFile) -> int | None:
    if "metadata" not in excel_file_handle.sheet_names:
        return None
    metadata = pd.read_excel(excel_file_handle, "metadata")
    if "year" not in metadata.columns:
        return None
    if "data_status" in metadata.columns:
        full_years = metadata[metadata["data_status"].eq("full")]["year"].dropna()
        if not full_years.empty:
            return int(full_years.max())
    years = metadata["year"].dropna()
    return int(years.max()) if not years.empty else None


def load_excel_data(xls_path: Path, year: int | None = None):
    excel_file_handle = pd.ExcelFile(xls_path)
    selected_year = year if year is not None else select_default_year(excel_file_handle)
    classes_sheet = "classes" if "classes" in excel_file_handle.sheet_names else "klasy"
    schools_sheet = (
        "schools" if "schools" in excel_file_handle.sheet_names else "szkoly"
    )

    df_klasy = pd.read_excel(excel_file_handle, classes_sheet)
    if selected_year is not None and "year" in df_klasy.columns:
        df_klasy = df_klasy[df_klasy["year"].eq(selected_year)].copy()
    df_klasy["RankingPoz"] = pd.to_numeric(df_klasy["RankingPoz"], errors="coerce")
    try:
        df_szkoly = pd.read_excel(excel_file_handle, schools_sheet)
        if selected_year is not None and "year" in df_szkoly.columns:
            df_szkoly = df_szkoly[df_szkoly["year"].eq(selected_year)].copy()
    except Exception as e:
        print(
            f"Ostrzezenie: Nie udalo sie wczytac arkusza szkol z pliku {xls_path}. {e}"
        )
        print("Heatmapy zalezne od danych szkol moga nie zostac wygenerowane.")
        df_szkoly = None
    return df_klasy, df_szkoly, selected_year


def ensure_subject_columns(df: pd.DataFrame):
    for subj_col in SUBJECTS:
        if subj_col not in df.columns:
            print(
                f"Ostrzezenie: Brak kolumny '{subj_col}' w danych klas. Moze to wplynac na generowanie profili."
            )


def add_profile_column(df: pd.DataFrame):
    if "Profil" in df.columns:
        return

    subj_cols = [s for s in SUBJECTS if s in df.columns]
    codes = pd.Index(subj_cols).str.slice(0, 3)
    df["Profil"] = (
        df[subj_cols]
        .astype(int)
        .dot(np.eye(len(subj_cols), dtype=int))
        .astype(bool)
        .dot(codes + "-")
        .str.rstrip("-")
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generuje wykresy PNG dla danych szkol."
    )
    parser.add_argument(
        "--year", type=int, default=None, help="Rok danych do wizualizacji."
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None):
    args = parse_args(argv)
    try:
        xls_path = get_input_xls()
        print(f"Uzywam pliku: {xls_path}")
        df_klasy, df_szkoly, selected_year = load_excel_data(xls_path, args.year)
        if selected_year is not None:
            print(f"Rok danych wizualizacji: {selected_year}")

        ensure_subject_columns(df_klasy)
        add_profile_column(df_klasy)

        for tag, filt in [
            ("all", None),
            ("top30", df_klasy["RankingPoz"] <= 30),
            ("top10", df_klasy["RankingPoz"] <= 10),
        ]:
            data = df_klasy if filt is None else df_klasy[filt]
            fig = heat_pairs(data, tag)
            if fig:
                save_fig(fig, f"heatmap_pairs_{tag.lower()}.png")

        fig = lollipop_diff_top30(df_klasy)
        if fig:
            save_fig(fig, "lollipop_diff_top30_vs_all.png")

        fig = histogram_threshold_distribution(df_klasy)
        if fig:
            save_fig(fig, "hist_threshold_distribution.png")

        fig = bar_classes_per_district(df_klasy, df_szkoly)
        if fig:
            save_fig(fig, "bar_classes_per_district.png")

        fig = heatmap_subject_cooccurrence(df_klasy)
        if fig:
            save_fig(fig, "heatmap_subject_cooccurrence.png")

        fig = scatter_rank_vs_threshold(df_szkoly)
        if fig:
            save_fig(fig, "scatter_rank_vs_threshold.png")

        profile_figs = heatmap_profiles_by_district(df_klasy, df_szkoly)
        for name, fig in (profile_figs or {}).items():
            save_fig(fig, f"heatmap_profiles_{name.lower()}.png")

        fig = heatmap_subjects_by_district(df_klasy, df_szkoly)
        if fig:
            save_fig(fig, "heatmap_subjects_by_district.png")

        fig = bubble_prog_vs_dojazd(df_szkoly)
        if fig:
            save_fig(fig, "bubble_prog_vs_dojazd.png")

        fig = heatmap_rank_commute(df_szkoly)
        if fig:
            save_fig(fig, "heat_rank_vs_commute.png")

        fig = stripplot_commute_district(df_szkoly)
        if fig:
            save_fig(fig, "strip_commute_district.png")

        fig = scatter_rank_vs_distance(df_szkoly)
        if fig:
            save_fig(fig, "scatter_rank_vs_distance.png")

        fig = scatter_density_vs_rank(df_szkoly)
        if fig:
            save_fig(fig, "scatter_density_vs_rank.png")

        fig = scatter_hidden_gems(df_szkoly)
        if fig:
            save_fig(fig, "scatter_hidden_gems.png")

        print("Gotowe - PNG-i w katalogu results/")
    except Exception as e:
        print(f"Blad podczas generowania wizualizacji: {e}")


if __name__ == "__main__":
    main()
