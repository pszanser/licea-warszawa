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


def _compute_min_prog(df: pd.DataFrame) -> pd.Series:
    """Zwraca serię z właściwym progiem przyjęcia dla każdej klasy."""
    return df["Prog_min_klasa"].fillna(df["Prog_min_szkola"])


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
