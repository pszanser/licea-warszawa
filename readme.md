[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE) [![PRs welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/pszanser/licea-warszawa/pulls) ![CodeRabbit Pull Request Reviews](https://img.shields.io/coderabbit/prs/github/pszanser/licea-warszawa?utm_source=oss&utm_medium=github&utm_campaign=pszanser%2Flicea-warszawa&labelColor=171717&color=FF570A&link=https%3A%2F%2Fcoderabbit.ai&label=CodeRabbit+Reviews)
# Projekt: Wybór szkoły średniej w Warszawie i okolicach
Ten projekt służy do pobrania informacji o liceach, technikach i szkołach branżowych z systemu Vulcan,
połączenia z danymi o progach punktowych z poprzednich lat,
rankingiem Perspektyw, wyliczenia czasu dojazdu z Google Maps komunikają miejską
oraz generowania różnorodnych wizualizacji ułatwiających analizę.

**Interaktywna mapa** i wizualizację są dostępne na https://licea-warszawa.streamlit.app/

Posty na LinkedIn o procesie tworzenia:  
[1 - Python -> Excel](https://www.linkedin.com/posts/pszanser_sgh-liceum-edukacja-activity-7323984277598040065-8DO0)  
[2 - Excel -> Asystent AI](https://www.linkedin.com/posts/pszanser_asystent-ai-do-wyboru-liceum-w-warszawie-activity-7328660490576990209-5mo8)  
[3 - Excel -> Aplikacja z mapą](https://www.linkedin.com/posts/pszanser_liceum-edukacja-warszawa-activity-7328808246729658368-sw5m)  
[4 - Otwarty projekt](https://www.linkedin.com/posts/pszanser_github-opensource-python-activity-7330834756634411009-2hCz)  

Zapytaj Devina o to repozytorium:  
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/pszanser/licea-warszawa)

## Spis treści
- [Projekt: Wybór szkoły średniej w Warszawie i okolicach](#projekt-wybór-szkoły-średniej-w-warszawie-i-okolicach)
  - [Spis treści](#spis-treści)
  - [Struktura katalogów](#struktura-katalogów)
  - [Model danych wieloletnich](#model-danych-wieloletnich)
  - [Jak zacząć](#jak-zacząć)
  - [Główne funkcjonalności](#główne-funkcjonalności)
    - [Przetwarzanie danych](#przetwarzanie-danych)
    - [Wizualizacje i analizy](#wizualizacje-i-analizy)
    - [Interaktywna aplikacja Streamlit](#interaktywna-aplikacja-streamlit)
  - [Uwagi](#uwagi)
  - [Wykorzystywane biblioteki](#wykorzystywane-biblioteki)
    - [Analiza danych i obliczenia](#analiza-danych-i-obliczenia)
    - [Przetwarzanie plików](#przetwarzanie-plików)
    - [HTTP, API i web scraping](#http-api-i-web-scraping)
    - [Wizualizacja i mapowanie](#wizualizacja-i-mapowanie)
    - [Aplikacje webowe](#aplikacje-webowe)
  - [Współtworzenie](#współtworzenie)

## Struktura katalogów

```
.
├── data/                 # Katalog na pliki wejściowe
│   ├── raw/              # Surowe źródła według roku danych
│   │   ├── 2024/         # Historyczne progi punktowe
│   │   ├── 2025/         # Ranking i progi dla danych 2025
│   │   └── 2026/         # Ranking i plan naboru dla danych 2026
│   └── reference/        # Słowniki pomocnicze niezależne od roku danych
│       └── waw_kod_dzielnica.csv
├── gpts/                 # Pliki związane z GPTs 
│   └── `dane_kolumny_opis.md`  # Opis arkuszy i kolumn w pliku wynikowych Excel 
├── results/              # Katalog na pliki wynikowe
│   ├── app/              # Stabilny plik danych aplikacji
│   └── processed/        # Dane pośrednie używane przez pipeline
├── scripts/              # Katalog ze skryptami Python
│   ├── __init__.py
│   ├── main.py               # Główny skrypt uruchamiający przetwarzanie danych
│   ├── api_clients/          # Skrypty do interakcji z zewnętrznymi API
│   │   ├── __init__.py
│   │   └── googlemaps_api.py
│   ├── analysis/             # Skrypty do analizy danych i scoringu
│   │   ├── __init__.py
│   │   └── score.py
│   ├── config/               # Pliki konfiguracyjne i stałe
│   │   ├── __init__.py
│   │   ├── config.yml
│   │   └── constants.py
│   ├── data_processing/      # Skrypty do pobierania i przetwarzania danych
│   │   ├── __init__.py
│   │   ├── get_data_kod_dzielnica.py
│   │   ├── get_data_vulcan_async.py
│   │   ├── load_minimum_points.py
│   │   └── parser_perspektywy.py
│   ├── tests/                # Starsze testy przy skryptach
│   └── visualization/        # Skrypty do generowania wizualizacji i map
│       ├── __init__.py
│       ├── generate_map.py
│       ├── generate_visuals.py
│       ├── plots.py
│       └── streamlit_mapa_licea.py
├── tests/                # Główna suita testów pytest
├── requirements.txt      # Lista zależności Python
└── README.md             # Ten plik
```

## Model danych wieloletnich

Projekt buduje teraz jeden stabilny plik aplikacyjny:

```powershell
results/app/licea_warszawa.xlsx
```

Plik zawiera arkusze `metadata`, `quality`, `schools`, `classes`, `rankings`, `thresholds` i `plan_naboru`. Kluczowe kolumny roczne to:

*   `year` - rok danych prezentowanych w aplikacji, np. `2026`.
*   `admission_year` - rok rekrutacji/oferty, np. `2026`.
*   `school_year` - rok szkolny, np. `2026/2027`.
*   `source_school_id` - trwały identyfikator szkoły z konkretnego źródła danych.
*   `data_status` / `status_label` - informacja, czy dane są pełne, czy planistyczne.
*   `threshold_year` - rok źródłowy progu punktowego, np. `2025` albo `2024`.
*   `threshold_mode` / `threshold_label` - informacja, czy progi są faktyczne dla danego roku, czy referencyjne.
*   `Progi_historyczne_szkola` - lista znanych przedziałów progów szkoły według lat progów, pokazywana w szczegółach szkoły.
*   `RankingPoz` / `RankingRok` - najnowszy znany ranking Perspektyw używany przez filtry i wykresy.
*   `Ranking_historyczny_szkola` - lista znanych pozycji rankingowych szkoły według lat, pokazywana w szczegółach szkoły.

Źródła dla kolejnych lat są opisane w `scripts/config/data_sources.yml`. Obecnie:

*   `2025` używa pełnej oferty Vulcan, rankingu Perspektyw 2025 i faktycznych progów 2025 jako aktywnego źródła. Progi 2024 są zachowane jako historia/fallback.
*   `2026` używa rankingu Perspektyw 2026, planu naboru 2026/2027 oraz progów referencyjnych 2025/2024. To są dane planistyczne do czasu publikacji szczegółowej oferty klas i progów 2026.

Pipeline można uruchomić dla wszystkich lat albo dla jednego roku:

```powershell
python scripts/main.py
python scripts/main.py --year 2026
```

## Jak zacząć

1.  Sklonuj repozytorium lub pobierz paczkę .zip.
2.  Utwórz i aktywuj środowisko wirtualne (zalecane):
    *   Utwórz środowisko (jeśli jeszcze nie istnieje):
        ```powershell
        python -m venv .venv
        ```
    *   Aktywuj środowisko:
        ```powershell
        .venv\Scripts\activate
        ```
    *Po aktywacji, nazwa środowiska `(.venv)` powinna pojawić się na początku wiersza poleceń.*
3.  Zainstaluj zależności (upewnij się, że masz zainstalowany Python i pip oraz aktywne środowisko wirtualne):
    ```powershell
    pip install -r requirements.txt
    ```
    Zależności deweloperskie do walidacji lokalnej:
    ```powershell
    pip install -r requirements-dev.txt
    ```
    *W razie potrzeby zaktualizuj pakiety:*
    ```powershell
    pip install --upgrade -r requirements.txt
    ```
4.  Skonfiguruj projekt:
    *   Wypełnij `scripts/config/config.yml` swoimi danymi:
        *   `adres_domowy`: Twój adres domowy, z którego będą liczone czasy dojazdu.
        *   Opcjonalnie zmień `departure_hour` i `departure_minute` dla obliczeń czasu dojazdu.
        *   Ustaw `pobierz_nowe_czasy` na `True`, jeśli chcesz pobrać świeże dane o czasach dojazdu (domyślnie `True`).
        *   Ustaw `licz_score` na `True`, jeśli chcesz obliczyć złożony wskaźnik dla szkół.
        *   `filtr_miasto` i `filtr_typ_szkola` pozwalają wstępnie ograniczyć dane już na etapie `main.py`. Pozostaw pustą wartość, aby nie stosować filtrów.
5.  Umieść wymagane pliki w folderze `data/`.
6.  Uruchom główny skrypt przetwarzający dane (z katalogu głównego projektu, np. `Licea/`):
    ```powershell
    python scripts/main.py
    ```
    Główny plik aplikacyjny `results/app/licea_warszawa.xlsx` oraz pliki pośrednie pojawią się w folderze `results/`.
7.  Aby wygenerować wizualizacje:
    ```powershell
    python scripts/visualization/generate_visuals.py
    ```
    Wykresy zostaną zapisane w folderze `results/`.
8.  Aby wygenerować interaktywną mapę:
    ```powershell
    python scripts/visualization/generate_map.py
    ```
    Mapa `mapa_licea_warszawa.html` zostanie zapisana w folderze `results/`.
9.  Aby uruchomić interaktywną aplikację Streamlit z zaawansowanymi funkcjami opisanymi w sekcji "Główne funkcjonalności":
    ```powershell
    streamlit run scripts/visualization/streamlit_mapa_licea.py
    ```

    W Codex App w oknie **Run** możesz użyć jednego polecenia:
    ```powershell
    scripts\dev\run_full_app.cmd
    ```

## Główne funkcjonalności

### Przetwarzanie danych
*   **Pobieranie danych:** Automatyczne pobieranie danych o szkołach z systemu Vulcan
*   **Parsowanie rankingu Perspektyw:** Ekstrakcja danych z HTML/JS rankingu, z fallbackiem do PDF
*   **Wczytywanie progów punktowych:** Integracja z historycznymi danymi o progach w różnych formatach Excela
*   **Plan naboru:** Wczytywanie planu naboru 2026/2027 jako danych planistycznych
*   **Obliczanie czasów dojazdu:** Precyzyjne geokodowanie i kalkulacja czasu podróży przez Google Maps API
*   **Scoring:** Opcjonalny złożony wskaźnik oceny szkół

### Wizualizacje i analizy
*   **Statyczne wykresy:** Histogramy, wykresy korelacji, analizy rozkładów
*   **Interaktywna mapa:** Mapa z klastrowaniem znaczników, trybem pełnoekranowym, lokalizacją użytkownika i opcjonalną warstwą gęstości
*   **Nawigacja:** Klikalne adresy otwierające trasę w Google Maps

### Interaktywna aplikacja Streamlit
Zaawansowana aplikacja webowa z:
*   **Rozbudowanym panelem filtrów:** typ szkoły, ranking, nazwy, typy oddziałów, przedmioty rozszerzone, progi punktowe
*   **Przyciskiem resetowania** wszystkich filtrów
*   **Trzema zakładkami: "Mapa", "Moje dopasowanie" i "Wizualizacje"** dla lepszej organizacji
*   **Personalizowanym dopasowaniem (FitScore):** ważone scoring szkół po rankingu, marginesie do progu i odległości od punktu startowego (klik na mapie / środek widoku / adres z geokodowania Google)
*   **Metrykami podsumowującymi:** liczba szkół/klas, średni próg
*   **Eksportem do Excel** przefiltrowanych danych oraz wyników dopasowania
*   **Expandowaną listą szkół** z kluczowymi statystykami
*   **Interaktywnymi wykresami:** histogram progów, analiza dzielnic, korelacje rankingu, współwystępowanie rozszerzeń, wykresy bąbelkowe

## Uwagi
*   **Konfiguracja:** Kluczowe parametry działania znajdują się w `scripts/config/config.yml`
*   **Google Maps API:** Wymagany klucz API w zmiennej środowiskowej `GOOGLE_MAPS_API_KEY`
    ```powershell
    # Windows (na stałe):
    setx GOOGLE_MAPS_API_KEY twój_klucz_api
    
    # Tymczasowo (sesja):
    set GOOGLE_MAPS_API_KEY=twój_klucz_api
    ```
    Bez ustawionej zmiennej czasy dojazdu nie zostaną obliczone
*   **Odświeżenie danych:** Użyj flagi `pobierz_nowe_czasy` w pliku konfiguracyjnym

## Wykorzystywane biblioteki

### Analiza danych i obliczenia
* **NumPy** – Podstawowa biblioteka do obliczeń numerycznych, wielowymiarowe tablice i szybkie operacje matematyczne
* **pandas** – Manipulacja i analiza danych tabelarycznych (DataFrame), wczytywanie i przetwarzanie dużych zbiorów danych

### Przetwarzanie plików
* **openpyxl** – Odczyt i zapis arkuszy Excel (.xlsx)
* **pdfplumber** – Ekstrakcja tekstu i tabel z dokumentów PDF
* **PyYAML** – Parsowanie plików konfiguracyjnych YAML

### HTTP, API i web scraping
* **requests** – Synchroniczne zapytania HTTP
* **aiohttp** – Asynchroniczne zapytania HTTP dla lepszej wydajności
* **BeautifulSoup4** – Parsowanie HTML/XML do web scrapingu
* **googlemaps** – Klient Google Maps API (geokodowanie, trasy, odległości)

### Wizualizacja i mapowanie
* **matplotlib** – Podstawowe wykresy 2D
* **seaborn** – Estetyczne wykresy statystyczne (nakładka na matplotlib)
* **folium** – Interaktywne mapy Leaflet
* **streamlit-folium** – Integracja map Folium ze Streamlit

### Aplikacje webowe
* **Streamlit** – Framework do szybkiego tworzenia interaktywnych aplikacji webowych

## Współtworzenie

Chętnie przyjmę sugestie i poprawki. Jeśli masz pomysł na usprawnienie skryptów
lub uzupełnienie dokumentacji, otwórz issue albo wyślij pull request.
Każda forma dzielenia się wiedzą jest mile widziana!
