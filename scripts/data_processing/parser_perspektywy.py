import html as html_lib
import logging
import re

import pandas as pd
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def _ranking_position_to_number(value):
    value = str(value).strip().replace("=", "")
    return pd.to_numeric(value, errors="coerce")


def _strip_html(value: str) -> str:
    soup = BeautifulSoup(html_lib.unescape(value), "html.parser")
    return soup.get_text(" ", strip=True)


def _parse_embedded_astro_ranking(html_text: str, year: int | None):
    """Parses the Perspektywy Astro payload embedded in HTML."""
    unescaped = html_lib.unescape(html_text)
    if year is None:
        year_match = re.search(r'"(20\d{2})":\[0,', unescaped)
        if year_match is None:
            return pd.DataFrame()
        year_key = year_match.group(1)
    else:
        year_key = str(year)
    pattern = re.compile(
        rf'"{year_key}":\[0,"?([^"\],]+)"?\]'
        r'.{0,500}?"name":\[0,"(.*?)"\]'
        r'.{0,300}?"dzielnica":\[0,"(.*?)"\]'
        r'.{0,300}?"wsk":\[0,"?([^"\],]+)"?\]',
        re.S,
    )
    rows = []
    seen = set()
    for match in pattern.finditer(unescaped):
        ranking_text, name_html, district, wsk = match.groups()
        name = _strip_html(name_html)
        key = (ranking_text, name, district)
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "RankingPoz": _ranking_position_to_number(ranking_text),
                "RankingPozTekst": ranking_text,
                "NazwaSzkoly": name,
                "Dzielnica": district,
                "WSK": pd.to_numeric(wsk, errors="coerce"),
            }
        )
    if not rows and year_key in unescaped and "dzielnica" in unescaped:
        logger.warning(
            "Nie znaleziono wierszy rankingu w osadzonym payloadzie Astro dla roku %s.",
            year_key,
        )
    return pd.DataFrame(rows)


def parse_ranking_perspektywy_html_text(html: str, year: int | None = None):
    """
    Odczytuje plik HTML z rankingiem Perspektyw i zwraca DataFrame
    z kolumnami: ["RankingPoz", "NazwaSzkoly", "Dzielnica", "WSK", ...].
    Należy dopasować do realnej struktury HTML.
    """
    embedded_df = _parse_embedded_astro_ranking(html, year=year)
    if not embedded_df.empty:
        if year is not None:
            embedded_df["year"] = year
        return embedded_df

    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    if table is None:
        columns = [
            "RankingPoz",
            "NazwaSzkoly",
            "Dzielnica",
            "Historia24",
            "WSK",
            "RankingPozTekst",
        ]
        if year is not None:
            columns.append("year")
        return pd.DataFrame(columns=columns)
    rows = table.find_all("tr")[1:]  # pomijamy nagłówek
    data = []

    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 3:
            continue
        poz = cells[0].get_text(strip=True)
        nazwa = cells[1].get_text(strip=True)
        dzielnica = cells[2].get_text(strip=True)
        hist24 = cells[3].get_text(strip=True) if len(cells) > 3 else ""
        wsk = cells[-1].get_text(strip=True) if len(cells) > 4 else ""

        data.append([poz, nazwa, dzielnica, hist24, wsk])

    df = pd.DataFrame(
        data, columns=["RankingPoz", "NazwaSzkoly", "Dzielnica", "Historia24", "WSK"]
    )
    df["RankingPozTekst"] = df["RankingPoz"].astype(str)
    df["RankingPoz"] = df["RankingPoz"].apply(_ranking_position_to_number)
    if year is not None:
        df["year"] = year
    return df


def parse_ranking_perspektywy_html(html_file_path, year: int | None = None):
    with open(html_file_path, "r", encoding="utf-8") as f:
        html = f.read()
    return parse_ranking_perspektywy_html_text(html, year=year)


def parse_ranking_perspektywy_pdf(pdf_file_path):
    """
    Wariant: Gdy mamy ranking w PDF.
    Można użyć pdfplumber/tabula-py - poniżej tylko schemat.
    """
    import pdfplumber

    import re

    data_rows = []
    dzielnice = [
        "Bemowo",
        "Białołęka",
        "Bielany",
        "Mokotów",
        "Ochota",
        "Praga Płd.",
        "Praga Płn.",
        "Rembertów",
        "Śródmieście",
        "Targówek",
        "Ursus",
        "Ursynów",
        "Wawer",
        "Wesoła",
        "Wilanów",
        "Włochy",
        "Wola",
        "Żoliborz",
    ]
    with pdfplumber.open(pdf_file_path) as pdf:
        for page in pdf.pages:
            table = page.extract_table()
            if not table:
                continue
            for row in table[1:]:  # pomijamy nagłówek
                poz = str(row[0]).strip()
                # Pobierz nazwę szkoły z drugiej kolumny (lub połącz 2 i 3 jeśli trzecia nie jest dzielnicą)
                nazwa = str(row[1]).strip() if len(row) > 1 and row[1] else ""
                dzielnica = ""
                # Jeśli trzecia kolumna istnieje i pasuje do dzielnic, to ją ustaw
                if len(row) > 2 and row[2]:
                    dzielnica_kand = str(row[2]).strip()
                    if dzielnica_kand in dzielnice:
                        dzielnica = dzielnica_kand
                    else:
                        # Jeśli trzecia kolumna nie jest dzielnicą, może to druga część nazwy szkoły
                        nazwa = nazwa.rstrip() + dzielnica_kand.lstrip()

                if not dzielnica and len(row) > 3:
                    for extra_col in row[3:]:
                        extra_val = str(extra_col).strip()
                        if extra_val in dzielnice:
                            dzielnica = extra_val
                            break
                # Sprawdź czy poz to liczba od 1 do 100 i czy nazwa nie jest pusta
                if re.fullmatch(r"[1-9][0-9]?|100", poz) and nazwa:
                    data_rows.append([poz, nazwa, dzielnica])

    df = pd.DataFrame(data_rows, columns=["RankingPoz", "NazwaSzkoly", "Dzielnica"])
    df["RankingPoz"] = pd.to_numeric(df["RankingPoz"], errors="coerce")
    return df


def main():
    # Przykład: odczyt z PDF
    df_pdf = parse_ranking_perspektywy_pdf(
        "data/raw/2025/ranking_liceow_warszawskich_2025.pdf"
    )
    print(df_pdf.head())

    # Zapis
    df_pdf.to_excel("results/ranking_perspektywy.xlsx", index=False)


if __name__ == "__main__":
    main()
