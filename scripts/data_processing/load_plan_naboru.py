import re

import pandas as pd

PLAN_COLUMN_RENAMES = {
    "Dzielnica": "Dzielnica",
    "Typ szkoły typ": "TypSzkolyZrodlo",
    "Nazwa szkoły": "NazwaSzkoly",
    "Ulica": "Ulica",
    "Typ oddziału": "TypOddzialu",
    "Zawód lub język w oddziałach dwujęzycznych": "ZawodLubJezyk",
}


def _flatten_columns(columns) -> list[str]:
    flattened = []
    for first, second in columns:
        first = "" if str(first).startswith("Unnamed") else str(first)
        second = "" if str(second).startswith("Unnamed") else str(second)
        name = re.sub(r"\s+", " ", f"{first} {second}").strip()
        flattened.append(name)
    return flattened


def _find_column(columns, phrase: str) -> str:
    phrase_lower = phrase.lower()
    matches = [col for col in columns if phrase_lower in str(col).lower()]
    if not matches:
        available = ", ".join(str(col) for col in columns)
        raise ValueError(
            f"Brak kolumny planu naboru zawierającej '{phrase}'. Dostępne kolumny: {available}"
        )
    return matches[0]


def _school_type_from_plan(value: str) -> str | None:
    value = str(value).strip()
    if value == "LO":
        return "liceum"
    if value == "T":
        return "technikum"
    if value.startswith("BS"):
        return "branżowa"
    return None


def load_plan_naboru(
    excel_path, year: int | None = None, school_year: str | None = None
):
    df_plan = pd.read_excel(excel_path, header=[1, 2])
    df_plan.columns = _flatten_columns(df_plan.columns)
    df_plan = df_plan.dropna(how="all").rename(columns=PLAN_COLUMN_RENAMES)

    classes_col = _find_column(df_plan.columns, "liczba oddziałów")
    seats_col = _find_column(df_plan.columns, "liczba miejsc")
    df_plan = df_plan.rename(
        columns={
            classes_col: "LiczbaOddzialowPlan",
            seats_col: "LiczbaMiejscPlan",
        }
    )

    required_columns = [
        "Dzielnica",
        "TypSzkolyZrodlo",
        "NazwaSzkoly",
        "Ulica",
        "TypOddzialu",
        "LiczbaOddzialowPlan",
        "LiczbaMiejscPlan",
    ]
    missing = [col for col in required_columns if col not in df_plan.columns]
    if missing:
        raise ValueError(f"Brak wymaganych kolumn planu naboru: {', '.join(missing)}")

    df_plan = df_plan.dropna(subset=["NazwaSzkoly", "TypOddzialu"]).copy()
    df_plan["TypSzkoly"] = df_plan["TypSzkolyZrodlo"].apply(_school_type_from_plan)
    df_plan["LiczbaOddzialowPlan"] = pd.to_numeric(
        df_plan["LiczbaOddzialowPlan"], errors="coerce"
    )
    df_plan["LiczbaMiejscPlan"] = pd.to_numeric(
        df_plan["LiczbaMiejscPlan"], errors="coerce"
    )
    if year is not None:
        df_plan["year"] = year
    if school_year is not None:
        df_plan["school_year"] = school_year
    return df_plan
