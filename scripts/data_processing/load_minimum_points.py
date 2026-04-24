import pandas as pd

MIN_POINTS_COLUMN_ALIASES = {
    "Minimalna": "Prog_min_klasa",
    "Najmniejsza liczba punktów kandydatów zakwalifikowanych": "Prog_min_klasa",
    "Nazwa szkoły": "NazwaSzkoly",
    "Nazwa krótka oddziału": "OddzialNazwa",
    "Symbol oddziału": "SymbolOddzialu",
    "Typ szkoły": "TypSzkolyZrodlo",
}


def _read_min_points_sheet(excel_path):
    """Reads either the old 2024 header layout or the newer direct-table layout."""
    raw = pd.read_excel(excel_path, header=None, nrows=5)
    first_row_values = {
        str(value).strip()
        for value in raw.iloc[0].dropna().tolist()
        if str(value).strip()
    }
    header = 0 if "Dzielnica" in first_row_values else 2
    return pd.read_excel(excel_path, header=header)


def load_min_points(excel_path, admission_year: int | None = None):
    df_punkty = _read_min_points_sheet(excel_path)
    df_punkty = df_punkty.rename(columns=MIN_POINTS_COLUMN_ALIASES)

    required_columns = ["NazwaSzkoly", "OddzialNazwa", "Prog_min_klasa"]
    missing = [col for col in required_columns if col not in df_punkty.columns]
    if missing:
        raise ValueError(
            f"Brak wymaganych kolumn progów punktowych: {', '.join(missing)}"
        )

    keep_columns = [
        col
        for col in [
            "Prog_min_klasa",
            "NazwaSzkoly",
            "OddzialNazwa",
            "Dzielnica",
            "TypSzkolyZrodlo",
            "SymbolOddzialu",
        ]
        if col in df_punkty.columns
    ]
    df_punkty = df_punkty[keep_columns].copy()
    df_punkty["Prog_min_klasa"] = pd.to_numeric(
        df_punkty["Prog_min_klasa"], errors="coerce"
    )
    df_punkty = df_punkty.dropna(subset=["NazwaSzkoly", "OddzialNazwa"])

    if admission_year is not None:
        df_punkty["admission_year"] = admission_year
    return df_punkty


def main():
    df = load_min_points("data/raw/2024/minimalna_liczba_punktow_2024.xlsx")
    print(df.head())


if __name__ == "__main__":
    main()
