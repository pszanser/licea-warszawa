
import sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from math import radians, sin, cos, asin, sqrt
import numpy as np
from itertools import combinations
import os

ROOT = Path(__file__).resolve().parent.parent.parent
RESULTS = ROOT / "results"
PATTERN = "LO_Warszawa_2025_*.xlsx"
OUT_DIR = RESULTS
WARSAW_CENTER_LAT = 52.2319  # Pałac Kultury i Nauki
WARSAW_CENTER_LON = 21.0067

def save_fig(fig, filename, dpi=150):
    """Zapisuje wykres do OUT_DIR i zamyka go."""
    out = OUT_DIR / filename
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=dpi)
    plt.close(fig)
    print(f"✔ zapisano {out.name}")

def get_latest_xls(results_dir, pattern):
    files = list(results_dir.glob(pattern))
    if not files:
        raise FileNotFoundError(f"Nie znaleziono plików pasujących do wzorca {pattern} w katalogu {results_dir}")
    return max(files, key=os.path.getmtime)

def load_excel_data(xls_path):
    excel_file_handle = pd.ExcelFile(xls_path)
    df_klasy = pd.read_excel(excel_file_handle, "klasy")
    df_klasy["RankingPoz"] = pd.to_numeric(df_klasy["RankingPoz"], errors="coerce")
    try:
        df_szkoly = pd.read_excel(excel_file_handle, "szkoly")
    except Exception as e:
        print(f"Ostrzeżenie: Nie udało się wczytać arkusza 'szkoly' z pliku {xls_path}. {e}")
        print("Heatmapy zależne od danych z arkusza 'szkoly' mogą nie zostać wygenerowane.")
        df_szkoly = None
    return df_klasy, df_szkoly

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.constants import ALL_SUBJECTS as SUBJECTS

# ----------------------- Helpers ---------------------------------------
def plot_heatmap_with_annotations(matrix, x_labels, y_labels, title, xlabel, ylabel, filename, cmap="YlGnBu", figsize=(10, 6), colorbar_label="Liczba klas"):
    """
    Rysuje heatmapę z anotacjami i zapisuje do pliku.
    """
    fig, ax = plt.subplots(figsize=figsize)
    im = ax.imshow(matrix, aspect='auto', cmap=cmap)
    ax.set_xticks(range(len(x_labels)))
    ax.set_xticklabels(x_labels, rotation=45, ha="right")
    ax.set_yticks(range(len(y_labels)))
    ax.set_yticklabels(y_labels)
    for i in range(len(y_labels)):
        for j in range(len(x_labels)):
            ax.text(j, i, matrix[i, j],
                    ha='center', va='center',
                    color='w' if matrix[i, j] > matrix.max() * 0.6 else 'black',
                    fontsize=8)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    fig.colorbar(im, ax=ax, fraction=0.03, pad=0.04, label=colorbar_label)
    plt.tight_layout()
    save_fig(fig, filename)

def merge_with_district(df_klasy_param, df_szkoly_param):
    """
    Łączy dane klas z dzielnicą na podstawie SzkolaIdentyfikator.
    """
    if "Dzielnica" not in df_klasy_param.columns and df_szkoly_param is not None:
        return df_klasy_param.merge(df_szkoly_param[['SzkolaIdentyfikator', 'Dzielnica']], on='SzkolaIdentyfikator', how='left')
    return df_klasy_param.copy()

def get_top_n(series, n):
    """Zwraca n najczęstszych wartości z serii."""
    return series.value_counts().head(n).index.tolist()

def get_top_subjects(df, n):
    """Zwraca n najpopularniejszych przedmiotów (kolumn binarnych) w DataFrame."""
    valid_subject_cols = [subj for subj in SUBJECTS if subj in df.columns]
    if not valid_subject_cols:
        return []
    return df[valid_subject_cols].sum().sort_values(ascending=False).head(n).index.tolist()

# ----------------------- 1) HEAT-MAPA PAR (helper) ---------------------
def heat_pairs(data: pd.DataFrame, tag: str, top_n_subj: int = 8) -> None:
    """
    Rysuje i zapisuje heat-mapę najczęstszych duetów rozszerzeń
    dla DataFrame `data` (podzbiór df) – plik PNG ląduje w OUT_DIR.
    """
    top_subj = get_top_subjects(data, top_n_subj)
    if not top_subj or len(top_subj) < 2: # Potrzebujemy co najmniej 2 przedmiotów do utworzenia par
        print(f"Brak wystarczających danych (mniej niż 2 popularne przedmioty) do wygenerowania heatmapy duetów ({tag})")
        return
    mat = pd.DataFrame(0, index=top_subj, columns=top_subj, dtype=int)

    # Zoptymalizowane obliczanie macierzy
    for subj_a, subj_b in combinations(top_subj, 2):
        # Liczymy, w ilu wierszach oba przedmioty (subj_a, subj_b) mają wartość 1
        count = ((data[subj_a] == 1) & (data[subj_b] == 1)).sum()
        mat.loc[subj_a, subj_b] = count
        mat.loc[subj_b, subj_a] = count # Macierz jest symetryczna

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
                    color="white" if v > mat.values.max()*0.5 else "black", fontsize=8)

    ax.set_title(f"{tag}: duety rozszerzeń")
    fig.colorbar(im, ax=ax, fraction=0.03, pad=0.04, label="Liczba klas")
    plt.tight_layout()
    filename = f"heatmap_pairs_{tag.lower()}.png"
    save_fig(fig, filename)

# ----------------------- 2) LOLLIPOP Δ TOP-30 vs ALL --------------------

def lollipop_diff_top30(df_klasy_param):
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
    filename = "lollipop_diff_top30_vs_all.png"
    save_fig(fig, filename)

# ----------------------- HEATMAPA PROFILI WG DZIELNIC ------------------

def heatmap_profiles_by_district(df_klasy_param, df_szkoly_param):
    if df_szkoly_param is None:
        print("Brak danych z arkusza 'szkoly' – pomijam heatmapy profili wg dzielnic.")
        return

    df_merged = merge_with_district(df_klasy_param, df_szkoly_param)
    if 'Dzielnica' not in df_merged.columns or df_merged['Dzielnica'].isnull().all():
        print("Ostrzeżenie: Kolumna 'Dzielnica' jest niedostępna lub pusta. Pomijam heatmapy profili wg dzielnic.")
        return
        
    groups = {
        'ALL': df_merged,
        'TOP30': df_merged[df_merged['RankingPoz'] <= 30],
        'TOP10': df_merged[df_merged['RankingPoz'] <= 10]
    }

    for name, sub in groups.items():
        if sub.empty:
            print(f"Brak danych dla grupy '{name}' – pomijam heatmapę profili wg dzielnic dla tej grupy.")
            continue
            
        top_dz = get_top_n(sub['Dzielnica'], 8)
        top_profiles = get_top_n(sub['Profil'], 10)

        if not top_dz or not top_profiles:
            print(f"Brak wystarczających danych (dzielnice lub profile) dla grupy '{name}' – pomijam heatmapę profili.")
            continue

        # Zoptymalizowane tworzenie macierzy za pomocą crosstab
        pivot_df = pd.crosstab(sub['Dzielnica'], sub['Profil'])
        # Upewniamy się, że wszystkie top_dz i top_profiles są obecne, brakujące wypełniamy 0
        matrix_df = pivot_df.reindex(index=top_dz, columns=top_profiles).fillna(0).astype(int)
        matrix = matrix_df.values
        
        plot_heatmap_with_annotations(
            matrix,
            x_labels=top_profiles,
            y_labels=top_dz,
            title=f'{name}: popularność profili wg dzielnic',
            xlabel='Profil (TOP 10)',
            ylabel='Dzielnica (TOP 8)',
            filename=f"heatmap_profiles_{name.lower()}.png"
        )

# ----------------------- HEATMAPA PRZEDMIOTÓW WG DZIELNIC (NOWA) ---------

def heatmap_subjects_by_district(df_klasy_param, df_szkoly_param):
    if df_szkoly_param is None:
        print("Brak danych z arkusza 'szkoly' – pomijam heatmapę przedmiotów wg dzielnic.")
        return

    df_klasy_merged = merge_with_district(df_klasy_param, df_szkoly_param)
    if 'Dzielnica' not in df_klasy_merged.columns or df_klasy_merged['Dzielnica'].isnull().all():
        print("Ostrzeżenie: Kolumna 'Dzielnica' jest niedostępna lub pusta po przetworzeniu. Pomijam heatmapę przedmiotów wg dzielnic.")
        return

    valid_subject_cols = [subj for subj in SUBJECTS if subj in df_klasy_merged.columns]
    if not valid_subject_cols:
        print("Brak kolumn przedmiotów w danych 'klasy' – pomijam heatmapę przedmiotów wg dzielnic.")
        return

    top10_subjects = get_top_subjects(df_klasy_merged, 10)
    # Upewnijmy się, że Dzielnica nie jest pusta przed próbą pobrania top_n
    if df_klasy_merged['Dzielnica'].dropna().empty:
        print("Brak danych o dzielnicach po scaleniu. Pomijam heatmapę przedmiotów wg dzielnic.")
        return
    top10_districts = get_top_n(df_klasy_merged['Dzielnica'].dropna(), 10)


    if not top10_subjects or not top10_districts:
        print("Brak wystarczających danych (przedmioty lub dzielnice) do wygenerowania heatmapy przedmiotów.")
        return

    # Zoptymalizowane tworzenie macierzy
    # Grupujemy po dzielnicy i sumujemy kolumny przedmiotów (które są binarne 0/1)
    grouped_df = df_klasy_merged.groupby('Dzielnica')[top10_subjects].sum()
    # Upewniamy się, że wszystkie top10_districts i top10_subjects są obecne, brakujące wypełniamy 0
    matrix_df = grouped_df.reindex(index=top10_districts, columns=top10_subjects).fillna(0).astype(int)
    matrix = matrix_df.values

    plot_heatmap_with_annotations(
        matrix,
        x_labels=top10_subjects,
        y_labels=top10_districts,
        title='Popularność rozszerzeń przedmiotowych wg dzielnic (Warszawa)',
        xlabel='Rozszerzenie (TOP 10)',
        ylabel='Dzielnica (TOP 10)',
        filename='heatmap_subjects_by_district.png'
    )

# ----------------------------------------------------------------------
#  WIZUALIZACJE „CZAS DOJAZDU”
# ----------------------------------------------------------------------

# 1) Bubble-chart  Próg pkt  ×  Czas dojazdu  ×  Ranking
def bubble_próg_vs_dojazd(df_szkoly_param):
    if df_szkoly_param is None or df_szkoly_param["CzasDojazdu"].isna().all():
        print("Brak kolumny CzasDojazdu – pomijam bubble-chart.")
        return
    df = df_szkoly_param.copy()
    df = df[df["CzasDojazdu"].notna() & df["Prog_min_szkola"].notna()]
    if df.empty:
        print("Bubble-chart: brak pełnych danych (próg + dojazd).")
        return

    # rozmiar ∝ odwrotność pozycji w rankingu
    size = 1200 / (df["RankingPoz"].fillna(100) + 4)
    # kolor = dzielnica
    dz_color = {d: c for d, c in zip(df["Dzielnica"].unique(), plt.cm.tab20.colors)}
    c = df["Dzielnica"].map(dz_color)

    fig, ax = plt.subplots(figsize=(8, 6))
    sc = ax.scatter(df["CzasDojazdu"], df["Prog_min_szkola"],
                    s=size, c=c, alpha=.7, edgecolor="k", linewidth=0.5)
    ax.set_xlabel("Czas dojazdu [min]")
    ax.set_ylabel("Próg punktowy 2024")
    ax.set_title("Próg punktowy vs czas dojazdu (rozmiar = ranking)")
    ax.grid(True, alpha=.2)
    plt.tight_layout()
    filename = "bubble_próg_vs_dojazd.png"
    save_fig(fig, filename)

# 2) Heat-mapa  „Ranking-bucket  ×  Czas-bucket”
def heatmap_rank_commute(df_szkoly_param):
    if df_szkoly_param is None or df_szkoly_param["CzasDojazdu"].isna().all():
        print("Brak CzasDojazdu – pomijam heat-mapę rank × czas.")
        return
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
    ax.set_xticks(range(len(pivot.columns))); ax.set_xticklabels(pivot.columns)
    ax.set_yticks(range(len(pivot.index)));   ax.set_yticklabels(pivot.index)
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
    filename = "heat_rank_vs_commute.png"
    save_fig(fig, filename)

# 3) Strip-plot  rozrzut czasów w każdej dzielnicy
def stripplot_commute_district(df_szkoly_param):
    if df_szkoly_param is None or df_szkoly_param["CzasDojazdu"].isna().all():
        print("Brak CzasDojazdu – pomijam strip-plot.")
        return
     
    df = df_szkoly_param.copy()

    fig, ax = plt.subplots(figsize=(9, 6))
    sns.stripplot(data=df, y="Dzielnica", x="CzasDojazdu",
                  jitter=0.25, size=5, ax=ax, alpha=.8)
    ax.set_xlabel("Czas dojazdu [min]")
    ax.set_ylabel("Dzielnica")
    ax.set_title("Rozrzut czasów dojazdu do liceów")
    plt.tight_layout()
    filename = "strip_commute_district.png"
    save_fig(fig, filename)

# ==== FUNKCJE POMOCNICZE ==============================================
def _haversine_km(lat1, lon1, lat2, lon2):
    """Szybki haversine (km) dla skalarów lub wektorów NumPy."""
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = np.sin(dlat/2)**2 + np.cos(lat1)*np.cos(lat2)*np.sin(dlon/2)**2
    return 2 * R * np.arcsin(np.sqrt(a))

# ==== SCATTER: RANKING VS DISTANCE OD PKiN ==========================
def scatter_rank_vs_distance(df_szkoly_param):
    if df_szkoly_param is None or df_szkoly_param[["SzkolaLat", "SzkolaLon"]].isna().any(axis=None):
        print("Brak współrzędnych – pomijam scatter rank vs distance.")
        return

    df = df_szkoly_param.copy()
    df["DistCenter_km"] = _haversine_km(df["SzkolaLat"], df["SzkolaLon"],
                                        WARSAW_CENTER_LAT, WARSAW_CENTER_LON)
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(df["DistCenter_km"], df["RankingPoz"],
               s=60, alpha=.7, edgecolor="k")
    # prosty trend liniowy
    z = np.polyfit(df["DistCenter_km"], df["RankingPoz"], 1)
    xp = np.linspace(0, df["DistCenter_km"].max(), 100)
    ax.plot(xp, np.polyval(z, xp), linestyle="--")
    ax.set_xlabel("Odległość od PKiN [km]")
    ax.set_ylabel("Pozycja w rankingu (↓ = lepiej)")
    ax.set_title("Ranking liceów vs odległość od centrum (PKiN)")
    ax.invert_yaxis()  # 1 = TOP
    plt.tight_layout()
    save_fig(fig, "scatter_rank_vs_distance.png")

# ==== SCATTER: GĘSTOŚĆ KONKURENCJI VS RANKING ======================
def scatter_density_vs_rank(df_szkoly_param, radius_km: float = 1.0):
    if df_szkoly_param is None or df_szkoly_param[["SzkolaLat", "SzkolaLon"]].isna().any(axis=None):
        print("Brak współrzędnych – pomijam scatter density vs rank.")
        return

    df = df_szkoly_param.copy()
    lat = np.radians(df["SzkolaLat"].values)
    lon = np.radians(df["SzkolaLon"].values)

    # wektorowo liczymy macierz odległości haversine
    sin_lat, cos_lat = np.sin(lat), np.cos(lat)
    dlon = lon[:, None] - lon
    d = np.arccos((sin_lat[:, None] * sin_lat) +
                  (cos_lat[:, None] * cos_lat) * np.cos(dlon))
    dist_km = 6371.0 * d

    # policz szkoły w promieniu radius_km (bez siebie)
    np.fill_diagonal(dist_km, np.inf)
    df["Nearby1km"] = (dist_km <= radius_km).sum(axis=1)

    fig, ax = plt.subplots(figsize=(8, 6))
    sc = ax.scatter(df["Nearby1km"], df["RankingPoz"],
                    s=60, alpha=.7, edgecolor="k")
    ax.set_xlabel(f"Liczba liceów w promieniu {radius_km} km")
    ax.set_ylabel("Pozycja w rankingu (↓ = lepiej)")
    ax.set_title("„Zagęszczenie konkurencji” a ranking liceów")
    ax.invert_yaxis()
    plt.tight_layout()
    save_fig(fig, "scatter_density_vs_rank.png")

# ==== SCATTER: HIDDEN GEMS =========================================
def scatter_hidden_gems(df_szkoly_param,
                        max_rank: int = 30,
                        min_commute: float = 25):
    if df_szkoly_param is None or "CzasDojazdu" not in df_szkoly_param.columns:
        print("Brak danych o czasie dojazdu – pomijam hidden gems.")
        return

    df = df_szkoly_param.copy()
    df = df[df["CzasDojazdu"].notna() & df["RankingPoz"].notna()]
    if df.empty:
        return

    gems = df[(df["RankingPoz"] <= max_rank) &
              (df["CzasDojazdu"] >= min_commute)]

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(df["CzasDojazdu"], df["RankingPoz"],
               s=40, alpha=.3, color="grey", label="pozostałe")
    ax.scatter(gems["CzasDojazdu"], gems["RankingPoz"],
               s=80, edgecolor="k", color="#e41a1c", label="hidden gem")
    for _, r in gems.iterrows():
        ax.text(r["CzasDojazdu"], r["RankingPoz"],
                r["NazwaSzkoly"], fontsize=7, va="center", ha="left")
    ax.set_xlabel("Czas dojazdu z M. Wilanowska [min]")
    ax.set_ylabel("Pozycja w rankingu (↓ = lepiej)")
    ax.set_title("„Hidden gems” – elitarne licea z długim dojazdem")
    ax.legend()
    ax.invert_yaxis()
    plt.tight_layout()
    save_fig(fig, "scatter_hidden_gems.png")

# ----------------------- MAIN ------------------------------------------
def ensure_subject_columns(df):
    for subj_col in SUBJECTS:
        if subj_col not in df.columns:
            print(f"Ostrzeżenie: Brak kolumny '{subj_col}' w danych 'klasy'. Może to wpłynąć na generowanie profili.")
            # Można dodać df[subj_col] = 0, jeśli to pożądane zachowanie

def add_profile_column(df):
    subject_codes = {s: s[:3] if len(s) > 3 else s for s in SUBJECTS}
    if "Profil" not in df.columns:
        def make_prof(r):
            active_subjects = [s for s in SUBJECTS if s in r and r[s] == 1]
            return "-".join(sorted(subject_codes[s] for s in active_subjects))
        df["Profil"] = df.apply(make_prof, axis=1)

def main():
    try:
        xls_path = get_latest_xls(RESULTS, PATTERN)
        print(f"Używam pliku: {xls_path}")
        df_klasy, df_szkoly = load_excel_data(xls_path)

        ensure_subject_columns(df_klasy)
        add_profile_column(df_klasy)

        # Heat-mapy duetów
        for tag, filt in [("all", None), ("top30", df_klasy["RankingPoz"] <= 30), ("top10", df_klasy["RankingPoz"] <= 10)]:
            data = df_klasy if filt is None else df_klasy[filt]
            heat_pairs(data, tag)

        lollipop_diff_top30(df_klasy)
        heatmap_profiles_by_district(df_klasy, df_szkoly)
        heatmap_subjects_by_district(df_klasy, df_szkoly)
        bubble_próg_vs_dojazd(df_szkoly)
        heatmap_rank_commute(df_szkoly)
        stripplot_commute_district(df_szkoly)
        scatter_rank_vs_distance(df_szkoly)
        scatter_density_vs_rank(df_szkoly)
        scatter_hidden_gems(df_szkoly)

        print("Gotowe – PNG-i w katalogu results/")
    except Exception as e:
        print(f"Błąd podczas generowania wizualizacji: {e}")


if __name__ == "__main__":
    main()