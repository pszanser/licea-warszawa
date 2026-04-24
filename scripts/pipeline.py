import argparse
import asyncio
import datetime
import logging
import os
import re
import time
import unicodedata
from pathlib import Path
from typing import Any

import pandas as pd
import requests
import yaml

from scripts.api_clients.googlemaps_api import (
    get_coordinates_for_addresses_batch,
    get_next_weekday_time,
    get_travel_times_batch,
)
from scripts.config.constants import ALL_SUBJECTS
from scripts.data_processing.load_minimum_points import load_min_points
from scripts.data_processing.load_plan_naboru import load_plan_naboru
from scripts.data_processing.parser_perspektywy import (
    parse_ranking_perspektywy_html,
    parse_ranking_perspektywy_pdf,
)

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RESULTS_DIR = BASE_DIR / "results"
SCRIPTS_DIR = BASE_DIR / "scripts"
SOURCE_CONFIG_FILE = SCRIPTS_DIR / "config" / "data_sources.yml"
PROJECT_CONFIG_FILE = SCRIPTS_DIR / "config" / "config.yml"
KODY_FILE = DATA_DIR / "reference" / "waw_kod_dzielnica.csv"
CZASY_DOJAZDU_FILE = RESULTS_DIR / "czasy_dojazdu.xlsx"
LEGACY_APP_FILE = RESULTS_DIR / "LO_Warszawa_2025_Warszawa_SL.xlsx"

REPL = {
    r"liceum og[oó]lnokszta[łl]c[a-ząćęłńóśźż]*": "lo",
    r"im(?:\.|ienia)?": "",
    r"i\.?i\.?": "ii",
}


def load_yaml(path: Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def project_config() -> dict[str, Any]:
    return load_yaml(PROJECT_CONFIG_FILE)


def source_config() -> dict[str, Any]:
    return load_yaml(SOURCE_CONFIG_FILE)


def resolve_path(path_value: str | Path) -> Path:
    path = Path(path_value)
    return path if path.is_absolute() else BASE_DIR / path


def normalize_name(name: str) -> str:
    if pd.isna(name):
        return ""
    x = str(name).lower()
    for pat, rep in REPL.items():
        x = re.sub(pat, rep, x)
    x = unicodedata.normalize("NFKD", x).encode("ascii", "ignore").decode()
    x = re.sub(r"[^a-z0-9 ]+", " ", x)
    x = re.sub(r"\s+", " ", x).strip()
    m = re.match(r"(?P<num>[ivxlcdm]+)\s+lo.*?(?P<patron>[a-z]+)$", x)
    if m:
        return f"{m['num']}_{m['patron']}"
    return x


def get_school_type(name: str) -> str:
    name = str(name).lower()
    if "technikum" in name:
        return "technikum"
    if "branżowa" in name or "branzowa" in name:
        return "branżowa"
    return "liceum"


def extract_class_type(class_name: str) -> str | None:
    if pd.isna(class_name):
        return None
    m = re.search(r"\[([^\]]+)\]", str(class_name))
    return m.group(1).strip() if m else None


def ensure_source_file(source: dict[str, Any]) -> Path:
    path = resolve_path(source["path"])
    if path.exists():
        return path
    url = source.get("source_url")
    if not url:
        raise FileNotFoundError(f"Brak lokalnego pliku i URL zrodla: {path}")
    logger.info("Pobieranie zrodla: %s", url)
    response = requests.get(url, timeout=60, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(response.content)
    logger.info("Zapisano zrodlo do %s", path)
    return path


def threshold_sources(year_cfg: dict[str, Any]) -> list[dict[str, Any]]:
    threshold_cfg = year_cfg.get("thresholds")
    if not threshold_cfg:
        return []
    if "sources" not in threshold_cfg:
        source = threshold_cfg.copy()
        source.setdefault("priority", 1)
        return [source]

    inherited = {key: value for key, value in threshold_cfg.items() if key != "sources"}
    sources = []
    for index, source in enumerate(threshold_cfg["sources"], start=1):
        merged = inherited | source
        merged.setdefault("priority", index)
        sources.append(merged)
    return sources


def load_thresholds(year_cfg: dict[str, Any]) -> pd.DataFrame:
    sources = threshold_sources(year_cfg)
    if not sources:
        return pd.DataFrame(columns=["NazwaSzkoly", "OddzialNazwa", "Prog_min_klasa"])

    frames = []
    for source in sources:
        path = ensure_source_file(source)
        threshold_year = source.get("threshold_year", year_cfg.get("admission_year"))
        df_source = load_min_points(path, admission_year=threshold_year)
        if "admission_year" in df_source.columns:
            df_source = df_source.rename(columns={"admission_year": "threshold_year"})
        else:
            df_source["threshold_year"] = threshold_year
        df_source["threshold_kind"] = source.get(
            "threshold_kind", year_cfg.get("threshold_mode", "actual")
        )
        df_source["threshold_priority"] = int(source.get("priority", 1))
        df_source["threshold_label"] = source.get(
            "threshold_label", f"progi {threshold_year}"
        )
        df_source["threshold_source"] = source.get("source_url", str(path))
        df_source["SzkolaIdentyfikator"] = df_source["NazwaSzkoly"].apply(
            normalize_name
        )
        df_source["year"] = year_cfg["year"]
        df_source["admission_year"] = year_cfg.get("admission_year")
        df_source["school_year"] = year_cfg.get("school_year")
        frames.append(df_source)

    return pd.concat(frames, ignore_index=True, sort=False)


def best_thresholds_for_keys(
    df_thresholds: pd.DataFrame, keys: list[str]
) -> pd.DataFrame:
    if df_thresholds.empty:
        return df_thresholds.copy()
    required = keys + ["threshold_priority"]
    if not set(required).issubset(df_thresholds.columns):
        return df_thresholds.copy()
    sort_cols = keys + ["threshold_priority"]
    if "Prog_min_klasa" in df_thresholds.columns:
        sort_cols.append("Prog_min_klasa")
    return (
        df_thresholds.sort_values(sort_cols, na_position="last")
        .drop_duplicates(keys, keep="first")
        .copy()
    )


def school_threshold_summary(df_thresholds: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "SzkolaIdentyfikator",
        "Prog_min_szkola",
        "Prog_max_szkola",
        "Prog_szkola_threshold_year",
        "Prog_szkola_threshold_kind",
        "Prog_szkola_threshold_label",
    ]
    if df_thresholds.empty:
        return pd.DataFrame(columns=columns)

    school_source_cols = [
        "SzkolaIdentyfikator",
        "threshold_priority",
        "threshold_year",
        "threshold_kind",
        "threshold_label",
    ]
    best_school_sources = best_thresholds_for_keys(
        df_thresholds[school_source_cols].drop_duplicates(),
        ["SzkolaIdentyfikator"],
    )
    selected = df_thresholds.merge(
        best_school_sources[
            ["SzkolaIdentyfikator", "threshold_priority", "threshold_year"]
        ],
        how="inner",
        on=["SzkolaIdentyfikator", "threshold_priority", "threshold_year"],
    )
    return (
        selected.groupby("SzkolaIdentyfikator")
        .agg(
            Prog_min_szkola=("Prog_min_klasa", "min"),
            Prog_max_szkola=("Prog_min_klasa", "max"),
            Prog_szkola_threshold_year=("threshold_year", "first"),
            Prog_szkola_threshold_kind=("threshold_kind", "first"),
            Prog_szkola_threshold_label=("threshold_label", "first"),
        )
        .reset_index()
    )


def format_threshold_value(value: Any) -> str:
    if pd.isna(value):
        return ""
    number = float(value)
    return str(int(number)) if number.is_integer() else f"{number:.2f}".rstrip("0")


def format_threshold_range(min_value: Any, max_value: Any) -> str:
    min_text = format_threshold_value(min_value)
    max_text = format_threshold_value(max_value)
    if min_text == max_text:
        return min_text
    return f"{min_text}-{max_text}"


def format_ranking_value(value: Any, text_value: Any = None) -> str:
    if text_value is not None and pd.notna(text_value):
        text = str(text_value).strip()
        if text and text.lower() != "nan":
            text = text.rstrip("=")
            return text[:-2] if text.endswith(".0") else text
    if pd.isna(value):
        return ""
    number = float(value)
    return str(int(number)) if number.is_integer() else f"{number:.2f}".rstrip("0")


def historical_school_thresholds(df_thresholds: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "SzkolaIdentyfikator",
        "Progi_historyczne_szkola",
        "Progi_historyczne_lata",
    ]
    if df_thresholds.empty:
        return pd.DataFrame(columns=columns)

    ranges = (
        df_thresholds.groupby(["SzkolaIdentyfikator", "threshold_year"])
        .agg(
            Prog_min=("Prog_min_klasa", "min"),
            Prog_max=("Prog_min_klasa", "max"),
        )
        .reset_index()
        .sort_values(["SzkolaIdentyfikator", "threshold_year"], ascending=[True, False])
    )

    rows = []
    for school_id, group in ranges.groupby("SzkolaIdentyfikator", sort=False):
        parts = [
            f"{int(row.threshold_year)}: "
            f"{format_threshold_range(row.Prog_min, row.Prog_max)}"
            for row in group.itertuples(index=False)
        ]
        rows.append(
            {
                "SzkolaIdentyfikator": school_id,
                "Progi_historyczne_szkola": "; ".join(parts),
                "Progi_historyczne_lata": "/".join(
                    str(int(year)) for year in group["threshold_year"].tolist()
                ),
            }
        )
    return pd.DataFrame(rows, columns=columns)


def school_ranking_summary(df_rankings: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "SzkolaIdentyfikator",
        "RankingPozNajnowszy",
        "RankingPozTekstNajnowszy",
        "RankingRok",
        "Ranking_historyczny_szkola",
        "Ranking_lata",
    ]
    if df_rankings.empty or "SzkolaIdentyfikator" not in df_rankings.columns:
        return pd.DataFrame(columns=columns)

    rankings = df_rankings.copy()
    if "RankingPozTekst" not in rankings.columns:
        rankings["RankingPozTekst"] = rankings["RankingPoz"].astype(str)
    rankings["RankingPoz"] = pd.to_numeric(rankings["RankingPoz"], errors="coerce")
    rankings["year"] = pd.to_numeric(rankings["year"], errors="coerce")
    rankings = rankings.dropna(subset=["SzkolaIdentyfikator", "year", "RankingPoz"])
    if rankings.empty:
        return pd.DataFrame(columns=columns)

    rankings = (
        rankings.sort_values(
            ["SzkolaIdentyfikator", "year", "RankingPoz"],
            ascending=[True, False, True],
        )
        .drop_duplicates(["SzkolaIdentyfikator", "year"], keep="first")
        .sort_values(["SzkolaIdentyfikator", "year"], ascending=[True, False])
    )

    rows = []
    for school_id, group in rankings.groupby("SzkolaIdentyfikator", sort=False):
        latest = group.iloc[0]
        parts = [
            f"{int(row.year)}: "
            f"{format_ranking_value(row.RankingPoz, row.RankingPozTekst)}"
            for row in group.itertuples(index=False)
        ]
        rows.append(
            {
                "SzkolaIdentyfikator": school_id,
                "RankingPozNajnowszy": latest["RankingPoz"],
                "RankingPozTekstNajnowszy": format_ranking_value(
                    latest["RankingPoz"], latest["RankingPozTekst"]
                ),
                "RankingRok": int(latest["year"]),
                "Ranking_historyczny_szkola": "; ".join(parts),
                "Ranking_lata": "/".join(
                    str(int(year)) for year in group["year"].tolist()
                ),
            }
        )
    return pd.DataFrame(rows, columns=columns)


def apply_latest_rankings(sheets: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    ranking_summary = school_ranking_summary(sheets.get("rankings", pd.DataFrame()))
    if ranking_summary.empty:
        return sheets

    updated = sheets.copy()
    for sheet_name in ["schools", "classes"]:
        df = updated.get(sheet_name, pd.DataFrame())
        if df.empty or "SzkolaIdentyfikator" not in df.columns:
            continue
        df = df.copy()
        rename_columns = {}
        if "RankingPoz" in df.columns:
            rename_columns["RankingPoz"] = "RankingPozRokuDanych"
        if "RankingPozTekst" in df.columns:
            rename_columns["RankingPozTekst"] = "RankingPozTekstRokuDanych"
        df = df.rename(columns=rename_columns)
        df = df.drop(
            columns=[
                "RankingPozNajnowszy",
                "RankingPozTekstNajnowszy",
                "RankingRok",
                "Ranking_historyczny_szkola",
                "Ranking_lata",
            ],
            errors="ignore",
        )
        df = df.merge(ranking_summary, how="left", on="SzkolaIdentyfikator")
        df["RankingPoz"] = df["RankingPozNajnowszy"]
        df["RankingPozTekst"] = df["RankingPozTekstNajnowszy"]
        updated[sheet_name] = df
    return updated


def threshold_meta(year_cfg: dict[str, Any]) -> dict[str, Any]:
    sources = threshold_sources(year_cfg)
    years = [
        str(source.get("threshold_year"))
        for source in sources
        if source.get("threshold_year") is not None
    ]
    source_refs = [source.get("source_url") or source.get("path") for source in sources]
    return {
        "threshold_mode": year_cfg.get("threshold_mode"),
        "threshold_label": year_cfg.get("threshold_label"),
        "threshold_years": "/".join(years),
        "threshold_source": " | ".join(str(ref) for ref in source_refs if ref),
    }


def load_ranking(year_cfg: dict[str, Any]) -> pd.DataFrame:
    ranking_cfg = year_cfg.get("ranking")
    if not ranking_cfg:
        return pd.DataFrame(columns=["RankingPoz", "NazwaSzkoly", "Dzielnica"])

    cache_path = (
        resolve_path(ranking_cfg["cache_path"])
        if ranking_cfg.get("cache_path")
        else None
    )
    if cache_path and cache_path.exists():
        df = pd.read_excel(cache_path)
    else:
        source_type = ranking_cfg["type"]
        path = ensure_source_file(ranking_cfg)
        if source_type == "perspektywy_pdf":
            df = parse_ranking_perspektywy_pdf(path)
        elif source_type == "perspektywy_html":
            df = parse_ranking_perspektywy_html(path, year=year_cfg["year"])
        else:
            raise ValueError(f"Nieznany typ rankingu: {source_type}")
        if cache_path:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            df.to_excel(cache_path, index=False)

    if "RankingPozTekst" not in df.columns and "RankingPoz" in df.columns:
        df["RankingPozTekst"] = df["RankingPoz"].astype(str)
    df["RankingPoz"] = pd.to_numeric(df["RankingPoz"], errors="coerce")
    df["SzkolaIdentyfikator"] = df["NazwaSzkoly"].apply(normalize_name)
    df["year"] = year_cfg["year"]
    df["school_year"] = year_cfg.get("school_year")
    return df


def load_location_cache() -> pd.DataFrame:
    candidates = [
        resolve_path("results/app/licea_warszawa.xlsx"),
        LEGACY_APP_FILE,
        RESULTS_DIR / "LO_Warszawa_2025_Warszawa_Metro_Wilanowska.xlsx",
    ]
    frames = []
    for path in candidates:
        if not path.exists():
            continue
        try:
            excel = pd.ExcelFile(path)
            sheet = "schools" if "schools" in excel.sheet_names else "szkoly"
            df = pd.read_excel(excel, sheet_name=sheet)
        except Exception:
            continue
        cols = [
            col
            for col in [
                "source_school_id",
                "SzkolaIdentyfikator",
                "AdresSzkoly",
                "CzasDojazdu",
                "SzkolaLat",
                "SzkolaLon",
                "url",
            ]
            if col in df.columns
        ]
        if cols:
            frames.append(df[cols].copy())
    if not frames:
        return pd.DataFrame()
    cache = pd.concat(frames, ignore_index=True)
    if "source_school_id" in cache.columns and cache["source_school_id"].notna().any():
        cache = cache.dropna(subset=["source_school_id"]).drop_duplicates(
            subset=["source_school_id"], keep="first"
        )
    else:
        cache = cache.dropna(subset=["SzkolaIdentyfikator"]).drop_duplicates(
            subset=["SzkolaIdentyfikator"], keep="first"
        )
    return cache


def load_vulcan_offer(year_cfg: dict[str, Any]) -> pd.DataFrame:
    offer_cfg = year_cfg["offer"]
    path = resolve_path(offer_cfg["path"])
    if path.exists():
        return pd.read_excel(path)

    from scripts.data_processing.get_data_vulcan_async import download_all_async

    start_id = offer_cfg.get("start_id", 1)
    end_id = offer_cfg.get("end_id", 400)
    df = asyncio.run(download_all_async(start_id, end_id, verbose=True))
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(path, index=False)
    return df


def prepare_vulcan_offer(df_vulcan: pd.DataFrame, cfg: dict[str, Any]) -> pd.DataFrame:
    df_vulcan = df_vulcan.copy()
    df_vulcan["TypSzkoly"] = df_vulcan["NazwaSzkoly"].apply(get_school_type)

    filtr_miasto = cfg.get("filtr_miasto")
    if filtr_miasto:
        df_vulcan = df_vulcan[
            df_vulcan["AdresSzkoly"].str.contains(filtr_miasto, na=False, case=False)
        ]

    filtr_typ = cfg.get("filtr_typ_szkola")
    if filtr_typ:
        typy = [filtr_typ] if isinstance(filtr_typ, str) else filtr_typ
        df_vulcan = df_vulcan[df_vulcan["TypSzkoly"].isin(typy)]

    df_vulcan["SzkolaIdentyfikator"] = df_vulcan["NazwaSzkoly"].apply(normalize_name)
    df_vulcan["source_school_id"] = "vulcan:" + df_vulcan["IdSzkoly"].astype(str)
    df_vulcan["Kod"] = df_vulcan["AdresSzkoly"].str.extract(r"(\d{2}-\d{3})")
    if KODY_FILE.exists():
        df_pc = pd.read_csv(KODY_FILE, dtype=str)
        df_vulcan = df_vulcan.merge(df_pc, how="left", on="Kod")
    else:
        df_vulcan["Dzielnica"] = None
    return df_vulcan


def attach_location_data(
    df_schools: pd.DataFrame,
    cfg: dict[str, Any],
    location_cache: pd.DataFrame | None = None,
) -> pd.DataFrame:
    df_schools = df_schools.copy()
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    should_fetch = bool(cfg.get("pobierz_nowe_czasy", True) and api_key)

    if should_fetch:
        try:
            import googlemaps

            df_schools["PelenAdres"] = (
                df_schools["NazwaSzkoly"].str.strip()
                + ", "
                + df_schools["AdresSzkoly"].str.strip()
            )
            addresses = df_schools["PelenAdres"].dropna().unique().tolist()
            client = googlemaps.Client(key=api_key)
            departure_timestamp = get_next_weekday_time(
                cfg.get("departure_hour", 7), cfg.get("departure_minute", 30)
            )
            travel_times = {}
            batch_size = cfg.get("googlemaps_batch_size", 25)
            for i in range(0, len(addresses), batch_size):
                batch = addresses[i : i + batch_size]
                travel_times.update(
                    get_travel_times_batch(
                        gmaps=client,
                        origin_address=cfg["adres_domowy"],
                        destination_addresses=batch,
                        mode="transit",
                        departure_time=departure_timestamp,
                    )
                )
                time.sleep(0.25)
            coordinates = get_coordinates_for_addresses_batch(client, addresses)
            df_schools["CzasDojazdu"] = df_schools["PelenAdres"].map(travel_times)
            df_schools["SzkolaLat"] = df_schools["PelenAdres"].map(
                lambda addr: coordinates.get(addr, (None, None))[0]
            )
            df_schools["SzkolaLon"] = df_schools["PelenAdres"].map(
                lambda addr: coordinates.get(addr, (None, None))[1]
            )
            df_schools.drop(columns=["PelenAdres"], inplace=True)
            df_schools[
                [
                    "SzkolaIdentyfikator",
                    "AdresSzkoly",
                    "CzasDojazdu",
                    "SzkolaLat",
                    "SzkolaLon",
                ]
            ].drop_duplicates().to_excel(CZASY_DOJAZDU_FILE, index=False)
            return df_schools
        except ImportError:
            logger.warning("Brak pakietu googlemaps; uzywam cache lokalizacji.")

    if location_cache is None or location_cache.empty:
        if CZASY_DOJAZDU_FILE.exists():
            location_cache = pd.read_excel(CZASY_DOJAZDU_FILE)
        else:
            location_cache = pd.DataFrame()

    if not location_cache.empty and "SzkolaIdentyfikator" in location_cache.columns:
        merge_key = "SzkolaIdentyfikator"
        if (
            "source_school_id" in df_schools.columns
            and "source_school_id" in location_cache.columns
            and location_cache["source_school_id"].notna().any()
        ):
            merge_key = "source_school_id"
        cols = [
            col
            for col in [
                merge_key,
                "CzasDojazdu",
                "SzkolaLat",
                "SzkolaLon",
            ]
            if col in location_cache.columns
        ]
        df_schools = df_schools.drop(
            columns=[col for col in cols if col != merge_key],
            errors="ignore",
        )
        df_schools = df_schools.merge(
            location_cache[cols].drop_duplicates(merge_key),
            on=merge_key,
            how="left",
        )

    for col in ["CzasDojazdu", "SzkolaLat", "SzkolaLon"]:
        if col not in df_schools.columns:
            df_schools[col] = None
    return df_schools


def add_common_class_columns(df_classes: pd.DataFrame) -> pd.DataFrame:
    df_classes = df_classes.copy()
    df_classes["Profil"] = (
        df_classes["OddzialNazwa"]
        .astype(str)
        .str.extract(r"\[[^\]]+\]\s*([^\(]+)")[0]
        .str.strip()
    )
    df_classes["TypOddzialu"] = df_classes["OddzialNazwa"].apply(extract_class_type)
    if "JezykiObce" in df_classes.columns:
        df_classes["JezykiObce"] = (
            df_classes["JezykiObce"]
            .fillna("")
            .astype(str)
            .str.replace("Pierwszy", "1", regex=False)
            .str.replace("Drugi", "2", regex=False)
            .str.replace("Trzeci", "3", regex=False)
            .str.replace("język", "", regex=False)
        )
    else:
        df_classes["JezykiObce"] = ""

    if "PrzedmiotyRozszerzone" not in df_classes.columns:
        df_classes["PrzedmiotyRozszerzone"] = ""
    for subject in ALL_SUBJECTS:
        pattern = rf"(?i)\b{subject}\b"
        df_classes[subject] = (
            df_classes["PrzedmiotyRozszerzone"]
            .fillna("")
            .astype(str)
            .str.contains(pattern, na=False)
            .astype(int)
        )
    return df_classes


def build_vulcan_year(
    year_cfg: dict[str, Any], cfg: dict[str, Any], location_cache: pd.DataFrame
) -> dict[str, pd.DataFrame]:
    df_vulcan = prepare_vulcan_offer(load_vulcan_offer(year_cfg), cfg)
    df_thresholds = load_thresholds(year_cfg)
    df_ranking = load_ranking(year_cfg)
    class_thresholds = best_thresholds_for_keys(
        df_thresholds,
        ["SzkolaIdentyfikator", "OddzialNazwa"],
    )

    df_classes = pd.merge(
        df_vulcan,
        class_thresholds[
            [
                "OddzialNazwa",
                "Prog_min_klasa",
                "SzkolaIdentyfikator",
                "threshold_year",
                "threshold_kind",
                "threshold_label",
            ]
        ],
        how="left",
        on=["SzkolaIdentyfikator", "OddzialNazwa"],
    )
    df_classes = pd.merge(
        df_classes,
        df_ranking[["RankingPoz", "RankingPozTekst", "SzkolaIdentyfikator"]],
        how="left",
        on="SzkolaIdentyfikator",
    )
    df_classes.drop(columns=["NazwaSzkoly_y"], errors="ignore", inplace=True)
    if "NazwaSzkoly_x" in df_classes.columns:
        df_classes.rename(columns={"NazwaSzkoly_x": "NazwaSzkoly"}, inplace=True)
    df_classes = _append_duplicate_suffix(df_classes)

    minmax = school_threshold_summary(df_thresholds)
    historical_thresholds = historical_school_thresholds(df_thresholds)
    df_schools = df_vulcan.drop_duplicates(
        subset=["SzkolaIdentyfikator", "NazwaSzkoly", "AdresSzkoly", "TypSzkoly"]
    )[
        [
            "SzkolaIdentyfikator",
            "source_school_id",
            "NazwaSzkoly",
            "AdresSzkoly",
            "TypSzkoly",
            "IdSzkoly",
            "Dzielnica",
        ]
    ].copy()
    df_schools = df_schools.merge(
        df_ranking[["SzkolaIdentyfikator", "RankingPoz", "RankingPozTekst"]],
        how="left",
        on="SzkolaIdentyfikator",
    )
    df_schools = df_schools.merge(minmax, how="left", on="SzkolaIdentyfikator")
    df_schools = df_schools.merge(
        historical_thresholds, how="left", on="SzkolaIdentyfikator"
    )
    df_schools = attach_location_data(df_schools, cfg, location_cache)
    df_schools["url"] = (
        "https://warszawa.edu.com.pl/kandydat/app/offer_school_details.xhtml?schoolId="
        + df_schools["IdSzkoly"].astype(str)
    )

    school_metric_cols = [
        "CzasDojazdu",
        "SzkolaLat",
        "SzkolaLon",
        "Prog_min_szkola",
        "Prog_max_szkola",
        "Prog_szkola_threshold_year",
        "Prog_szkola_threshold_kind",
        "Prog_szkola_threshold_label",
        "Progi_historyczne_szkola",
        "Progi_historyczne_lata",
    ]
    school_metric_keys = ["SzkolaIdentyfikator"]
    if (
        "source_school_id" in df_classes.columns
        and "source_school_id" in df_schools.columns
    ):
        school_metric_keys = ["source_school_id", "SzkolaIdentyfikator"]
    school_metrics = df_schools[
        school_metric_keys + school_metric_cols
    ].drop_duplicates(school_metric_keys)
    df_classes = df_classes.merge(
        school_metrics,
        how="left",
        on=school_metric_keys,
    )
    df_classes = add_common_class_columns(df_classes)

    threshold_info = threshold_meta(year_cfg)
    for df in [df_schools, df_classes, df_thresholds, df_ranking]:
        df["year"] = year_cfg["year"]
        df["admission_year"] = year_cfg.get("admission_year")
        df["school_year"] = year_cfg.get("school_year")
        df["data_status"] = year_cfg.get("data_status")
        df["status_label"] = year_cfg.get("status_label")
        df["threshold_mode"] = threshold_info["threshold_mode"]
        df["threshold_label"] = threshold_info["threshold_label"]
        df["threshold_years"] = threshold_info["threshold_years"]

    return {
        "schools": df_schools,
        "classes": df_classes,
        "thresholds": df_thresholds,
        "ranking": df_ranking,
        "plan": pd.DataFrame(),
    }


def _append_duplicate_suffix(df: pd.DataFrame) -> pd.DataFrame:
    school_key = "SzkolaIdentyfikator"
    if "source_school_id" in df.columns and df["source_school_id"].notna().any():
        school_key = "source_school_id"
    key = [school_key, "OddzialNazwa"]
    duplicate_no = df.groupby(key).cumcount()
    mask = duplicate_no > 0
    df.loc[mask, "OddzialNazwa"] = (
        df.loc[mask, "OddzialNazwa"] + " #" + (duplicate_no[mask] + 1).astype(str)
    )
    return df


def build_plan_year(
    year_cfg: dict[str, Any], cfg: dict[str, Any], location_cache: pd.DataFrame
) -> dict[str, pd.DataFrame]:
    plan_path = ensure_source_file(year_cfg["offer"])
    df_plan = load_plan_naboru(
        plan_path, year=year_cfg["year"], school_year=year_cfg.get("school_year")
    )
    df_thresholds = load_thresholds(year_cfg)
    df_ranking = load_ranking(year_cfg)

    df_plan["SzkolaIdentyfikator"] = df_plan["NazwaSzkoly"].apply(normalize_name)
    df_plan["source_school_id"] = (
        "plan:"
        + str(year_cfg["year"])
        + ":"
        + df_plan["SzkolaIdentyfikator"].astype(str)
    )
    df_plan["AdresSzkoly"] = df_plan["Ulica"].fillna("").astype(str) + ", Warszawa"

    minmax = school_threshold_summary(df_thresholds)
    historical_thresholds = historical_school_thresholds(df_thresholds)

    df_classes = df_plan.copy()
    detail = df_classes["ZawodLubJezyk"].fillna("").astype(str).str.strip()
    df_classes["OddzialNazwa"] = (
        "plan "
        + df_classes["TypOddzialu"].astype(str)
        + detail.map(lambda value: f" - {value}" if value else "")
    )
    df_classes = _append_duplicate_suffix(df_classes)
    df_classes["IdSzkoly"] = pd.NA
    df_classes["PrzedmiotyRozszerzone"] = ""
    df_classes["JezykiObce"] = df_classes["ZawodLubJezyk"].fillna("")
    df_classes["LiczbaMiejsc"] = df_classes["LiczbaMiejscPlan"]
    df_classes["UrlGrupy"] = pd.NA
    df_classes["Prog_min_klasa"] = pd.NA
    df_classes = df_classes.merge(minmax, how="left", on="SzkolaIdentyfikator")
    df_classes = df_classes.merge(
        historical_thresholds, how="left", on="SzkolaIdentyfikator"
    )
    df_classes = df_classes.merge(
        df_ranking[["SzkolaIdentyfikator", "RankingPoz", "RankingPozTekst"]],
        how="left",
        on="SzkolaIdentyfikator",
    )
    df_classes = add_common_class_columns(df_classes)

    agg = {
        "source_school_id": "first",
        "NazwaSzkoly": "first",
        "AdresSzkoly": "first",
        "TypSzkoly": "first",
        "Dzielnica": "first",
        "LiczbaOddzialowPlan": "sum",
        "LiczbaMiejscPlan": "sum",
    }
    df_schools = df_plan.groupby("SzkolaIdentyfikator", as_index=False).agg(agg)
    df_schools = df_schools.merge(
        df_ranking[["SzkolaIdentyfikator", "RankingPoz", "RankingPozTekst"]],
        how="left",
        on="SzkolaIdentyfikator",
    )
    df_schools = df_schools.merge(minmax, how="left", on="SzkolaIdentyfikator")
    df_schools = df_schools.merge(
        historical_thresholds, how="left", on="SzkolaIdentyfikator"
    )

    if not location_cache.empty:
        cache_cols = [
            col
            for col in [
                "SzkolaIdentyfikator",
                "AdresSzkoly",
                "CzasDojazdu",
                "SzkolaLat",
                "SzkolaLon",
                "url",
            ]
            if col in location_cache.columns
        ]
        df_schools = df_schools.merge(
            location_cache[cache_cols].drop_duplicates("SzkolaIdentyfikator"),
            how="left",
            on="SzkolaIdentyfikator",
            suffixes=("", "_cache"),
        )
        if "AdresSzkoly_cache" in df_schools.columns:
            df_schools["AdresSzkoly"] = df_schools["AdresSzkoly_cache"].combine_first(
                df_schools["AdresSzkoly"]
            )
            df_schools.drop(columns=["AdresSzkoly_cache"], inplace=True)

    for col in ["CzasDojazdu", "SzkolaLat", "SzkolaLon"]:
        if col not in df_schools.columns:
            df_schools[col] = None
    if "url" not in df_schools.columns:
        df_schools["url"] = "https://rekrutacje-warszawa.pzo.edu.pl"
    else:
        df_schools["url"] = df_schools["url"].fillna(
            "https://rekrutacje-warszawa.pzo.edu.pl"
        )

    df_classes = df_classes.merge(
        df_schools[
            [
                "SzkolaIdentyfikator",
                "CzasDojazdu",
                "SzkolaLat",
                "SzkolaLon",
                "url",
            ]
        ],
        how="left",
        on="SzkolaIdentyfikator",
        suffixes=("", "_szkola"),
    )

    threshold_info = threshold_meta(year_cfg)
    for df in [df_schools, df_classes, df_thresholds, df_ranking, df_plan]:
        df["year"] = year_cfg["year"]
        df["admission_year"] = year_cfg.get("admission_year")
        df["school_year"] = year_cfg.get("school_year")
        df["data_status"] = year_cfg.get("data_status")
        df["status_label"] = year_cfg.get("status_label")
        df["threshold_mode"] = threshold_info["threshold_mode"]
        df["threshold_label"] = threshold_info["threshold_label"]
        df["threshold_years"] = threshold_info["threshold_years"]

    return {
        "schools": df_schools,
        "classes": df_classes,
        "thresholds": df_thresholds,
        "ranking": df_ranking,
        "plan": df_plan,
    }


def process_year(
    year_cfg: dict[str, Any], cfg: dict[str, Any], location_cache: pd.DataFrame
) -> dict[str, pd.DataFrame]:
    offer_type = year_cfg["offer"]["type"]
    if offer_type == "vulcan_legacy":
        return build_vulcan_year(year_cfg, cfg, location_cache)
    if offer_type == "plan_naboru":
        return build_plan_year(year_cfg, cfg, location_cache)
    raise ValueError(f"Nieznany typ oferty: {offer_type}")


def validate_year_data(
    year_cfg: dict[str, Any], schools: pd.DataFrame, classes: pd.DataFrame
) -> dict[str, Any]:
    duplicate_count = 0
    school_key = (
        "source_school_id"
        if "source_school_id" in classes.columns
        else "SzkolaIdentyfikator"
    )
    duplicate_columns = {"year", school_key, "OddzialNazwa"}
    if duplicate_columns.issubset(classes.columns):
        duplicate_count = classes.duplicated(
            subset=["year", school_key, "OddzialNazwa"]
        ).sum()
    classes_with_threshold = (
        int(classes["Prog_min_klasa"].notna().sum())
        if "Prog_min_klasa" in classes
        else 0
    )
    classes_with_school_threshold = (
        int(classes["Prog_min_szkola"].notna().sum())
        if "Prog_min_szkola" in classes
        else 0
    )
    schools_with_threshold = (
        int(schools["Prog_min_szkola"].notna().sum())
        if "Prog_min_szkola" in schools
        else 0
    )
    threshold_info = threshold_meta(year_cfg)
    return {
        "year": year_cfg["year"],
        "school_year": year_cfg.get("school_year"),
        "data_status": year_cfg.get("data_status"),
        "status_label": year_cfg.get("status_label"),
        "threshold_mode": threshold_info["threshold_mode"],
        "threshold_label": threshold_info["threshold_label"],
        "threshold_years": threshold_info["threshold_years"],
        "schools_count": len(schools),
        "classes_count": len(classes),
        "schools_with_threshold": schools_with_threshold,
        "classes_with_threshold": classes_with_threshold,
        "classes_with_school_threshold": classes_with_school_threshold,
        "schools_without_district": (
            int(schools["Dzielnica"].isna().sum()) if "Dzielnica" in schools else 0
        ),
        "schools_without_ranking": (
            int(schools["RankingPoz"].isna().sum()) if "RankingPoz" in schools else 0
        ),
        "classes_without_threshold": (len(classes) - classes_with_threshold),
        "duplicate_class_keys": int(duplicate_count),
    }


def build_metadata(year_configs: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for year_cfg in year_configs:
        threshold_info = threshold_meta(year_cfg)
        rows.append(
            {
                "year": year_cfg["year"],
                "admission_year": year_cfg.get("admission_year"),
                "school_year": year_cfg.get("school_year"),
                "data_status": year_cfg.get("data_status"),
                "status_label": year_cfg.get("status_label"),
                "threshold_mode": threshold_info["threshold_mode"],
                "threshold_label": threshold_info["threshold_label"],
                "threshold_years": threshold_info["threshold_years"],
                "ranking_source": year_cfg.get("ranking", {}).get("source_url"),
                "threshold_source": threshold_info["threshold_source"],
                "offer_source": year_cfg.get("offer", {}).get("source_url"),
                "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
            }
        )
    return pd.DataFrame(rows)


def export_app_workbook(
    output_path: Path,
    datasets: list[dict[str, pd.DataFrame]],
    metadata: pd.DataFrame,
    quality: pd.DataFrame,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    def concat(name: str) -> pd.DataFrame:
        frames = [dataset[name] for dataset in datasets if not dataset[name].empty]
        clean_frames = [frame.dropna(axis=1, how="all") for frame in frames]
        clean_frames = [frame for frame in clean_frames if not frame.empty]
        return (
            pd.concat(clean_frames, ignore_index=True, sort=False)
            if clean_frames
            else pd.DataFrame()
        )

    sheets = {
        "metadata": metadata,
        "quality": quality,
        "schools": concat("schools"),
        "classes": concat("classes"),
        "rankings": concat("ranking"),
        "thresholds": concat("thresholds"),
        "plan_naboru": concat("plan"),
    }
    sheets = apply_latest_rankings(sheets)
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        for sheet_name, df in sheets.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)

    import openpyxl

    wb = openpyxl.load_workbook(output_path)
    for ws in wb.worksheets:
        if ws.max_row and ws.max_column:
            ws.auto_filter.ref = ws.dimensions
    wb.save(output_path)
    logger.info("Zapisano plik aplikacyjny: %s", output_path)


def run_pipeline(year: int | None = None) -> Path:
    cfg = project_config()
    sources = source_config()
    years_config = sources["years"]
    selected_configs = []
    for key, value in years_config.items():
        year_value = int(value.get("year", key))
        if year is None or year_value == year:
            value = value.copy()
            value["year"] = year_value
            selected_configs.append(value)
    if not selected_configs:
        raise ValueError(f"Nie znaleziono konfiguracji dla roku {year}")

    location_cache = load_location_cache()
    datasets = []
    quality_rows = []
    for year_cfg in selected_configs:
        logger.info("Przetwarzanie roku danych %s", year_cfg["year"])
        dataset = process_year(year_cfg, cfg, location_cache)
        datasets.append(dataset)
        quality_rows.append(
            validate_year_data(year_cfg, dataset["schools"], dataset["classes"])
        )

    output_path = resolve_path(sources["app_data_file"])
    export_app_workbook(
        output_path=output_path,
        datasets=datasets,
        metadata=build_metadata(selected_configs),
        quality=pd.DataFrame(quality_rows),
    )
    return output_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Buduje dane aplikacji Licea Warszawa")
    parser.add_argument(
        "--year",
        type=int,
        default=None,
        help="Rok danych do zbudowania. Brak wartosci buduje wszystkie lata z konfiguracji.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> Path:
    args = parse_args(argv)
    return run_pipeline(year=args.year)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s"
    )
    main()
