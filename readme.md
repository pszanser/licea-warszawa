[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE) [![PRs welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/pszanser/licea-warszawa/pulls) ![CodeRabbit Pull Request Reviews](https://img.shields.io/coderabbit/prs/github/pszanser/licea-warszawa?utm_source=oss&utm_medium=github&utm_campaign=pszanser%2Flicea-warszawa&labelColor=171717&color=FF570A&link=https%3A%2F%2Fcoderabbit.ai&label=CodeRabbit+Reviews)
# Projekt: Wybór szkoły średniej w Warszawie i okolicach
Ten projekt służy do pobrania informacji o liceach, technikach i szkołach branżowych z systemu Vulcan,
połączenia z danymi o progach punktowych z poprzednich lat,
rankingiem Perspektyw, wyliczenia czasu dojazdu z Google Maps komunikają miejską
oraz generowania różnorodnych wizualizacji ułatwiających analizę.

**Interaktywna mapa** i wizualizację są dostępne na https://licea-warszawa-2025.streamlit.app/

Posty na LinkedIn o procesie tworzenia:  
[1 - Python -> Excel](https://www.linkedin.com/posts/pszanser_sgh-liceum-edukacja-activity-7323984277598040065-8DO0)  
[2 - Excel -> Asystent AI](https://www.linkedin.com/posts/pszanser_asystent-ai-do-wyboru-liceum-w-warszawie-activity-7328660490576990209-5mo8)  
[3 - Excel -> Aplikacja z mapą](https://www.linkedin.com/posts/pszanser_liceum-edukacja-warszawa-activity-7328808246729658368-sw5m)  


Zapytaj Devina o to repozytorium:  
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/pszanser/licea-warszawa)

## Spis treści
- [Projekt: Wybór szkoły średniej w Warszawie i okolicach](#projekt-wybór-szkoły-średniej-w-warszawie-i-okolicach)
  - [Spis treści](#spis-treści)
  - [Struktura katalogów](#struktura-katalogów)
  - [Jak zacząć](#jak-zacząć)
  - [Główne funkcjonalności](#główne-funkcjonalności)
  - [Uwagi](#uwagi)
  - [Wykorzystywane biblioteki](#wykorzystywane-biblioteki)
    - [1. Analiza danych i obliczenia](#1-analiza-danych-i-obliczenia)
    - [2. Przetwarzanie plików](#2-przetwarzanie-plików)
    - [3. HTTP, API i web scraping](#3-http-api-i-web-scraping)
    - [4. Wizualizacja i mapowanie](#4-wizualizacja-i-mapowanie)
    - [5. Budowa interaktywnych aplikacji (dashboardów)](#5-budowa-interaktywnych-aplikacji-dashboardów)
  - [Współtworzenie](#współtworzenie)

## Struktura katalogów

```
.
├── data/                 # Katalog na pliki wejściowe
│   ├── Minimalna liczba punktów 2024.xlsx
│   ├── ranking-licea-warszawskie-2025.pdf
│   └── waw_kod_dzielnica.csv
├── gpts/                 # Pliki związane z GPTs 
│   └── `dane_kolumny_opis.md`  # Opis arkuszy i kolumn w pliku wynikowych Excel 
├── results/              # Katalog na pliki wynikowe 
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
│   ├── tests/                # Testy
│   └── visualization/        # Skrypty do generowania wizualizacji i map
│       ├── __init__.py
│       ├── generate_map.py
│       ├── generate_visuals.py
│       ├── plots.py
│       └── streamlit_mapa_licea.py
├── requirements.txt      # Lista zależności Python
└── README.md             # Ten plik
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
    Główny plik wynikowy `LO_Warszawa_2025_{adres_bez_znakow_z_config}.xlsx` oraz pliki pośrednie pojawią się w folderze `results/`.
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
9.  Aby uruchomić interaktywną aplikację Streamlit z mapą i filtrami oraz wizualizacjami:
    ```powershell
    streamlit run scripts/visualization/streamlit_mapa_licea.py
    ```
    Aplikacja uruchomi się lokalnie i otworzy w domyślnej przeglądarce, umożliwiając interaktywną filtrację liceów.

## Główne funkcjonalności

*   **Pobieranie danych** Skrypt `main.py` (korzystając z `scripts/data_processing/get_data_vulcan_async.py`) automatycznie pobierze dane o szkołach z systemu Vulcan.
*   **Parsowanie rankingu Perspektyw:** Ranking jest parsowany z PDF (przez `scripts/data_processing/parser_perspektywy.py`).
*   **Wczytywanie progów punktowych:** Dane o progach wczytywane są przez `scripts/data_processing/load_minimum_points.py`.
*   **Obliczanie czasów dojazdu i geokodowanie:**
    *   Skrypt `main.py` (korzystając z `scripts/api_clients/googlemaps_api.py`) oblicza czasy dojazdu z adresu domowego (z `scripts/config/config.yml`).
    *   W zapytaniach do **Google Maps API** przekazywana jest pełna fraza zawierająca nazwę szkoły i jej adres, co zwiększa precyzję geokodowania.
*   **Normalizacja i łączenie danych:** 
*   **Filtrowanie:** 
*   **Scoring:** Opcjonalnie obliczany jest wskaźnik przez `scripts/analysis/score.py`.
*   **Generowanie wizualizacji:** Skrypt `scripts/visualization/generate_visuals.py` tworzy wykresy.
*   **Generowanie interaktywnej mapy:** Skrypt `scripts/visualization/generate_map.py` tworzy mapę.
*   **Grupowanie znaczników na mapie:** Dzięki `folium.plugins.MarkerCluster` ikony szkół łączą się w klastry, co zmniejsza bałagan wizualny i poprawia czytelność przy małym powiększeniu mapy.
*   **Tryb pełnoekranowy i przycisk "Znajdź mnie":** Mapa wykorzystuje wtyczki `Fullscreen` oraz `LocateControl`, pozwalając na wygodne przełączanie na pełny ekran i szybkie odnalezienie bieżącej lokalizacji użytkownika.
*   **Opcjonalna warstwa HeatMap:** Można włączyć podgląd gęstości szkół przyciskiem na mapie (w pliku HTML) lub checkboxem w aplikacji Streamlit.
*   **Nawigacja do szkoły:** W okienku informacji adres szkoły jest klikalny i otwiera Google Maps z trasą do wybranej placówki.
*   **Interaktywna aplikacja Streamlit:** Skrypt `scripts/visualization/streamlit_mapa_licea.py` uruchamia aplikację webową.

## Uwagi
*   **Konfiguracja:** Kluczowe parametry działania skryptów znajdują się w pliku `scripts/config/config.yml`.
*   **Google Maps API**: Wymagany klucz API w zmiennej środowiskowej `GOOGLE_MAPS_API_KEY`. 
    * **Zalecane:** Aby ustawić zmienną na stałe w systemie Windows (PowerShell lub CMD):
      ```powershell
      setx GOOGLE_MAPS_API_KEY twój_klucz_api
      ```
      Po ustawieniu otwórz nowe okno terminala, aby zmienna była widoczna.
    * Tymczasowo (tylko na czas bieżącej sesji):
      ```powershell
      set GOOGLE_MAPS_API_KEY=twój_klucz_api
      ```
    * W systemie Linux/MacOS (bash):
      ```bash
      export GOOGLE_MAPS_API_KEY=twój_klucz_api
      ```
    * **Uwaga:** Bez ustawionej zmiennej `GOOGLE_MAPS_API_KEY` czasy dojazdu nie zostaną obliczone i odpowiednie kolumny w plikach wynikowych pozostaną puste.
*   **Wymuszenie odświeżenia danych:** Zmodyfikuj flagę `pobierz_nowe_czasy` w `scripts/config/config.yml`.

## Wykorzystywane biblioteki

Poniżej grupuję wymienione biblioteki według głównych zastosowań i zamieszczam krótkie opisy każdej z nich.

### 1. Analiza danych i obliczenia

* **NumPy**
  Podstawowa biblioteka do obliczeń numerycznych w Pythonie – oferuje wielowymiarowe tablice (ndarray) oraz szybkie operacje matematyczne.
* **pandas**
  Rozbudowany zestaw narzędzi do manipulacji i analizy danych tabelarycznych (DataFrame), wczytywania/wykonywania operacji na dużych zbiorach danych.

### 2. Przetwarzanie plików

* **openpyxl**
  Odczyt i zapis arkuszy kalkulacyjnych Excel (.xlsx), umożliwia tworzenie, modyfikację i odczyt struktury skoroszytów.
* **pdfplumber**
  Ekstrakcja tekstu, tabel i metadanych z dokumentów PDF, pozwala na precyzyjne wydobywanie zawartości.
* **PyYAML**
  Parsowanie i generowanie plików w formacie YAML (konfiguracja, wymiana danych), proste mapowanie struktur Pythona ↔ YAML.

### 3. HTTP, API i web scraping

* **requests**
  Najpopularniejsza biblioteka do synchronizowanych zapytań HTTP (GET/POST itp.) – prosta i czytelna składnia.
* **aiohttp**
  Asynchroniczne klient–serwer HTTP, pozwala na równoległe wykonywanie wielu zapytań bez blokowania wątków.
* **BeautifulSoup4**
  Parsowanie i nawigacja po drzewie HTML/XML – ułatwia wydobywanie danych ze stron WWW po pobraniu ich np. przez `requests`.
* **googlemaps**
  Klient Pythona do Google Maps API: geokodowanie, obliczanie tras, odległości, wyszukiwanie miejsc itp.

### 4. Wizualizacja i mapowanie

* **matplotlib**
  Uniwersalna biblioteka do tworzenia wykresów 2D (linie, słupki, rozrzuty itd.) – fundament wielu innych narzędzi wizualizacyjnych.
* **seaborn**
  Nakładka na matplotlib, ułatwia tworzenie estetycznych wykresów statystycznych z prostą obsługą kolorów i stylów.
* **folium**
  Generowanie interaktywnych map Leaflet w Pythonie – dodawanie znaczników, warstw, obrysów i warstw geograficznych.
* **streamlit-folium**
  Komponent dla Streamlita, który pozwala łatwo osadzać i komunikować się z mapami stworzonymi za pomocą Folium.

### 5. Budowa interaktywnych aplikacji (dashboardów)

* **Streamlit**
  Prosty framework do szybkiego tworzenia interaktywnych aplikacji webowych (dashboardów, wizualizacji), bez konieczności znajomości front-endu.

## Współtworzenie

Chętnie przyjmę sugestie i poprawki. Jeśli masz pomysł na usprawnienie skryptów
lub uzupełnienie dokumentacji, otwórz issue albo wyślij pull request.
Każda forma dzielenia się wiedzą jest mile widziana!
