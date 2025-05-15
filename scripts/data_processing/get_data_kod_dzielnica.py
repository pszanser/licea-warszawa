import requests, pandas as pd
from bs4 import BeautifulSoup

BASE_URL = "https://www.kodypocztowe.info/warszawa"      # strona 1
LAST_PAGE = 670                                          # na dziś jest 670 podstron

def _rows_from_page(page: int) -> list[tuple[str,str]]:
    """Zwraca [(kod, dzielnica), ...] z pojedynczej podstrony."""
    url = BASE_URL if page == 1 else f"{BASE_URL}/page:{page}"
    html = requests.get(url, timeout=10).text
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    for tr in soup.select("tr._data"):                   # wiersze z danymi
        kod = tr.select_one("td.code-row").text.strip()
        dziel = tr.select("td")[2].text.strip()          # 3-cia kolumna
        rows.append((kod, dziel))
    return rows

def build_csv(out_path: str = "data/waw_kod_dzielnica.csv") -> pd.DataFrame:
    all_rows = []
    for p in range(1, LAST_PAGE + 1):
        all_rows.extend(_rows_from_page(p))
    df = (pd.DataFrame(all_rows, columns=["Kod", "Dzielnica"])
            .drop_duplicates()             # ten sam kod potrafi być na kilku ulicach
            .sort_values("Kod"))
    df.to_csv(out_path, index=False)
    print(f"Zapisano {len(df)} unikalnych kodów do {out_path}")
    return df

if __name__ == "__main__":
    build_csv()