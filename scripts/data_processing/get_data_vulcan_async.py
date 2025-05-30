import asyncio
import aiohttp
import pandas as pd
from bs4 import BeautifulSoup

GROUP_LIST_TITLE = "Lista grup rekrutacyjnych/oddziałów"
INTERNAL_ERROR_TITLE = "Wewnętrzny błąd aplikacji"
COLUMNS = [
    "IdSzkoly",
    "NazwaSzkoly",
    "AdresSzkoly",
    "OddzialNazwa",
    "PrzedmiotyRozszerzone",
    "JezykiObce",
    "LiczbaMiejsc",
    "UrlGrupy",
]

SEM = asyncio.Semaphore(32)  # max równoczesnych żądań


def parse_school_html(html, school_id):
    soup = BeautifulSoup(html, "html.parser")
    error_h2 = soup.find("h2", string=INTERNAL_ERROR_TITLE)
    if error_h2:
        return []
    h2_oferta = soup.find("h2", string=lambda t: t and "Oferta szkoły" in t)
    school_name = ""
    school_address = ""
    if h2_oferta:
        ptr = h2_oferta
        lines_found = []
        while ptr and ptr.name != "h3":
            ptr = ptr.next_sibling
            if ptr and getattr(ptr, "string", None) and ptr.string.strip():
                lines_found.append(ptr.string.strip())
        if len(lines_found) >= 2:
            school_name = lines_found[0]
            school_address = lines_found[1]
    table_header = soup.find("h3", string=GROUP_LIST_TITLE)
    if not table_header:
        return []
    table = table_header.find_next("table")
    if not table:
        return []
    tbody = table.find("tbody")
    if not tbody:
        return []
    rows = tbody.find_all("tr")
    if not rows:
        return []
    results = []
    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 4:
            continue
        a_tag = cells[0].find("a")
        oddzial_nazwa = a_tag.get_text(strip=True) if a_tag else ""
        url_grupy = a_tag["href"] if a_tag else ""
        if url_grupy:
            url_grupy = f"https://warszawa.edu.com.pl{url_grupy}"
        przedmioty_rozszerzone = cells[1].get_text(separator=" ").strip()
        jezyki_obce = cells[2].get_text(separator=" ").strip()
        liczba_miejsc = cells[3].get_text(strip=True)
        results.append(
            [
                school_id,
                school_name,
                school_address,
                oddzial_nazwa,
                przedmioty_rozszerzone,
                jezyki_obce,
                liczba_miejsc,
                url_grupy,
            ]
        )
    return results


async def fetch_school(session, school_id):
    url = f"https://warszawa.edu.com.pl/kandydat/app/offer_school_details.xhtml?schoolId={school_id}"
    async with SEM, session.get(url) as r:
        if r.status != 200:
            return []
        html = await r.text()
        return parse_school_html(html, school_id)


async def download_all_async(start_id=1, end_id=400, verbose=True):
    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=60)
    ) as session:
        tasks = [fetch_school(session, i) for i in range(start_id, end_id + 1)]
        all_rows = []
        for i, task in enumerate(asyncio.as_completed(tasks), start=start_id):
            rows = await task
            if verbose and (i - start_id) % 10 == 0:
                print(f"Pobrano schoolId={i}")
            all_rows.extend(rows)
    df = pd.DataFrame(all_rows, columns=COLUMNS)
    # Sortowanie po IdSzkoly (jako liczba) i OddzialNazwa (alfabetycznie)
    df["IdSzkoly"] = pd.to_numeric(df["IdSzkoly"], errors="coerce")
    df = df.sort_values(["IdSzkoly", "OddzialNazwa"]).reset_index(drop=True)
    return df


def main():
    df = asyncio.run(download_all_async(1, 400, verbose=True))
    print(f"Łączna liczba wierszy = {len(df)}")
    df.to_excel("results/szkoly_vulcan_async.xlsx", index=False)
    print("Zapisano do szkoly_vulcan_async.xlsx")


if __name__ == "__main__":
    main()
