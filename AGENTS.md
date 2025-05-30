# Przewodnik dla Agentów - Licea Warszawa

**Cel tego dokumentu:** Ten plik (`AGENTS.MD`) służy jako Twój główny przewodnik do pracy w tym repozytorium. Zawiera kluczowe informacje o strukturze projektu, konfiguracji środowiska, standardach kodowania, testowaniu i sposobie prezentowania wyników Twojej pracy. Przestrzegaj go uważnie, aby Twoje zmiany były spójne i wysokiej jakości.

## Przegląd Projektu
Ten projekt analizuje licea, technika i szkoły branżowe w Warszawie i okolicach. Integruje dane z systemu Vulcan, ranking Perspektyw, progi punktowe oraz czasy dojazdu z Google Maps API. Głównym produktem jest interaktywna aplikacja Streamlit z mapą i wizualizacjami.
**Twoim nadrzędnym celem jest pomoc w rozwijaniu i utrzymaniu tego projektu, mając na uwadze jego końcowych użytkowników: rodziców i uczniów wybierających szkołę.**

## Zasady Pracy Agenta

*   **Zrozumienie Kontekstu**:
    *   Zapoznaj się z `scripts/config/config.yml` oraz `scripts/main.py`, aby zrozumieć główny przepływ danych i konfigurację.
    *   Sekcja `Kontekst Biznesowy` na końcu tego dokumentu wyjaśnia cel projektu – miej go na uwadze.
*   **Weryfikacja Pracy**:
    *   **Zawsze uruchamiaj testy (`pytest`)** po wprowadzeniu zmian, aby upewnić się, że niczego nie zepsułeś. Dąż do tego, aby wszystkie testy przechodziły.
    *   **Proaktywnie dodawaj testy** dla nowych lub zmodyfikowanych funkcjonalności, nawet jeśli nie zostało to bezpośrednio zlecone. Zobacz sekcję `Testowanie`.
    *   Używaj skonfigurowanych linterów i formatterów (np. Black, Flake8), jeśli są dostępne. Jeśli nie, stosuj się do PEP 8 i istniejącego stylu kodu.
*   **Dokumentacja**:
    *   Aktualizuj komentarze w kodzie oraz docstringi funkcji/klas, jeśli wprowadzasz zmiany w logice.
*   **Komunikacja i Prezentacja Zmian**:
    *   Przygotowując Pull Request (PR), ściśle przestrzegaj formatu opisanego w sekcji `Instrukcje dla PR`.
    *   Jeśli zostaniesz poproszony o analizę, dostarczaj wnioski poparte danymi. Rozważ wygenerowanie odpowiednich wizualizacji, jeśli to pomoże zilustrować wyniki.
*   **Dostęp do Sieci**:
    *   Pamiętaj, że dostęp do internetu może być ograniczony (np. tylko podczas fazy instalacji zależności). Wszystkie potrzebne pakiety powinny być zdefiniowane w `requirements.txt`.

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
Upewnij się, że pracujesz w skonfigurowanym środowisku Python. Główne polecenie instalacji zależności to:
```powershell
# Zainstaluj zależności
pip install -r requirements.txt
```
Jeśli tworzysz nowe środowisko:
```powershell
# Utwórz i aktywuj środowisko wirtualne (przykład dla lokalnego dewelopera)
python -m venv .venv
.venv\\Scripts\\activate # Dla Windows
# source .venv/bin/activate # Dla Linux/macOS

pip install -r requirements.txt
```

### Zmienne środowiskowe:
Kluczową zmienną środowiskową jest `GOOGLE_MAPS_API_KEY`. **Musisz mieć ją ustawioną w swoim środowisku wykonawczym, aby funkcje związane z Google Maps działały poprawnie.**
Przykład dla lokalnego dewelopera (Windows):
```powershell
# Google Maps API (wymagane dla czasów dojazdu)
setx GOOGLE_MAPS_API_KEY twój_klucz_api
```
W środowisku kontenerowym (np. Docker), zmienna ta musi być przekazana do kontenera.

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
- Testy nazywane według wzorca `test_*.py`

### Uruchamianie testów:
Użyj `pytest` do uruchamiania testów.
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
**Twoim obowiązkiem jest upewnienie się, że wszystkie testy przechodzą pomyślnie po Twoich modyfikacjach.**

### Dodawanie testów:
-   Dodawaj testy dla każdej nowej lub zmodyfikowanej funkcjonalności. Jest to kluczowe dla utrzymania jakości kodu.
-   Umieść test w odpowiednim pliku `test_*.py`
-   Użyj fixtures z `conftest.py` dla wspólnych danych testowych
-   Testuj zarówno pozytywne jak i negatywne scenariusze

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

**Zanim zgłosisz swoje zmiany (np. w formie Pull Requestu), jako agent MUSISZ przeprowadzić następujące kroki walidacyjne, aby upewnić się, że Twoje modyfikacje są poprawne i nie wprowadzają regresji:**

1.  **Sformatuj kod:** Użyj skonfigurowanego formatera, aby zapewnić spójność stylu.
    ```powershell
    black .
    ```
2.  **Uruchom linter:** Sprawdź kod pod kątem błędów stylistycznych i potencjalnych problemów.
    ```powershell
    flake8 scripts tests
    ```
3.  **Sprawdź typy statyczne:** Jeśli projekt używa adnotacji typów, zweryfikuj ich poprawność.
    ```powershell
    mypy scripts
    ```
    Upewnij się, że nie ma nowych błędów typowania.
4.  **Uruchom wszystkie testy jednostkowe i integracyjne:**
    ```powershell
    pytest
    ```
    Wszystkie testy muszą zakończyć się sukcesem.
5.  **Sprawdź główne przepływy pracy projektu:** Uruchom kluczowe skrypty, aby zweryfikować ich poprawne działanie z Twoimi zmianami.
    ```powershell
    python scripts/main.py
    python scripts/visualization/generate_visuals.py
    ```
6.  **Przetestuj aplikację Streamlit** (jeśli Twoje zmiany mogły na nią wpłynąć):
    ```powershell
    streamlit run scripts/visualization/streamlit_mapa_licea.py
    ```
    Sprawdź interakcję użytkownika i poprawność wyświetlanych danych w aplikacji.

Upewnij się, że wszystkie powyższe kroki zostały wykonane i zakończyły się pomyślnie przed utworzeniem Pull Requestu lub zgłoszeniem zakończenia zadania.

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
Jako agent, będziesz prawdopodobnie tworzyć Pull Requesty (PR) z proponowanymi zmianami. Przestrzegaj poniższych zasad:

### Format tytułu:
`[obszar] Krótki opis zmian`

Przykłady:
- `[data] Dodanie parsera dla nowego formatu rankingu`
- `[viz] Nowy wykres analizy czasów dojazdu`
- `[api] Optymalizacja wywołań Google Maps API`
- `[tests] Testy dla modułu scoring`
- `[streamlit] Nowy filtr według typów oddziałów`

### Opis PR:
-   Opisz problem, który rozwiązujesz lub funkcjonalność, którą dodajesz.
-   Wymień główne wprowadzone zmiany.
-   Podaj kroki niezbędne do przetestowania Twoich zmian (jeśli wykraczają poza standardową walidację).
-   Dołącz screenshoty dla zmian w interfejsie użytkownika lub wizualizacjach, jeśli to możliwe i zasadne.
-   Nie używaj polskich znaków diakrytycznych w nazwie brancha na GitHub.

### Checklist przed utworzeniem PR (dla Ciebie, Agencie):
Upewnij się, że:
- [ ] Wszystkie testy jednostkowe i integracyjne przechodzą (`pytest`).
- [ ] Dodałeś/zaktualizowałeś testy dla wprowadzonych zmian.
- [ ] Przetestowałeś główne przepływy pracy (np. `scripts/main.py`).
- [ ] Aplikacja Streamlit (jeśli dotyczy) działa poprawnie z Twoimi zmianami.
- [ ] Zaktualizowałeś dokumentację (komentarze, docstringi, ten plik `AGENTS.md` jeśli to konieczne).
- [ ] Twój kod jest sformatowany i zgodny ze standardami (np. PEP 8, Black, Flake8).

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
