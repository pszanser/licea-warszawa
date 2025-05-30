"""Skrypt zapisujący wykresy do plików w katalogu `results`."""

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
PATTERN = "LO_Warszawa_2025_*.xlsx"
OUT_DIR = RESULTS


def save_fig(fig, filename, dpi: int = 150):
    """Zapisuje wykres do OUT_DIR i zamyka go."""
    out = OUT_DIR / filename
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=dpi)
    plt.close(fig)
    print(f"✔ zapisano {out.name}")


def get_latest_xls(results_dir: Path, pattern: str) -> Path:
    files = list(results_dir.glob(pattern))
    if not files:
        raise FileNotFoundError(
            f"Nie znaleziono plików pasujących do wzorca {pattern} w katalogu {results_dir}"
        )
    return max(files, key=os.path.getmtime)


def load_excel_data(xls_path: Path):
    excel_file_handle = pd.ExcelFile(xls_path)
    df_klasy = pd.read_excel(excel_file_handle, "klasy")
    df_klasy["RankingPoz"] = pd.to_numeric(df_klasy["RankingPoz"], errors="coerce")
    try:
        df_szkoly = pd.read_excel(excel_file_handle, "szkoly")
    except Exception as e:
        print(
            f"Ostrzeżenie: Nie udało się wczytać arkusza 'szkoly' z pliku {xls_path}. {e}"
        )
        print(
            "Heatmapy zależne od danych z arkusza 'szkoly' mogą nie zostać wygenerowane."
        )
        df_szkoly = None
    return df_klasy, df_szkoly


def ensure_subject_columns(df: pd.DataFrame):
    for subj_col in SUBJECTS:
        if subj_col not in df.columns:
            print(
                f"Ostrzeżenie: Brak kolumny '{subj_col}' w danych 'klasy'. Może to wpłynąć na generowanie profili."
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


def main():
    try:
        xls_path = get_latest_xls(RESULTS, PATTERN)
        print(f"Używam pliku: {xls_path}")
        df_klasy, df_szkoly = load_excel_data(xls_path)

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

        print("Gotowe – PNG-i w katalogu results/")
    except Exception as e:
        print(f"Błąd podczas generowania wizualizacji: {e}")


if __name__ == "__main__":
    main()
