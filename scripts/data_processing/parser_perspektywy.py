# najprościej jest sobie skopiować te dane ze strony do MS Excel, dobrze to działa
# https://2025.licea.perspektywy.pl/rankingi/ranking-liceow-warszawskich

import pandas as pd
from bs4 import BeautifulSoup

def parse_ranking_perspektywy_html(html_file_path):
    """
    Odczytuje plik HTML z rankingiem Perspektyw i zwraca DataFrame
    z kolumnami: ["RankingPoz", "NazwaSzkoly", "Dzielnica", "WSK", ...].
    Należy dopasować do realnej struktury HTML.
    """
    with open(html_file_path, "r", encoding="utf-8") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")  # o ile jest <table>
    # Lub: soup.find("div", {"class":"ranking-table"}) – zależy od realnego kodu

    rows = table.find_all("tr")[1:]  # pomijamy nagłówek
    data = []

    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 6:
            continue
        poz = cells[0].get_text(strip=True)
        nazwa = cells[1].get_text(strip=True)
        dzielnica = cells[2].get_text(strip=True)
        hist24 = cells[3].get_text(strip=True)
        # itp.
        wsk = cells[6].get_text(strip=True) if len(cells)>6 else ""

        data.append([poz, nazwa, dzielnica, hist24, wsk])

    df = pd.DataFrame(data, columns=["RankingPoz", "NazwaSzkoly", "Dzielnica", "Historia24", "WSK"])
    return df


def parse_ranking_perspektywy_pdf(pdf_file_path):
    """
    Wariant: Gdy mamy ranking w PDF.
    Można użyć pdfplumber/tabula-py - poniżej tylko schemat.
    """
    import pdfplumber

    import re
    data_rows = []
    dzielnice = [
        "Bemowo", "Białołęka", "Bielany", "Mokotów", "Ochota", "Praga Płd.", "Praga Płn.", "Rembertów", "Śródmieście", "Targówek", "Ursus", "Ursynów", "Wawer", "Wesoła", "Wilanów", "Włochy", "Wola", "Żoliborz"
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
                        nazwa = (nazwa.rstrip() + dzielnica_kand.lstrip())

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
    # Przykład: odczyt z HTML
    df_html = parse_ranking_perspektywy_pdf("data/ranking-licea-warszawskie-2025.pdf")
    print(df_html.head())

    # Zapis
    df_html.to_excel("results/ranking_perspektywy.xlsx", index=False)

if __name__ == "__main__":
    main()