# Przewodnik dla Agentów - Licea Warszawa

## Przegląd Projektu
Ten projekt analizuje licea, technika i szkoły branżowe w Warszawie i okolicach. Integruje dane z systemu Vulcan, ranking Perspektyw, progi punktowe oraz czasy dojazdu z Google Maps API. Głównym produktem jest interaktywna aplikacja Streamlit z mapą i wizualizacjami.

## Struktura Katalogów i Obszary Robocze

### Główne katalogi robocze:
- **`scripts/`** - Cały kod źródłowy Python
  - `main.py` - punkt wejścia do przetwarzania danych
  - `api_clients/` - klienty zewnętrznych API (Google Maps)
  - `data_processing/` - pobieranie i przetwarzanie danych (Vulcan, Perspektywy, progi)
  - `analysis/` - analiza danych i scoring
  - `visualization/` - generowanie map i wykresów
  - `config/` - konfiguracja (`config.yml`, stałe)
- **`data/`** - pliki wejściowe (Excel, PDF, CSV)
- **`results/`** - pliki wynikowe (Excel, PNG, HTML)
- **`tests/`** - testy jednostkowe z pytest
- **`gpts/`** - dokumentacja dla asystentów AI

### Kluczowe pliki konfiguracyjne:
- `scripts/config/config.yml` - główna konfiguracja
- `requirements.txt` - zależności Python
- `pytest.ini` - konfiguracja testów

## Środowisko Deweloperskie

### Konfiguracja środowiska:
```powershell
# Utwórz i aktywuj środowisko wirtualne
python -m venv .venv
.venv\Scripts\activate

# Zainstaluj zależności
pip install -r requirements.txt
```

### Zmienne środowiskowe:
```powershell
# Google Maps API (wymagane dla czasów dojazdu)
setx GOOGLE_MAPS_API_KEY twój_klucz_api
```

### Główne punkty wejścia:
```powershell
# Przetwarzanie danych
python scripts/main.py

# Generowanie wizualizacji
python scripts/visualization/generate_visuals.py

# Generowanie mapy
python scripts/visualization/generate_map.py

# Aplikacja Streamlit
streamlit run scripts/visualization/streamlit_mapa_licea.py
```

## Testowanie

### Struktura testów:
- Testy znajdują się w katalogu `tests/`
- Konfiguracja pytest w `pytest.ini`
- Fixtures w `tests/fixtures/`
- Testy nazywane według wzorca `test_*.py`

### Uruchamianie testów:
```powershell
# Wszystkie testy
pytest

# Konkretny test
pytest tests/test_main_helpers.py

# Testy z pokryciem
pytest --cov=scripts

# Verbose output
pytest -v
```

### Dodawanie testów:
- Dodaj testy dla każdej nowej funkcjonalności
- Umieść test w odpowiednim pliku `test_*.py`
- Użyj fixtures z `conftest.py` dla wspólnych danych testowych
- Testuj zarówno pozytywne jak i negatywne scenariusze

## Zasady Kodowania

### Styl kodu:
- Używaj polskich nazw zmiennych i komentarzy (kontekst projektu)
- Zachowaj spójność z istniejącym stylem
- Dodawaj docstringi do funkcji i klas
- Używaj type hints gdzie to możliwe

### Struktura modułów:
- Każdy katalog w `scripts/` ma własny `__init__.py`
- Importy względne w ramach pakietu
- Eksportuj tylko publiczne API przez `__init__.py`

### Obsługa błędów:
- Używaj odpowiednich wyjątków
- Loguj błędy w krytycznych miejscach
- Graceful degradation dla opcjonalnych funkcji (np. Google Maps API)

## Walidacja Zmian

### Przed commitem:
1. **Uruchom testy**: `pytest`
2. **Sprawdź główne workflow**: 
   ```powershell
   python scripts/main.py
   python scripts/visualization/generate_visuals.py
   ```
3. **Testuj aplikację Streamlit**:
   ```powershell
   streamlit run scripts/visualization/streamlit_mapa_licea.py
   ```
4. **Sprawdź jakość kodu**: ustaw lintery jeśli potrzebne

## Praca z Danymi

### Źródła danych:
- **Vulcan API** - dane o szkołach (asynchroniczne pobieranie)
- **PDF Perspektyw** - ranking szkół (parsing PDF)
- **Excel z progami** - historyczne progi punktowe
- **Google Maps API** - geokodowanie i czasy dojazdu

### Formaty wyjściowe:
- **Excel** - główne pliki wynikowe z pełnymi danymi
- **HTML** - interaktywne mapy Folium
- **PNG** - statyczne wykresy matplotlib/seaborn
- **Streamlit** - interaktywna aplikacja webowa

### Obsługa danych:
- Wszystkie dane wejściowe w `data/`
- Wszystkie wyniki w `results/`
- Używaj pandas DataFrame jako głównej struktury danych
- Zachowuj oryginalne nazwy kolumn z systemów źródłowych

## Instrukcje dla PR

### Format tytułu:
`[obszar] Krótki opis zmian`

Przykłady:
- `[data] Dodanie parsera dla nowego formatu rankingu`
- `[viz] Nowy wykres analizy czasów dojazdu`
- `[api] Optymalizacja wywołań Google Maps API`
- `[tests] Testy dla modułu scoring`
- `[streamlit] Nowy filtr według typów oddziałów`

### Opis PR:
- Opisz problem który rozwiązujesz
- Wymień główne zmiany
- Podaj instrukcje testowania
- Dołącz screenshoty dla zmian UI/wizualizacji
- Nie używaj PL znaków w 'branch name' na Github

### Checklist przed PR:
- [ ] Testy przechodzą
- [ ] Dodano testy dla nowych funkcji  
- [ ] Sprawdzono główne workflow
- [ ] Aplikacja Streamlit działa poprawnie
- [ ] Zaktualizowano dokumentację jeśli potrzebne
- [ ] Sprawdzono czy zmiany nie psują istniejących funkcji

## Obszary Specjalne

### Google Maps API:
- Limit zapytań - używaj cache'owania
- Obsługa błędów API (brak klucza, przekroczenie limitów)
- Geokodowanie może być niedokładne - weryfikuj wyniki

### Async/Await (Vulcan API):
- Moduł `get_data_vulcan_async.py` używa aiohttp
- Pamiętaj o proper cleanup sesji
- Rate limiting dla API Vulcan

### Streamlit:
- Stan aplikacji w `st.session_state`
- Cache'owanie ciężkich operacji z `@st.cache_data`
- Responsywność map folium

### Pliki Excel:
- Używaj openpyxl do zapisu
- Zachowuj formatowanie (kolory, filtry)
- Dodawaj arkusze pomocnicze dla metadanych

## Kontekst Biznesowy

Projekt służy rodzicom uczniów wybierających szkołę średnią w Warszawie. Kluczowe czynniki:
- **Ranking** - jakość szkoły
- **Progi punktowe** - szanse dostania się
- **Czas dojazdu** - praktyczność
- **Przedmioty rozszerzone** - profil kształcenia

Przy wprowadzaniu zmian pamiętaj o tym kontekście i testuj z perspektywy użytkownika końcowego.
