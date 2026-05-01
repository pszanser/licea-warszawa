[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE) [![PRs welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/pszanser/licea-warszawa/pulls) ![CodeRabbit Pull Request Reviews](https://img.shields.io/coderabbit/prs/github/pszanser/licea-warszawa?utm_source=oss&utm_medium=github&utm_campaign=pszanser%2Flicea-warszawa&labelColor=171717&color=FF570A&link=https%3A%2F%2Fcoderabbit.ai&label=CodeRabbit+Reviews)
# Projekt: Wybór szkoły średniej w Warszawie i okolicach
Ten projekt pomaga rodzicom i uczniom porównywać licea, technika i szkoły branżowe
w Warszawie i okolicach. Łączy historyczne dane oferty 2025 z systemu Vulcan,
aktualną oficjalną ofertę 2026/2027 z PZO/Omikron, progi punktowe z poprzednich
lat, ranking Perspektyw, języki obce, rozszerzenia oraz czasy dojazdu komunikacją
miejską z Google Maps. Wyniki są dostępne jako aplikacja Streamlit, plik Excel,
mapa i zestaw wizualizacji.

**Interaktywna mapa** i wizualizacje są dostępne na https://licea-warszawa.streamlit.app/

**Historia zmian**: [zobacz, co nowego w aplikacji](HISTORIA_ZMIAN.md)

Posty na LinkedIn o procesie tworzenia:  
[1 - Python -> Excel](https://www.linkedin.com/posts/pszanser_sgh-liceum-edukacja-activity-7323984277598040065-8DO0)  
[2 - Excel -> Asystent AI](https://www.linkedin.com/posts/pszanser_asystent-ai-do-wyboru-liceum-w-warszawie-activity-7328660490576990209-5mo8)  
[3 - Excel -> Aplikacja z mapą](https://www.linkedin.com/posts/pszanser_liceum-edukacja-warszawa-activity-7328808246729658368-sw5m)  
[4 - Otwarty projekt](https://www.linkedin.com/posts/pszanser_github-opensource-python-activity-7330834756634411009-2hCz)  
[5 - Aktualizacja danych 2025](https://www.linkedin.com/posts/pszanser_rok-temu-zrobi%C5%82em-narz%C4%99dzie-%C5%BCeby-pom%C3%B3c-synowi-activity-7453658959212666880-XR5I)  
[6 - Aktualizacja o ofertę 2026 i nowe funkcje](https://www.linkedin.com/posts/pszanser_edukacja-warszawa-liceum-activity-7455617098636070912-j3Gz)  

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
│   │   ├── 2025/         # Ranking, oferta Vulcan i progi dla danych 2025
│   │   └── 2026/         # Ranking i lokalny snapshot oficjalnej oferty PZO 2026
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
│   │   ├── get_data_pzo_omikron.py
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

Plik zawiera arkusze `metadata`, `quality`, `schools`, `classes`, `rankings`,
`thresholds`, `school_details`, `class_details` i `threshold_matches`.
Kluczowe kolumny roczne to:

*   `year` - rok danych prezentowanych w aplikacji, np. `2026`.
*   `admission_year` - rok rekrutacji/oferty, np. `2026`.
*   `school_year` - rok szkolny, np. `2026/2027`.
*   `source_school_id` - trwały identyfikator szkoły z konkretnego źródła danych.
*   `data_status` / `status_label` - informacja, czy dane są pełne, czy są oficjalną ofertą na kolejny rok.
*   `threshold_year` - rok źródłowy progu punktowego, np. `2025` albo `2024`.
*   `threshold_mode` / `threshold_label` - informacja, czy progi są faktyczne dla danego roku, czy referencyjne.
*   `Progi_historyczne_szkola` - lista znanych przedziałów progów szkoły według lat progów, pokazywana w szczegółach szkoły.
*   `RankingPoz` / `RankingRok` - najnowszy znany ranking Perspektyw używany przez filtry i wykresy.
*   `Ranking_historyczny_szkola` - lista znanych pozycji rankingowych szkoły według lat, pokazywana w szczegółach szkoły.
*   `source_class_id` - trwały identyfikator klasy/oddziału z konkretnego źródła danych.
*   `ProgUsedLevel` - opis, czy próg w aplikacji jest dokładnym/przybliżonym dopasowaniem klasy 2025, czy fallbackiem szkolnym.
*   `JezykiPierwszeNorm` / `JezykiDrugieNorm` - znormalizowane języki obce do filtrowania.
*   `JezykiPierwszePoziomy` / `JezykiDrugiePoziomy` - poziom języka, np. kontynuacja, od podstaw albo dwujęzyczny.

Źródła dla kolejnych lat są opisane w `scripts/config/data_sources.yml`. Obecnie:

*   `2025` używa pełnej oferty Vulcan, rankingu Perspektyw 2025 i faktycznych progów 2025 jako aktywnego źródła. Progi 2024 są zachowane jako historia/fallback.
*   `2026` używa oficjalnej publicznej oferty PZO/Omikron 2026/2027, rankingu Perspektyw 2026 oraz progów referencyjnych 2025/2024. Progi dla klas 2026 są dopasowywane do historycznych klas 2025, a przy braku mocnego dopasowania aplikacja pokazuje fallback do progu szkoły.

Surowy snapshot PZO (`data/raw/2026/pzo_omikron_2026_2027/`) oraz robocze pliki
pośrednie są lokalnymi artefaktami odtwarzalnymi z publicznego API i nie są
przeznaczone do commitowania. Do repozytorium trafia finalny plik aplikacji
`results/app/licea_warszawa.xlsx`.

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
*   **Pobieranie danych:** Automatyczne pobieranie danych o szkołach z systemu Vulcan dla 2025 oraz oficjalnej oferty PZO/Omikron dla 2026
*   **Parsowanie rankingu Perspektyw:** Ekstrakcja danych z HTML/JS rankingu, z fallbackiem do PDF
*   **Wczytywanie progów punktowych:** Integracja z historycznymi danymi o progach w różnych formatach Excela
*   **Oficjalna oferta 2026:** Wczytywanie publicznej oferty PZO/Omikron, w tym adresów, współrzędnych, kontaktów, opisów szkół i klas, języków, rozszerzeń oraz kryteriów punktowanych
*   **Obliczanie czasów dojazdu:** Precyzyjne geokodowanie i kalkulacja czasu podróży przez Google Maps API
*   **Scoring:** Opcjonalny złożony wskaźnik oceny szkół

### Wizualizacje i analizy
*   **Statyczne wykresy:** Histogramy, wykresy korelacji, analizy rozkładów
*   **Interaktywna mapa:** Mapa z klastrowaniem znaczników, trybem pełnoekranowym, lokalizacją użytkownika i opcjonalną warstwą gęstości
*   **Nawigacja:** Klikalne adresy szkół oraz linki dojazdu z wybranego punktu startowego otwierające trasę w Google Maps

### Interaktywna aplikacja Streamlit
Zaawansowana aplikacja webowa z:
*   **Przewodnikiem dla nowych użytkowników:** krótki onboarding w aplikacji dostępny jako zwijany panel pomocy
*   **Rozbudowanym panelem filtrów:** typ szkoły, ranking, nazwy, typy oddziałów, przedmioty rozszerzone, języki obce i progi punktowe
*   **Przyciskiem resetowania** wszystkich filtrów oraz stanu zakładki "Moje dopasowanie"
*   **Trzema zakładkami: "Mapa", "Moje dopasowanie" i "Wizualizacje"** dla lepszej organizacji
*   **Personalizowanym dopasowaniem (FitScore):** ważony scoring szkół po rankingu, marginesie do progu i odległości od punktu startowego (klik na mapie / środek widoku / adres z geokodowania Google). Jeśli dla ważonej składowej brakuje danych, np. rankingu albo progu, składowa liczy się jako `0` i jest pokazana w kolumnie **Braki danych**.
*   **Punktem startowym do porównań:** klik na mapie zapamiętuje pinezkę, środek widoku pozwala szybko użyć aktualnego kadru mapy, a adres można zgeokodować przez Google Maps API
*   **Linkami do rzeczywistego dojazdu:** popupy szkół i wyniki dopasowania mogą otworzyć gotową trasę komunikacją miejską z wybranego punktu startowego
*   **Szczegółami oferty 2026:** po wyborze szkoły na mapie aplikacja pokazuje pod mapą panel z ofertą 2026, opisem placówki, klasami 2025 z progami oraz szczegółami wybranej klasy
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
    Bez ustawionej zmiennej czasy dojazdu nie zostaną obliczone, a w aplikacji Streamlit nie będzie dostępne geokodowanie punktu startowego z wpisanego adresu. Klik na mapie, środek widoku i linki do tras w Google Maps działają bez klucza API.
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
