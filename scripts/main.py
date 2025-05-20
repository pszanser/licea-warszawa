import pandas as pd
import re, unicodedata
import os
from pathlib import Path
import sys

if __name__ == "__main__" and __package__ is None:
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path: 
        sys.path.insert(0, str(project_root))

import time
import datetime
import yaml
import logging
import asyncio

# Konfiguracja loggera
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

from scripts.data_processing.load_minimum_points import load_min_points
from scripts.data_processing.parser_perspektywy import parse_ranking_perspektywy_pdf  # lub parse_ranking_perspektywy_html
from scripts.api_clients.googlemaps_api import get_travel_times_batch, get_next_weekday_time, get_coordinates_for_addresses_batch
from scripts.analysis.score import add_metrics, compute_composite
from scripts.config.constants import ALL_SUBJECTS
import googlemaps

# --- Stałe i ścieżki plików ---
BASE_DIR = Path(__file__).resolve().parent.parent  # Główny katalog projektu Licea
DATA_DIR = BASE_DIR / "data"
RESULTS_DIR = BASE_DIR / "results"
SCRIPTS_DIR = BASE_DIR / "scripts" # Folder główny skryptów

with open(SCRIPTS_DIR / "config" / "config.yml", "r", encoding="utf-8") as f:
    CFG = yaml.safe_load(f)

# Upewnij się, że katalog results istnieje
RESULTS_DIR.mkdir(exist_ok=True)

VULCAN_FILE = RESULTS_DIR / "szkoly_vulcan.xlsx"
PUNKTY_FILE = DATA_DIR / "Minimalna liczba punktów 2024.xlsx"
RANKING_PDF_FILE = DATA_DIR / "ranking-licea-warszawskie-2025.pdf"
KODY_FILE = DATA_DIR / "waw_kod_dzielnica.csv"
RANKING_EXCEL_FILE = RESULTS_DIR / "ranking_perspektywy.xlsx"
CZASY_DOJAZDU_FILE = RESULTS_DIR / "czasy_dojazdu.xlsx"

ADRES_DOMOWY = CFG["adres_domowy"]
POBIERZ_NOWE_CZASY = CFG.get("pobierz_nowe_czasy", True)
DEPARTURE_HOUR = CFG.get("departure_hour", 7)
DEPARTURE_MINUTE = CFG.get("departure_minute", 30)
LICZ_SCORE = CFG.get("licz_score", False)
FILTR_MIASTO = CFG.get("filtr_miasto")
FILTR_TYP_SZKOLA = CFG.get("filtr_typ_szkola")

# Tworzenie nazwy pliku finalnego na podstawie adresu domowego
adres_bez_znakow = re.sub(r"\W+", "_", ADRES_DOMOWY).strip("_")
FINAL_SCHOOLS_FILE = RESULTS_DIR / f"LO_Warszawa_2025_{adres_bez_znakow}.xlsx"

REPL = {
    r"liceum og[oó]lnokszta[łl]c[a-ząćęłńóśźż]*": "lo",
    r"im(?:\.|ienia)?": "",       # im. / imienia  -> out
    r"i\.?i\.?": "ii",            # II LO edge-case
}

def normalize_name(name: str) -> str:
    if pd.isna(name): 
        return ""
    # 1. lowercase (nie usuwaj polskich znaków przed zamianą fraz!)
    x = name.lower()
    # 2. zastąp długie frazy (na oryginalnych znakach)
    for pat, rep in REPL.items():
        x = re.sub(pat, rep, x)
    # 3. usuwanie polskich znaków
    x = unicodedata.normalize("NFKD", x).encode("ascii", "ignore").decode()
    # 4. tylko litery/cyfry/spacja
    x = re.sub(r"[^a-z0-9 ]+", " ", x)
    # 5. pojedyncze spacje
    x = re.sub(r"\s+", " ", x).strip()
    # 6. numer + patron
    m = re.match(r"(?P<num>[ivxlcdm]+)\s+lo.*?(?P<patron>[a-z]+)$", x)
    if m:
        return f"{m['num']}_{m['patron']}"
    return x          # fallback (np. technikum)

# Dodaj typ szkoły (liceum, technikum, szkoła branżowa), na podstawie nazwy szkoły małymi literami
def get_school_type(name):
        name = name.lower()
        if "technikum" in name:
            return "technikum"
        elif "branżowa" in name :
            return "branżowa"
        else:
            return "liceum"

def wczytaj_dane_vulcan():
    """
    Wczytuje dane szkół z systemu Vulcan, pobierając je asynchronicznie lub wczytując z pliku cache.
    
    Jeśli plik z danymi nie istnieje, pobiera dane asynchronicznie i zapisuje je do pliku Excel; w przeciwnym razie wczytuje dane z istniejącego pliku. Zwraca DataFrame z danymi szkół.
    """
    t0 = time.perf_counter()
    if not VULCAN_FILE.exists():
        logger.info(f"Pobieranie danych z Vulcan (async)...")
        from scripts.data_processing.get_data_vulcan_async import download_all_async
        df_vulcan = asyncio.run(download_all_async(1, 400, verbose=True))
        df_vulcan.to_excel(VULCAN_FILE, index=False)
        logger.info(f"Zapisano dane Vulcan do {VULCAN_FILE}")
    else:
        logger.info(f"Wczytywanie danych Vulcan z {VULCAN_FILE}...")
        df_vulcan = pd.read_excel(VULCAN_FILE)
    t1 = time.perf_counter()
    logger.info(f"Czas pobierania/wczytywania danych Vulcan: {t1-t0:.2f} s")
    return df_vulcan

def przetworz_dane_vulcan(df_vulcan):
    t0 = time.perf_counter()
    df_vulcan["TypSzkoly"] = df_vulcan["NazwaSzkoly"].apply(get_school_type)
    # Opcjonalne filtrowanie danych na podstawie konfiguracji
    if FILTR_MIASTO:
        df_vulcan = df_vulcan[df_vulcan["AdresSzkoly"].str.contains(
            FILTR_MIASTO, na=False, case=False
        )]

    if FILTR_TYP_SZKOLA:
        typy = FILTR_TYP_SZKOLA
        if isinstance(typy, str):
            typy = [typy]
        df_vulcan = df_vulcan[df_vulcan["TypSzkoly"].isin(typy)]

    df_vulcan["SzkolaIdentyfikator"] = df_vulcan["NazwaSzkoly"].apply(normalize_name)
    df_vulcan["Kod"] = df_vulcan["AdresSzkoly"].str.extract(r"(\d{2}-\d{3})")
    df_pc = pd.read_csv(KODY_FILE, dtype=str)
    df_vulcan = df_vulcan.merge(df_pc, how="left", on="Kod")
    missing = df_vulcan["Dzielnica"].isna().sum()
    logger.warning(f"Brak przypisanej dzielnicy dla {missing} szkół")
    logger.info("Przykładowe dane Vulcan:")
    logger.info(f"\n{df_vulcan.head()}")
    t1 = time.perf_counter()
    logger.info(f"Czas przetwarzania danych Vulcan: {t1-t0:.2f} s")
    return df_vulcan

def wczytaj_progi():
    t0 = time.perf_counter()
    logger.info(f"Wczytywanie progów punktowych z {PUNKTY_FILE}...")
    try:
        df_punkty = load_min_points(PUNKTY_FILE)
        df_punkty["SzkolaIdentyfikator"] = df_punkty["NazwaSzkoly"].apply(normalize_name)
        logger.info("Przykładowe progi punktowe:")
        logger.info(f"\n{df_punkty.head()}")
    except FileNotFoundError:
        logger.error(f"BŁĄD: Nie znaleziono pliku z progami punktowymi: {PUNKTY_FILE}")
        return None
    t1 = time.perf_counter()
    logger.info(f"Czas wczytywania progów punktowych: {t1-t0:.2f} s")
    return df_punkty

def wczytaj_ranking():
    t0 = time.perf_counter()
    if not RANKING_EXCEL_FILE.exists() and RANKING_PDF_FILE.exists():
        logger.info(f"Parsowanie rankingu z PDF: {RANKING_PDF_FILE}...")
        df_rank = parse_ranking_perspektywy_pdf(RANKING_PDF_FILE)
        df_rank.to_excel(RANKING_EXCEL_FILE, index=False)
        logger.info(f"Zapisano ranking do {RANKING_EXCEL_FILE}")
    elif RANKING_EXCEL_FILE.exists():
        logger.info(f"Wczytywanie rankingu z {RANKING_EXCEL_FILE}...")
        df_rank = pd.read_excel(RANKING_EXCEL_FILE)
    else:
        logger.error(f"BŁĄD: Brak pliku rankingu PDF ({RANKING_PDF_FILE}) lub Excel ({RANKING_EXCEL_FILE}).")
        df_rank = pd.DataFrame(columns=["NazwaSzkoly", "RankingPoz", "Dzielnica"])
    t1 = time.perf_counter()
    logger.info(f"Czas wczytywania/parsowania rankingu: {t1-t0:.2f} s")
    df_rank["SzkolaIdentyfikator"] = df_rank["NazwaSzkoly"].apply(normalize_name)
    logger.info("Przykładowe dane rankingu:")
    logger.info(f"\n{df_rank.head()}")
    return df_rank

def polacz_dane(df_vulcan, df_punkty, df_rank):
    t0 = time.perf_counter()
    logger.info("Łączenie danych Vulcan z progami punktowymi...")
    df_merged = pd.merge(
        df_vulcan,
        df_punkty[["NazwaSzkoly", "OddzialNazwa", "Prog_min_klasa", "SzkolaIdentyfikator"]],
        how="left",
        on=["SzkolaIdentyfikator", "OddzialNazwa"]
    )
    logger.info("Łączenie danych z rankingiem...")
    df_merged = pd.merge(
        df_merged,
        df_rank[["RankingPoz", "SzkolaIdentyfikator"]],
        how="left",
        on=["SzkolaIdentyfikator"]
    )
    t1 = time.perf_counter()
    logger.info(f"Czas łączenia danych: {t1-t0:.2f} s")
    for col in ["NazwaSzkoly_y", "OddzialNazwa_y"]:
        if col in df_merged.columns:
            df_merged.drop(columns=[col], inplace=True)
    return df_merged

def oblicz_czasy_dojazdu(df_szkoly):
    t0 = time.perf_counter()
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        logger.warning("OSTRZEŻENIE: Brak klucza GOOGLE_MAPS_API_KEY w zmiennych środowiskowych. Pomijam obliczanie czasów dojazdu i współrzędnych.")
        df_szkoly["CzasDojazdu"] = None
        df_szkoly["SzkolaLat"] = None
        df_szkoly["SzkolaLon"] = None
    elif POBIERZ_NOWE_CZASY:
        logger.info(f"Pobieranie danych z Google Maps API dla adresu: {ADRES_DOMOWY}...")
        t_api_start = time.perf_counter()
        # łącz nazwy szkół z adresami, aby zwiększyć precyzję geokodowania
        df_szkoly["PelenAdres"] = (
            df_szkoly["NazwaSzkoly"].str.strip() + ", " + df_szkoly["AdresSzkoly"].str.strip()
        )
        destination_addresses = df_szkoly["PelenAdres"].unique().tolist()  # użyj unikalnych pełnych adresów
        logger.info(
            f"  Pobieranie czasów dojazdu dla {len(destination_addresses)} unikalnych adresów szkół"
        )
        gmaps_client = googlemaps.Client(key=api_key)
        
        # Pobieranie czasów dojazdu
        travel_times_dict = {}
        batch_size = CFG.get("googlemaps_batch_size", 25)
        departure_timestamp = get_next_weekday_time(DEPARTURE_HOUR, DEPARTURE_MINUTE)
        for i in range(0, len(destination_addresses), batch_size):
            batch_destinations = destination_addresses[i:i + batch_size]
            logger.info(f"  Pobieranie paczki czasów {i // batch_size + 1}/{ (len(destination_addresses) + batch_size - 1) // batch_size } ({len(batch_destinations)} adresów)")
            batch_travel_times = get_travel_times_batch(
                gmaps=gmaps_client,
                origin_address=ADRES_DOMOWY,
                destination_addresses=batch_destinations,
                mode="transit",
                departure_time=departure_timestamp
            )
            travel_times_dict.update(batch_travel_times)
            time.sleep(0.25) # Zgodnie z pierwotnym kodem
        
        df_szkoly["CzasDojazdu"] = df_szkoly["PelenAdres"].map(travel_times_dict)
        missing_travel_time_count = df_szkoly["CzasDojazdu"].isna().sum()
        if missing_travel_time_count > 0:
            logger.warning(f"OSTRZEŻENIE: {missing_travel_time_count} adresów nie ma przypisanego czasu dojazdu.")
        
        # Pobieranie współrzędnych
        logger.info(f"  Pobieranie współrzędnych dla {len(destination_addresses)} unikalnych adresów szkół")
        coordinates_dict = get_coordinates_for_addresses_batch(gmaps_client, destination_addresses)

        df_szkoly["SzkolaLat"] = df_szkoly["PelenAdres"].map(lambda addr: coordinates_dict.get(addr, (None, None))[0])
        df_szkoly["SzkolaLon"] = df_szkoly["PelenAdres"].map(lambda addr: coordinates_dict.get(addr, (None, None))[1])
        missing_coords_count = df_szkoly["SzkolaLat"].isna().sum() # Sprawdzamy tylko Lat, Lon powinien być NaN razem z Lat
        if missing_coords_count > 0:
            logger.warning(f"OSTRZEŻENIE: {missing_coords_count} adresów nie ma przypisanych współrzędnych.")

        t_api_end = time.perf_counter()
        logger.info(f"Czas pobierania danych z API (czasy i współrzędne): {t_api_end-t_api_start:.2f} s")
        
        logger.info(f"Zapisywanie czasów dojazdu i współrzędnych do {CZASY_DOJAZDU_FILE}...")
        # Upewnij się, że zapisujesz unikalne kombinacje SzkolaIdentyfikator/AdresSzkoly, jeśli df_szkoly może mieć duplikaty przed tym etapem
        # Na tym etapie df_szkoly zawiera unikalne szkoły, więc jest OK.
        # kolumna pomocnicza nie jest potrzebna w dalszych etapach
        df_to_save = df_szkoly[["SzkolaIdentyfikator", "AdresSzkoly", "CzasDojazdu", "SzkolaLat", "SzkolaLon"]].drop_duplicates()
        df_to_save.to_excel(CZASY_DOJAZDU_FILE, index=False)
        df_szkoly.drop(columns=["PelenAdres"], inplace=True)

    elif CZASY_DOJAZDU_FILE.exists():
        logger.info(f"Wczytywanie czasów dojazdu i współrzędnych z {CZASY_DOJAZDU_FILE}...")
        try:
            t_read_start = time.perf_counter()
            df_cache = pd.read_excel(CZASY_DOJAZDU_FILE)
            
            # Usuń stare kolumny, jeśli istnieją, aby uniknąć konfliktów przy merge
            cols_to_drop = ["CzasDojazdu", "SzkolaLat", "SzkolaLon"]
            for col in cols_to_drop:
                if col in df_szkoly.columns:
                    df_szkoly = df_szkoly.drop(columns=[col])
            
            # Dołącz dane z cache. Użyj AdresSzkoly jako klucza, jeśli SzkolaIdentyfikator może nie być w cache lub być niejednoznaczny
            # Jednak SzkolaIdentyfikator powinien być głównym kluczem, jeśli jest spójny.
            # Zakładając, że CZASY_DOJAZDU_FILE ma SzkolaIdentyfikator
            if "SzkolaIdentyfikator" in df_cache.columns:
                 df_szkoly = pd.merge(
                    df_szkoly,
                    df_cache[["SzkolaIdentyfikator", "CzasDojazdu", "SzkolaLat", "SzkolaLon"]],
                    how="left",
                    on="SzkolaIdentyfikator"
                )
            else: # Fallback na AdresSzkoly, jeśli plik cache jest starszy
                 df_szkoly = pd.merge(
                    df_szkoly,
                    df_cache[["AdresSzkoly", "CzasDojazdu", "SzkolaLat", "SzkolaLon"]], # Upewnij się, że te kolumny są w pliku
                    how="left",
                    on="AdresSzkoly"
                )

            # Jeśli kolumny SzkolaLat/Lon nie istnieją w pliku cache, zostaną utworzone z wartościami NaN
            if "SzkolaLat" not in df_szkoly.columns:
                df_szkoly["SzkolaLat"] = None
            if "SzkolaLon" not in df_szkoly.columns:
                df_szkoly["SzkolaLon"] = None

            t_read_end = time.perf_counter()
            logger.info(f"Czas wczytywania danych lokalizacyjnych z pliku: {t_read_end-t_read_start:.2f} s")
        except Exception as e:
            logger.error(f"BŁĄD podczas wczytywania lub łączenia danych lokalizacyjnych: {e}")
            df_szkoly["CzasDojazdu"] = None
            df_szkoly["SzkolaLat"] = None
            df_szkoly["SzkolaLon"] = None
    else:
        logger.warning(f"Plik {CZASY_DOJAZDU_FILE} nie istnieje i POBIERZ_NOWE_CZASY jest False. Brak danych o czasach dojazdu i współrzędnych.")
        df_szkoly["CzasDojazdu"] = None
        df_szkoly["SzkolaLat"] = None
        df_szkoly["SzkolaLon"] = None
    t1 = time.perf_counter()
    logger.info(f"Czas obsługi czasów dojazdu: {t1-t0:.2f} s")
    return df_szkoly

def zapisz_plik_excel(
    sciezka,
    df_info,
    df_szkoly,
    df_merged,
    df_rank,
    df_punkty,
    df_alg
):
    """Zapisuje wszystkie arkusze do pliku Excel i dodaje filtry do każdego arkusza."""
    logger.info(f"Zapisywanie finalnego pliku Excel do {sciezka}...")
    try:
        with pd.ExcelWriter(sciezka, engine="openpyxl") as writer:
            df_info.to_excel(writer, sheet_name="info", index=False)
            df_szkoly.to_excel(writer, sheet_name="szkoly", index=False)
            df_merged.to_excel(writer, sheet_name="klasy", index=False)
            df_rank.to_excel(writer, sheet_name="ranking", index=False)
            df_punkty.to_excel(writer, sheet_name="min pkt", index=False)
            # Dodaj ranking_alg tylko jeśli nie jest None i nie jest pusty
            if df_alg is not None and not (isinstance(df_alg, pd.DataFrame) and df_alg.empty):
                df_alg.to_excel(writer, sheet_name="ranking_alg", index=False)
        # Dodaj automatyczne filtry do wszystkich arkuszy
        import openpyxl
        wb = openpyxl.load_workbook(sciezka)
        for ws in wb.worksheets:
            ws.auto_filter.ref = ws.dimensions
        wb.save(sciezka)
        logger.info("Zakończono przetwarzanie i dodano filtry!")
    except Exception as e:
        logger.error(f"BŁĄD podczas zapisywania pliku Excel: {e}")


def main():

    total_start = time.perf_counter()

    # --- Wykonanie głównych kroków ---
    df_vulcan = wczytaj_dane_vulcan()
    df_vulcan = przetworz_dane_vulcan(df_vulcan)
    df_punkty = wczytaj_progi()
    if df_punkty is None:
        return
    df_rank = wczytaj_ranking()
    df_merged = polacz_dane(df_vulcan, df_punkty, df_rank)

    # 6. Przygotowanie danych dla arkuszy do Excela

    t0 = time.perf_counter()
    logger.info("Przygotowywanie danych do zapisu...")
    # Wylicz min/max punktów dla każdej szkoły na podstawie df_punkty
    minmax_punkty = (
        df_punkty.groupby("SzkolaIdentyfikator")["Prog_min_klasa"]
        .agg(["min", "max"])
        .reset_index()
        .rename(columns={"min": "Prog_min_szkola", "max": "Prog_max_szkola"})
    )

    # Unikalne szkoły z Vulcan (dodaj IdSzkoly)
    szkoly_vulcan = df_vulcan.drop_duplicates(subset=["SzkolaIdentyfikator", "NazwaSzkoly", "AdresSzkoly","TypSzkoly", "IdSzkoly"])[["SzkolaIdentyfikator", "NazwaSzkoly", "AdresSzkoly","TypSzkoly", "IdSzkoly", "Dzielnica"]]

    # Dodaj ranking
    szkoly_vulcan = pd.merge(
        szkoly_vulcan,
        df_rank[["SzkolaIdentyfikator","RankingPoz"]],
        how="left",
        on="SzkolaIdentyfikator"
    )

    # Dodaj min/max punktów
    df_szkoly = pd.merge(
        szkoly_vulcan,
        minmax_punkty,
        how="left",
        on="SzkolaIdentyfikator"
    )
    t1 = time.perf_counter()
    logger.info(f"Czas przygotowania danych do zapisu: {t1-t0:.2f} s")    # 7. Czasy dojazdu

    # Oblicz czasy dojazdu dla df_szkoly
    df_szkoly = oblicz_czasy_dojazdu(df_szkoly)

    # dodaj czas dojazdu do df_merged
    df_merged = pd.merge(
        df_merged,
        df_szkoly[["SzkolaIdentyfikator", "CzasDojazdu", "SzkolaLat", "SzkolaLon"]], # Dodaj SzkolaLat, SzkolaLon
        how="left",
        on="SzkolaIdentyfikator"
    )

    # dodaj kolumny PunktyOd, PunktyDo z df_szkoly
    df_merged = pd.merge(
        df_merged,
        df_szkoly[["SzkolaIdentyfikator", "Prog_min_szkola", "Prog_max_szkola"]],
        how="left",
        on="SzkolaIdentyfikator",
        suffixes=("", "_szkola")
    )

    # dodaj kolumnę Profil na podstawie OddzialNazwa, np. z "1a [O] geogr-ang-mat (ang-hisz,niem,ros)" ma być "geogr-ang-mat"
    # poprawka: obsługuje także przypadki jak "1D [I-o] h.szt.-ang-pol (ang-hisz*)"
    df_merged["Profil"] = (
        df_merged["OddzialNazwa"]
        .str.extract(r"\[[^\]]+\]\s*([^\(]+)")[0]  # wyciągnij tekst po [..] do nawiasu (lub końca)
        .str.strip()
    )

    # w kolumnie "JezykiObce" zamień "Pierwszy" na 1, "Drugi" na 2, "Trzeci" na 3, język na ""
    df_merged["JezykiObce"] = df_merged["JezykiObce"].str.replace("Pierwszy", "1").str.replace("Drugi", "2").str.replace("Trzeci", "3").str.replace("język", "")

    # --- TERAZ wywołaj add_metrics na df_merged, który już ma CzasDojazdu ---
    if LICZ_SCORE:
        df_alg = add_metrics(
            df_merged,
            P              = CFG["P"],
            desired_subject= CFG["desired_subject"]
        )

        df_alg = compute_composite(df_alg, w=CFG)

        # filtr ryzyka i top-rank
        df_alg = df_alg[
            (df_alg["AdmitMargin"] >= CFG["margin_min"]) &
            (df_alg["RankingPoz"]  <= CFG["rank_cutoff"])
        ]
    else:
        df_alg = None

    # Dodaj binarne kolumny dla przedmiotów rozszerzonych
    # ALL_SUBJECTS jest importowane na górze pliku z config.constants
    for subj in ALL_SUBJECTS:
        # wyszukuj całe wyrazy bez uwzględniania wielkości liter
        pattern = rf"(?i)\b{subj}\b"
        df_merged[subj] = df_merged["PrzedmiotyRozszerzone"].str.contains(pattern, na=False).astype(int)

    # zmień nazwę kolumny NazwaSzkoly_x na NazwaSzkoly
    if "NazwaSzkoly_x" in df_merged.columns:
        df_merged.rename(columns={"NazwaSzkoly_x": "NazwaSzkoly"}, inplace=True)
    # zmień nazwę kolumny "wiedza" na "wos"
    if "wiedza" in df_merged.columns:
        df_merged.rename(columns={"wiedza": "wos"}, inplace=True)

    # Zamień "Liceum Ogólnokształcące" na "LO" w kolumnie NazwaSzkoly dla obu DataFrame'ów
    for df in [df_merged, df_szkoly]:
        df["NazwaSzkoly"] = df["NazwaSzkoly"].str.replace("Liceum Ogólnokształcące", "LO", case=False)

    # Dodaj kolumnę url
    df_szkoly["url"] = "https://warszawa.edu.com.pl/kandydat/app/offer_school_details.xhtml?schoolId=" + df_szkoly["IdSzkoly"].astype(str)
    
    # posortuj df_szkoly wg czasu dojazdu malącego
    df_szkoly.sort_values(by="CzasDojazdu", ascending=True, inplace=True)

    # usuń kolumnę "IdSzkoly" z df_szkoly, bo nie jest potrzebna
    if "IdSzkoly" in df_szkoly.columns:
        df_szkoly.drop(columns=["IdSzkoly"], inplace=True)

    # Przygotuj dane dla arkusza "info"
    # jeżeli departure_timestamp jest None, to ustaw na aktualny czas
    departure_timestamp = get_next_weekday_time(DEPARTURE_HOUR, DEPARTURE_MINUTE)
    departure_datetime = datetime.datetime.fromtimestamp(departure_timestamp)
    departure_str = departure_datetime.strftime("%Y-%m-%d %H:%M")
    info_data = {
        "Opis": ["Adres początkowy", "Data i godzina wyjazdu (szacunkowa)", "Uwaga do czasów", "szkoly","klasy","ranking","min pkt"],
        "Wartość": [ADRES_DOMOWY, departure_str, "Szacunki czasów dojazdu mogą się różnić o +/- kilka minut.", "lista liceów w Warszawie 2025 z progami oraz rankingiem","lista klas w LO w Wwie 2025 z progami oraz rankingiem","ranking Perspektyw 2025","minimalna progi w roku 2024"],
    }
    df_info = pd.DataFrame(info_data)

    # 8. Zapisz finalny plik Excel

    t0 = time.perf_counter()
    zapisz_plik_excel(
        FINAL_SCHOOLS_FILE,
        df_info,
        df_szkoly,
        df_merged,
        df_rank,
        df_punkty,
        df_alg if LICZ_SCORE else None
    )
    t1 = time.perf_counter()
    logger.info(f"Czas zapisu pliku Excel: {t1-t0:.2f} s")

    total_end = time.perf_counter()
    logger.info(f"\nCałkowity czas wykonania: {total_end-total_start:.2f} s")

if __name__ == "__main__":
    main()