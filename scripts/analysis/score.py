import numpy as np
import pandas as pd

# wstępna przymiarka liczenia wskaźnika oraz wag
# wQ - jakość szkoły wynikająca z rankingu
# wA - prawdopodobieństwo przyjęcia na podstawie punktów
# wC - czas dojazdu do szkoły
# wP - dopasowanie profilu do przedmiotów rozszerzonych
# wQ + wA + wC + wP = 1

DEFAULT_W = dict(wQ=0.4, wA=0.4, wC=0.2, wP=0.0)
K_SIGMOID = 0.15
DEFAULT_DISTANCE_SCORE_LIMIT_KM = 15.0
FIT_COMPONENTS = {
    "ranking": "RankingComponent",
    "admission": "AdmissionComponent",
    "distance": "DistanceComponent",
    "profile": "ProfileComponent",
}
BEST_SCHOOL_SUMMARY_COLUMNS = [
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
]


def haversine_km(lat1, lon1, lat2, lon2):
    """Zwraca odległość w linii prostej w kilometrach."""
    lat1_num = pd.to_numeric(lat1, errors="coerce")
    lon1_num = pd.to_numeric(lon1, errors="coerce")
    lat2_num = pd.to_numeric(lat2, errors="coerce")
    lon2_num = pd.to_numeric(lon2, errors="coerce")
    lat1_rad, lon1_rad, lat2_rad, lon2_rad = map(
        np.radians, [lat1_num, lon1_num, lat2_num, lon2_num]
    )
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    a = (
        np.sin(dlat / 2) ** 2
        + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2) ** 2
    )
    return 2 * 6371.0 * np.arcsin(np.sqrt(a))


def add_distance_from_point(
    df_schools: pd.DataFrame, start_lat: float, start_lon: float
) -> pd.DataFrame:
    """Dodaje kolumnę OdlegloscKm dla szkół względem punktu startowego."""
    df = df_schools.copy()
    if "SzkolaLat" not in df.columns or "SzkolaLon" not in df.columns:
        df["OdlegloscKm"] = np.nan
        return df
    df["OdlegloscKm"] = haversine_km(
        start_lat, start_lon, df["SzkolaLat"], df["SzkolaLon"]
    )
    return df


def _lat_lng_from_mapping(value: object) -> tuple[float, float] | None:
    if not isinstance(value, dict):
        return None
    lat = value.get("lat")
    lng = value.get("lng")
    if lat is None or lng is None:
        return None
    try:
        return float(lat), float(lng)
    except (TypeError, ValueError):
        return None


def select_start_point(
    map_state: dict | None, allow_center: bool = False
) -> tuple[float, float] | None:
    """Zwraca punkt startowy z mapy; kliknięcie ma pierwszeństwo przed środkiem."""
    if not map_state:
        return None
    clicked = _lat_lng_from_mapping(map_state.get("last_clicked"))
    if clicked is not None:
        return clicked
    if allow_center:
        return _lat_lng_from_mapping(map_state.get("center"))
    return None


def shortlist_schools_by_distance(
    df_schools: pd.DataFrame,
    limit: int = 40,
    max_distance_km: float | None = None,
) -> pd.DataFrame:
    """Zwraca najbliższe szkoły z uzupełnioną odległością."""
    if "OdlegloscKm" not in df_schools.columns:
        raise ValueError("Brak kolumny OdlegloscKm; wywołaj add_distance_from_point().")
    if limit <= 0:
        return df_schools.iloc[0:0].copy()
    df_with_distance = df_schools.dropna(subset=["OdlegloscKm"]).copy()
    if max_distance_km is not None:
        df_with_distance = df_with_distance[
            df_with_distance["OdlegloscKm"] <= float(max_distance_km)
        ]
    return (
        df_with_distance.sort_values(["OdlegloscKm", "NazwaSzkoly"], na_position="last")
        .head(limit)
        .copy()
    )


def _compute_min_prog(df: pd.DataFrame) -> pd.Series:
    """Zwraca serię z właściwym progiem przyjęcia dla każdej klasy."""
    return df["Prog_min_klasa"].fillna(df["Prog_min_szkola"])


def _score_ranking(ranking: pd.Series) -> pd.Series:
    ranking_num = pd.to_numeric(ranking, errors="coerce")
    valid = ranking_num.dropna()
    if valid.empty:
        return pd.Series(np.nan, index=ranking.index, dtype=float)
    max_rank = valid.max()
    if max_rank <= 1:
        return pd.Series(
            np.where(ranking_num.notna(), 1.0, np.nan), index=ranking.index
        )
    return (1 - (ranking_num - 1) / (max_rank - 1)).clip(0, 1)


def _score_distance(
    distance: pd.Series, score_limit_km: float = DEFAULT_DISTANCE_SCORE_LIMIT_KM
) -> pd.Series:
    distance_num = pd.to_numeric(distance, errors="coerce")
    if score_limit_km <= 0:
        raise ValueError("score_limit_km musi być większe od zera.")
    if distance_num.dropna().empty:
        return pd.Series(np.nan, index=distance.index, dtype=float)
    return (1 - distance_num / float(score_limit_km)).clip(0, 1)


def _score_profile(df: pd.DataFrame, subjects: list[str] | None) -> pd.Series:
    subjects = subjects or []
    if not subjects:
        return pd.Series(np.nan, index=df.index, dtype=float)
    values = []
    for subject in subjects:
        if subject in df.columns:
            values.append(pd.to_numeric(df[subject], errors="coerce").fillna(0))
        else:
            values.append(pd.Series(0, index=df.index, dtype=float))
    return pd.concat(values, axis=1).sum(axis=1).div(len(subjects)).clip(0, 1)


def risk_label(margin: float | int | None) -> str:
    """Opisuje ryzyko progu na podstawie marginesu punktowego."""
    if margin is None or pd.isna(margin):
        return "brak danych"
    if margin >= 15:
        return "bezpiecznie"
    if margin >= 0:
        return "realnie"
    if margin >= -10:
        return "ryzykownie"
    return "bardzo ryzykownie"


def build_fit_explanation(row: pd.Series) -> str:
    """Buduje krótkie wyjaśnienie wyniku dopasowania."""
    plusy = []
    ryzyka = []
    missing_components = row.get("BrakiDanych")
    missing_components_text = (
        str(missing_components).strip()
        if pd.notna(missing_components) and str(missing_components).strip()
        else ""
    )

    profile_score = row.get("ProfileComponent")
    if pd.notna(profile_score):
        if profile_score >= 0.99:
            plusy.append("profil pasuje")
        elif profile_score > 0:
            plusy.append("profil częściowo pasuje")

    distance = row.get("OdlegloscKm")
    if pd.notna(distance):
        distance_text = f"{float(distance):.1f} km"
        if distance <= 5:
            plusy.append(f"blisko ({distance_text})")
        elif distance >= 12:
            ryzyka.append(f"daleko ({distance_text})")

    margin = row.get("AdmitMargin")
    label = risk_label(margin)
    if pd.notna(margin):
        margin_value = float(margin)
        if margin_value >= 0:
            plusy.append(f"margines +{margin_value:.0f} pkt")
        else:
            ryzyka.append(f"próg o {abs(margin_value):.0f} pkt powyżej wyniku")
    elif label == "brak danych" and "brak progu" not in missing_components_text:
        ryzyka.append("brak progu")

    if missing_components_text:
        ryzyka.append(missing_components_text)

    ranking = row.get("RankingPoz")
    if pd.notna(ranking) and float(ranking) <= 30:
        plusy.append(f"ranking TOP {int(float(ranking))}")

    if not plusy:
        plusy.append("najlepsze dostępne dane")
    text = "wysoko: " + ", ".join(plusy)
    if ryzyka:
        text += "; ryzyko: " + ", ".join(ryzyka)
    return text


def _missing_components_text(row: pd.Series, active_weights: dict[str, float]) -> str:
    """Opisuje brakujące dane dla składowych, które użytkownik faktycznie waży."""
    missing = []
    if active_weights.get("ranking", 0) > 0 and pd.isna(row.get("RankingComponent")):
        missing.append("brak rankingu")
    if active_weights.get("admission", 0) > 0 and pd.isna(
        row.get("AdmissionComponent")
    ):
        missing.append("brak progu")
    if active_weights.get("distance", 0) > 0 and pd.isna(row.get("DistanceComponent")):
        missing.append("brak odległości")
    if active_weights.get("profile", 0) > 0 and pd.isna(row.get("ProfileComponent")):
        missing.append("brak profilu")
    return "; ".join(missing)


def score_personalized_classes(
    df_classes: pd.DataFrame,
    points: float,
    weights: dict[str, float],
    profile_subjects: list[str] | None = None,
    distance_score_limit_km: float = DEFAULT_DISTANCE_SCORE_LIMIT_KM,
) -> pd.DataFrame:
    """Liczy FitScore 0-100 dla klas według preferencji użytkownika."""
    df = df_classes.copy()
    df["MinProg"] = _compute_min_prog(df)
    df["AdmitMargin"] = points - df["MinProg"]

    if "RankingPoz" in df.columns:
        df["RankingComponent"] = _score_ranking(df["RankingPoz"])
    else:
        df["RankingComponent"] = np.nan
    df["AdmissionComponent"] = np.where(
        df["MinProg"].notna(),
        1 / (1 + np.exp(-K_SIGMOID * df["AdmitMargin"])),
        np.nan,
    )
    if "OdlegloscKm" in df.columns:
        df["DistanceComponent"] = _score_distance(
            df["OdlegloscKm"], score_limit_km=distance_score_limit_km
        )
    else:
        df["DistanceComponent"] = np.nan
    df["ProfileComponent"] = _score_profile(df, profile_subjects)

    df["RankingScore"] = df["RankingComponent"] * 100
    df["AdmissionScore"] = df["AdmissionComponent"] * 100
    df["DistanceScore"] = df["DistanceComponent"] * 100
    df["ProfileScore"] = df["ProfileComponent"] * 100

    weighted_sum = pd.Series(0.0, index=df.index)
    active_weight_sum = 0.0
    active_weights: dict[str, float] = {}
    for key, component_col in FIT_COMPONENTS.items():
        weight = float(weights.get(key, 0) or 0)
        if weight <= 0:
            continue
        active_weights[key] = weight
        component = pd.to_numeric(df[component_col], errors="coerce")
        weighted_sum = weighted_sum.add(component.fillna(0) * weight)
        active_weight_sum += weight

    df["FitScore"] = (
        weighted_sum / active_weight_sum * 100 if active_weight_sum > 0 else np.nan
    )
    df["RyzykoProgu"] = df["AdmitMargin"].apply(risk_label)
    df["BrakiDanych"] = df.apply(
        _missing_components_text, axis=1, active_weights=active_weights
    )
    df["Dlaczego"] = df.apply(build_fit_explanation, axis=1)
    return df.sort_values("FitScore", ascending=False, na_position="last")


def summarize_best_schools(fit_results: pd.DataFrame) -> pd.DataFrame:
    """Zwraca jedno podsumowanie szkoły na podstawie jej najlepszej klasy."""
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
        col for col in BEST_SCHOOL_SUMMARY_COLUMNS if col in best_schools.columns
    ]
    return best_schools[summary_cols].copy()


def add_metrics(
    df: pd.DataFrame, P: float, desired_subject: str | None = None
) -> pd.DataFrame:
    """Dodaje kolumny Quality, AdmitProb, CommuteScore, ProfileMatch."""
    df = df.copy()
    max_rank = max(df["RankingPoz"].dropna().max(), 1)
    max_commute = max(df["CzasDojazdu"].dropna().max(), 1)

    df["MinProg"] = _compute_min_prog(df)
    df["AdmitMargin"] = P - df["MinProg"]
    df["AdmitProb"] = 1 / (1 + np.exp(-K_SIGMOID * df["AdmitMargin"]))
    df["Quality"] = (max_rank - df["RankingPoz"].fillna(max_rank) + 1) / max_rank
    df["CommuteScore"] = 1 - df["CzasDojazdu"].fillna(max_commute) / max_commute

    if desired_subject:
        pattern = rf"(?i)\b{desired_subject}\b"
        df["ProfileMatch"] = (
            df["PrzedmiotyRozszerzone"].str.contains(pattern, na=False).astype(int)
        )
    else:
        df["ProfileMatch"] = 1  # brak filtru → każdy = 1

    return df


def compute_composite(df: pd.DataFrame, w: dict | None = None) -> pd.DataFrame:
    """Zwraca df z kolumną Composite i posortowany."""
    w = w or DEFAULT_W
    cols = ["Quality", "AdmitProb", "CommuteScore", "ProfileMatch"]
    for c in cols:
        if c not in df.columns:
            raise ValueError(f"Brak kolumny {c}; wywołaj add_metrics() najpierw.")
    df["Composite"] = (
        w["wQ"] * df["Quality"]
        + w["wA"] * df["AdmitProb"]
        + w["wC"] * df["CommuteScore"]
        + w["wP"] * df["ProfileMatch"]
    )
    return df.sort_values("Composite", ascending=False)
