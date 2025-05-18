"""Funkcje generujące wykresy dla liceów w Warszawie."""

from itertools import combinations
from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import sys

# Pozostałe moduły z projektu
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.constants import ALL_SUBJECTS as SUBJECTS, WARSAW_CENTER_LAT, WARSAW_CENTER_LON

# ---------------------------------------------------------------------------
# Helpery
# ---------------------------------------------------------------------------

def plot_heatmap_with_annotations(matrix, x_labels, y_labels, title, xlabel, ylabel, cmap="YlGnBu", figsize=(10, 6), colorbar_label="Liczba klas"):
    """Tworzy heatmapę z anotacjami i zwraca obiekt Figure."""
    fig, ax = plt.subplots(figsize=figsize)
    im = ax.imshow(matrix, aspect="auto", cmap=cmap)
    ax.set_xticks(range(len(x_labels)))
    ax.set_xticklabels(x_labels, rotation=45, ha="right")
    ax.set_yticks(range(len(y_labels)))
    ax.set_yticklabels(y_labels)
    for i in range(len(y_labels)):
        for j in range(len(x_labels)):
            ax.text(j, i, matrix[i, j],
                    ha="center", va="center",
                    color="w" if matrix[i, j] > matrix.max() * 0.6 else "black",
                    fontsize=8)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    fig.colorbar(im, ax=ax, fraction=0.03, pad=0.04, label=colorbar_label)
    plt.tight_layout()
    return fig

def merge_with_district(df_klasy_param: pd.DataFrame, df_szkoly_param: Optional[pd.DataFrame]) -> pd.DataFrame:
    """Łączy dane klas z dzielnicą na podstawie identyfikatora szkoły."""
    if "Dzielnica" not in df_klasy_param.columns and df_szkoly_param is not None:
        return df_klasy_param.merge(
            df_szkoly_param[["SzkolaIdentyfikator", "Dzielnica"]],
            on="SzkolaIdentyfikator",
            how="left",
        )
    return df_klasy_param.copy()

def get_top_n(series: pd.Series, n: int):
    """Zwraca n najczęstszych elementów w serii."""
    return series.value_counts().head(n).index.tolist()

def get_top_subjects(df: pd.DataFrame, n: int):
    """Zwraca n najpopularniejszych przedmiotów w danych."""
    valid_subject_cols = [subj for subj in SUBJECTS if subj in df.columns]
    if not valid_subject_cols:
        return []
    return df[valid_subject_cols].sum().sort_values(ascending=False).head(n).index.tolist()

# ---------------------------------------------------------------------------
# Wykresy
# ---------------------------------------------------------------------------

def heat_pairs(data: pd.DataFrame, tag: str, top_n_subj: int = 8):
    """Zwraca heatmapę najczęstszych duetów rozszerzeń."""
    top_subj = get_top_subjects(data, top_n_subj)
    if not top_subj or len(top_subj) < 2:
        print(
            f"Brak wystarczających danych (mniej niż 2 popularne przedmioty) do wygenerowania heatmapy duetów ({tag})"
        )
        return None
    mat = pd.DataFrame(0, index=top_subj, columns=top_subj, dtype=int)
    for subj_a, subj_b in combinations(top_subj, 2):
        count = ((data[subj_a] == 1) & (data[subj_b] == 1)).sum()
        mat.loc[subj_a, subj_b] = count
        mat.loc[subj_b, subj_a] = count
    fig, ax = plt.subplots(figsize=(7, 5))
    im = ax.imshow(mat.values, cmap="Reds")
    ax.set_xticks(range(len(top_subj)))
    ax.set_xticklabels(top_subj, rotation=45, ha="right")
    ax.set_yticks(range(len(top_subj)))
    ax.set_yticklabels(top_subj)
    for i in range(len(top_subj)):
        for j in range(len(top_subj)):
            if i == j:
                continue
            v = mat.iat[i, j]
            ax.text(j, i, v, ha="center", va="center",
                    color="white" if v > mat.values.max() * 0.5 else "black",
                    fontsize=8)
    ax.set_title(f"{tag}: duety rozszerzeń")
    fig.colorbar(im, ax=ax, fraction=0.03, pad=0.04, label="Liczba klas")
    plt.tight_layout()
    return fig

def lollipop_diff_top30(df_klasy_param: pd.DataFrame):
    top_profiles = get_top_n(df_klasy_param["Profil"], 10)

    def prof_pct(subset):
        return (
            subset["Profil"].value_counts()
            .reindex(top_profiles).fillna(0) / len(subset) * 100
        )

    pct_all = prof_pct(df_klasy_param)
    pct_30 = prof_pct(df_klasy_param[df_klasy_param["RankingPoz"] <= 30])
    diff = (pct_30 - pct_all).sort_values()

    fig, ax = plt.subplots(figsize=(8, 6))
    y = np.arange(len(diff))
    ax.hlines(y, 0, diff, color="grey", alpha=.4)
    ax.scatter(diff, y, s=100,
               color=["#1b9e77" if d > 0 else "#d95f02" for d in diff])
    ax.set_yticks(y)
    ax.set_yticklabels(diff.index)
    ax.axvline(0, color="black", linewidth=.5)
    ax.set_xlabel("Różnica udziału w TOP-30 vs ALL (p.p.)")
    ax.set_title("Które profile są nad- / niedoreprezentowane w TOP-30?")
    plt.tight_layout()
    return fig

def heatmap_profiles_by_district(df_klasy_param: pd.DataFrame, df_szkoly_param: Optional[pd.DataFrame]):
    if df_szkoly_param is None:
        print("Brak danych z arkusza 'szkoly' – pomijam heatmapy profili wg dzielnic.")
        return None
    df_merged = merge_with_district(df_klasy_param, df_szkoly_param)
    if 'Dzielnica' not in df_merged.columns or df_merged['Dzielnica'].isnull().all():
        print("Ostrzeżenie: Kolumna 'Dzielnica' jest niedostępna lub pusta. Pomijam heatmapy profili wg dzielnic.")
        return None
    groups = {
        'ALL': df_merged,
        'TOP30': df_merged[df_merged['RankingPoz'] <= 30],
        'TOP10': df_merged[df_merged['RankingPoz'] <= 10]
    }
    figs = {}
    for name, sub in groups.items():
        if sub.empty:
            print(f"Brak danych dla grupy '{name}' – pomijam heatmapę profili wg dzielnic dla tej grupy.")
            continue
        top_dz = get_top_n(sub['Dzielnica'], 8)
        top_profiles = get_top_n(sub['Profil'], 10)
        if not top_dz or not top_profiles:
            print(f"Brak wystarczających danych (dzielnice lub profile) dla grupy '{name}' – pomijam heatmapę profili.")
            continue
        pivot_df = pd.crosstab(sub['Dzielnica'], sub['Profil'])
        matrix_df = pivot_df.reindex(index=top_dz, columns=top_profiles).fillna(0).astype(int)
        matrix = matrix_df.values
        figs[name] = plot_heatmap_with_annotations(
            matrix,
            x_labels=top_profiles,
            y_labels=top_dz,
            title=f'{name}: popularność profili wg dzielnic',
            xlabel='Profil (TOP 10)',
            ylabel='Dzielnica (TOP 8)'
        )
    return figs

def heatmap_subjects_by_district(df_klasy_param: pd.DataFrame, df_szkoly_param: Optional[pd.DataFrame]):
    if df_szkoly_param is None:
        print("Brak danych z arkusza 'szkoly' – pomijam heatmapę przedmiotów wg dzielnic.")
        return None
    df_klasy_merged = merge_with_district(df_klasy_param, df_szkoly_param)
    if 'Dzielnica' not in df_klasy_merged.columns or df_klasy_merged['Dzielnica'].isnull().all():
        print("Ostrzeżenie: Kolumna 'Dzielnica' jest niedostępna lub pusta po przetworzeniu. Pomijam heatmapę przedmiotów wg dzielnic.")
        return None
    valid_subject_cols = [subj for subj in SUBJECTS if subj in df_klasy_merged.columns]
    if not valid_subject_cols:
        print("Brak kolumn przedmiotów w danych 'klasy' – pomijam heatmapę przedmiotów wg dzielnic.")
        return None
    top10_subjects = get_top_subjects(df_klasy_merged, 10)
    if df_klasy_merged['Dzielnica'].dropna().empty:
        print("Brak danych o dzielnicach po scaleniu. Pomijam heatmapę przedmiotów wg dzielnic.")
        return None
    top10_districts = get_top_n(df_klasy_merged['Dzielnica'].dropna(), 10)
    if not top10_subjects or not top10_districts:
        print("Brak wystarczających danych (przedmioty lub dzielnice) do wygenerowania heatmapy przedmiotów.")
        return None
    grouped_df = df_klasy_merged.groupby('Dzielnica')[top10_subjects].sum()
    matrix_df = grouped_df.reindex(index=top10_districts, columns=top10_subjects).fillna(0).astype(int)
    matrix = matrix_df.values
    fig = plot_heatmap_with_annotations(
        matrix,
        x_labels=top10_subjects,
        y_labels=top10_districts,
        title='Popularność rozszerzeń przedmiotowych wg dzielnic (Warszawa)',
        xlabel='Rozszerzenie (TOP 10)',
        ylabel='Dzielnica (TOP 10)'
    )
    return fig


def bubble_prog_vs_dojazd(df_szkoly_param: pd.DataFrame):
    if df_szkoly_param is None or df_szkoly_param["CzasDojazdu"].isna().all():
        print("Brak kolumny CzasDojazdu – pomijam bubble-chart.")
        return None
    df = df_szkoly_param.copy()
    df = df[df["CzasDojazdu"].notna() & df["Prog_min_szkola"].notna()]
    if df.empty:
        print("Bubble-chart: brak pełnych danych (próg + dojazd).")
        return None
    size = 1200 / (df["RankingPoz"].fillna(100) + 4)
    dz_color = {d: c for d, c in zip(df["Dzielnica"].unique(), plt.cm.tab20.colors)}
    c = df["Dzielnica"].map(dz_color)
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(df["CzasDojazdu"], df["Prog_min_szkola"],
               s=size, c=c, alpha=.7, edgecolor="k", linewidth=0.5)
    ax.set_xlabel("Czas dojazdu [min]")
    ax.set_ylabel("Próg punktowy 2024")
    ax.set_title("Próg punktowy vs czas dojazdu (rozmiar = ranking)")
    ax.grid(True, alpha=.2)
    plt.tight_layout()
    return fig

def heatmap_rank_commute(df_szkoly_param: pd.DataFrame):
    if df_szkoly_param is None or df_szkoly_param["CzasDojazdu"].isna().all():
        print("Brak CzasDojazdu – pomijam heat-mapę rank × czas.")
        return None
    df = df_szkoly_param.copy()
    bins_t = [0, 20, 30, 40, 50, 60, 1e3]
    bins_r = [0, 10, 20, 30, 40, 50, 80]
    df["T_bin"] = pd.cut(df["CzasDojazdu"], bins_t,
                         labels=["≤20", "21-30", "31-40", "41-50", "51-60", ">60"])
    df["R_bin"] = pd.cut(df["RankingPoz"], bins_r,
                         labels=["1-10", "11-20", "21-30", "31-40", "41-50", "51-80"])
    pivot = pd.crosstab(df["R_bin"], df["T_bin"])
    fig, ax = plt.subplots(figsize=(8, 5))
    im = ax.imshow(pivot.values, cmap="YlOrRd")
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns)
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index)
    for i in range(pivot.shape[0]):
        for j in range(pivot.shape[1]):
            ax.text(j, i, pivot.iat[i, j], ha="center", va="center",
                    color="white" if pivot.iat[i, j] > pivot.values.max()*0.6 else "black",
                    fontsize=8)
    ax.set_xlabel("Czas dojazdu [min]")
    ax.set_ylabel("Pozycja w rankingu")
    ax.set_title("Liczba klas: ranking vs czas dojazdu")
    fig.colorbar(im, ax=ax, fraction=0.03, pad=0.04, label="Liczba klas")
    plt.tight_layout()
    return fig

def stripplot_commute_district(df_szkoly_param: pd.DataFrame):
    if df_szkoly_param is None or df_szkoly_param["CzasDojazdu"].isna().all():
        print("Brak CzasDojazdu – pomijam strip-plot.")
        return None
    df = df_szkoly_param.copy()
    fig, ax = plt.subplots(figsize=(9, 6))
    sns.stripplot(data=df, y="Dzielnica", x="CzasDojazdu",
                  jitter=0.25, size=5, ax=ax, alpha=.8)
    ax.set_xlabel("Czas dojazdu [min]")
    ax.set_ylabel("Dzielnica")
    ax.set_title("Rozrzut czasów dojazdu do liceów")
    plt.tight_layout()
    return fig

def histogram_threshold_distribution(df_klasy_param: pd.DataFrame):
    if "Prog_min_klasa" not in df_klasy_param.columns and "Prog_min_szkola" not in df_klasy_param.columns:
        print("Brak kolumny z progami – pomijam histogram progów punktowych.")
        return None
    series = df_klasy_param.get("Prog_min_klasa")
    if series is None:
        series = df_klasy_param.get("Prog_min_szkola")
    else:
        series = series.fillna(df_klasy_param.get("Prog_min_szkola"))
    data = series.dropna()
    if data.empty:
        print("Histogram progów: brak danych do wyświetlenia.")
        return None
    fig, ax = plt.subplots(figsize=(8, 6))
    sns.histplot(data, bins=20, kde=True, color="skyblue", ax=ax)
    ax.axvline(data.mean(), color="red", linestyle="--", label=f"Średnia: {data.mean():.1f}")
    ax.set_xlabel("Minimalny próg punktowy")
    ax.set_ylabel("Liczba klas")
    ax.set_title("Rozkład minimalnych progów punktowych (klasy)")
    ax.legend()
    plt.tight_layout()
    return fig

def bar_classes_per_district(df_klasy_param: pd.DataFrame, df_szkoly_param: Optional[pd.DataFrame]):
    if df_szkoly_param is None:
        print("Brak danych z arkusza 'szkoly' – pomijam wykres klas na dzielnice.")
        return None
    df = merge_with_district(df_klasy_param, df_szkoly_param)
    if "Dzielnica" not in df.columns:
        print("Kolumna 'Dzielnica' niedostępna – pomijam wykres klas na dzielnice.")
        return None
    counts = df["Dzielnica"].value_counts().sort_values(ascending=False)
    if counts.empty:
        print("Brak danych do wykresu klas na dzielnice.")
        return None
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.barplot(y=counts.index, x=counts.values, ax=ax, color="steelblue")
    ax.set_xlabel("Liczba klas")
    ax.set_ylabel("Dzielnica")
    ax.set_title("Liczba klas licealnych w dzielnicach")
    plt.tight_layout()
    return fig

def heatmap_subject_cooccurrence(df_klasy_param: pd.DataFrame, top_n: int = 10):
    valid_cols = [s for s in SUBJECTS if s in df_klasy_param.columns]
    if not valid_cols:
        print("Brak kolumn przedmiotów – pomijam heatmapę współwystępowania.")
        return None
    top_subjects = get_top_subjects(df_klasy_param, top_n)
    df_sub = df_klasy_param[top_subjects]
    if df_sub.empty:
        print("Brak danych do heatmapy współwystępowania.")
        return None
    matrix = df_sub.T.dot(df_sub).values
    fig = plot_heatmap_with_annotations(
        matrix,
        x_labels=top_subjects,
        y_labels=top_subjects,
        title="Współwystępowanie rozszerzeń przedmiotowych",
        xlabel="Przedmiot",
        ylabel="Przedmiot",
        cmap="OrRd",
    )
    return fig


def scatter_rank_vs_threshold(df_szkoly_param: pd.DataFrame):
    if df_szkoly_param is None:
        print("Brak danych o szkołach – pomijam scatter rank vs próg.")
        return None
    cols_needed = ["RankingPoz", "Prog_min_szkola"]
    if any(c not in df_szkoly_param.columns for c in cols_needed):
        print("Brak wymaganych kolumn do scatter rank vs próg.")
        return None
    df = df_szkoly_param.dropna(subset=cols_needed)
    if df.empty:
        print("Scatter rank vs próg: brak kompletnych danych.")
        return None
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(df["RankingPoz"], df["Prog_min_szkola"], s=60, alpha=.7, edgecolor="k")
    z = np.polyfit(df["RankingPoz"], df["Prog_min_szkola"], 1)
    xp = np.linspace(df["RankingPoz"].min(), df["RankingPoz"].max(), 100)
    ax.plot(xp, np.polyval(z, xp), linestyle="--")
    ax.set_xlabel("Pozycja w rankingu (↓ = lepiej)")
    ax.set_ylabel("Minimalny próg punktowy 2024")
    ax.set_title("Ranking szkoły a minimalny próg punktowy")
    plt.tight_layout()
    return fig

def _haversine_km(lat1, lon1, lat2, lon2):
    """Szybki haversine (km) dla skalarów lub wektorów NumPy."""
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = np.sin(dlat/2)**2 + np.cos(lat1)*np.cos(lat2)*np.sin(dlon/2)**2
    return 2 * R * np.arcsin(np.sqrt(a))

def scatter_rank_vs_distance(df_szkoly_param: pd.DataFrame):
    if df_szkoly_param is None or df_szkoly_param[["SzkolaLat", "SzkolaLon"]].isna().any(axis=None):
        print("Brak współrzędnych – pomijam scatter rank vs distance.")
        return None
    df = df_szkoly_param.copy()
    df["DistCenter_km"] = _haversine_km(df["SzkolaLat"], df["SzkolaLon"], WARSAW_CENTER_LAT, WARSAW_CENTER_LON)
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(df["DistCenter_km"], df["RankingPoz"], s=60, alpha=.7, edgecolor="k")
    z = np.polyfit(df["DistCenter_km"], df["RankingPoz"], 1)
    xp = np.linspace(0, df["DistCenter_km"].max(), 100)
    ax.plot(xp, np.polyval(z, xp), linestyle="--")
    ax.set_xlabel("Odległość od PKiN [km]")
    ax.set_ylabel("Pozycja w rankingu (↓ = lepiej)")
    ax.set_title("Ranking liceów vs odległość od centrum (PKiN)")
    ax.invert_yaxis()
    plt.tight_layout()
    return fig

def scatter_density_vs_rank(df_szkoly_param: pd.DataFrame, radius_km: float = 1.0):
    if df_szkoly_param is None or df_szkoly_param[["SzkolaLat", "SzkolaLon"]].isna().any(axis=None):
        print("Brak współrzędnych – pomijam scatter density vs rank.")
        return None
    df = df_szkoly_param.copy()
    lat = np.radians(df["SzkolaLat"].values)
    lon = np.radians(df["SzkolaLon"].values)
    sin_lat, cos_lat = np.sin(lat), np.cos(lat)
    dlon = lon[:, None] - lon
    cos_val = (sin_lat[:, None] * sin_lat) + (cos_lat[:, None] * cos_lat) * np.cos(dlon)
    cos_val = np.clip(cos_val, -1.0, 1.0)
    d = np.arccos(cos_val)
    dist_km = 6371.0 * d
    np.fill_diagonal(dist_km, np.inf)
    df["Nearby1km"] = (dist_km <= radius_km).sum(axis=1)
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(df["Nearby1km"], df["RankingPoz"], s=60, alpha=.7, edgecolor="k")
    ax.set_xlabel(f"Liczba liceów w promieniu {radius_km} km")
    ax.set_ylabel("Pozycja w rankingu (↓ = lepiej)")
    ax.set_title("„Zagęszczenie konkurencji” a ranking liceów")
    ax.invert_yaxis()
    plt.tight_layout()
    return fig

def scatter_hidden_gems(df_szkoly_param: pd.DataFrame, max_rank: int = 30, min_commute: float = 25):
    if df_szkoly_param is None or "CzasDojazdu" not in df_szkoly_param.columns:
        print("Brak danych o czasie dojazdu – pomijam hidden gems.")
        return None
    df = df_szkoly_param.copy()
    df = df[df["CzasDojazdu"].notna() & df["RankingPoz"].notna()]
    if df.empty:
        return None
    gems = df[(df["RankingPoz"] <= max_rank) & (df["CzasDojazdu"] >= min_commute)]
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(df["CzasDojazdu"], df["RankingPoz"], s=40, alpha=.3, color="grey", label="pozostałe")
    ax.scatter(gems["CzasDojazdu"], gems["RankingPoz"], s=80, edgecolor="k", color="#e41a1c", label="hidden gem")
    for _, r in gems.iterrows():
        ax.text(r["CzasDojazdu"], r["RankingPoz"], r["NazwaSzkoly"], fontsize=7, va="center", ha="left")
    ax.set_xlabel("Czas dojazdu z M. Wilanowska [min]")
    ax.set_ylabel("Pozycja w rankingu (↓ = lepiej)")
    ax.set_title("„Hidden gems” – elitarne licea z długim dojazdem")
    ax.legend()
    ax.invert_yaxis()
    plt.tight_layout()
    return fig

