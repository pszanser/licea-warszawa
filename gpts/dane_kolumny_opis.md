## Plik aplikacyjny `results/app/licea_warszawa.xlsx`

To jest finalny workbook używany przez aplikację Streamlit. Zawiera dane
wieloletnie: historyczny tryb 2025 z oferty Vulcan oraz aktualny tryb 2026
oparty o oficjalną publiczną ofertę PZO/Omikron.

Surowe odpowiedzi API PZO i workbooki robocze nie są źródłem dla aplikacji.
Służą do odtworzenia finalnego pliku lokalnie i nie powinny być commitowane.

### Arkusze sterujące

#### `metadata`

| Kolumna | Znaczenie |
| --- | --- |
| `year` | Rok danych widoczny w aplikacji, np. `2026`. |
| `admission_year` | Rok rekrutacji/oferty. |
| `school_year` | Rok szkolny, np. `2026/2027`. |
| `data_status` | Status danych, np. `full` albo `official_offer`. |
| `status_label` | Czytelna etykieta statusu w aplikacji. |
| `threshold_mode` | Tryb progów: faktyczne albo referencyjne. |
| `threshold_label` | Czytelna etykieta progów, np. `progi referencyjne 2025`. |
| `threshold_years` | Lata progów dostępne jako historia/fallback. |

#### `quality`

Arkusz kontrolny z liczbami szkół, klas, progów i braków danych. Przydaje się
do szybkiego sprawdzenia, czy pipeline zbudował sensowny plik aplikacyjny.

### Główne arkusze aplikacji

#### `schools`

Zbiorcze dane szkół, używane w filtrach, mapie i panelu szczegółów szkoły.

| Kolumna | Znaczenie |
| --- | --- |
| `SzkolaIdentyfikator` | Stabilny identyfikator szkoły używany do łączenia lat. |
| `source_school_id` | Identyfikator szkoły w konkretnym źródle, np. `pzo:<id>`. |
| `NazwaSzkoly` | Oficjalna nazwa szkoły. |
| `AdresSzkoly` | Adres prezentowany użytkownikowi. |
| `TypSzkoly` | Typ szkoły, np. liceum, technikum, szkoła branżowa. |
| `Dzielnica` | Dzielnica Warszawy. |
| `SzkolaLat`, `SzkolaLon` | Współrzędne używane na mapie. |
| `Telefon`, `Email`, `WWW` | Dane kontaktowe szkoły, jeśli są dostępne w źródle. |
| `url` | Główny link pokazywany w aplikacji; dla 2026 jest to strona szkoły. |
| `OfertaPzoUrl` | Link do publicznej wyszukiwarki PZO. |
| `RankingPoz`, `RankingRok` | Najnowsza znana pozycja szkoły w rankingu Perspektyw. |
| `Ranking_historyczny_szkola` | Historia pozycji rankingowych według lat. |
| `Prog_min_szkola`, `Prog_max_szkola` | Zakres progów szkoły z aktywnego roku referencyjnego. |
| `Progi_historyczne_szkola` | Historia progów szkoły, np. `2025: 130-150; 2024: 120`. |
| `OpisSzkolyPreview` | Krótki opis placówki do panelu szczegółów. |
| `data_status`, `threshold_label` | Kontekst roczny danych i progów. |

#### `classes`

Główna tabela klas/oddziałów, używana w wynikach, filtrach, mapie i scoringu.

| Kolumna | Znaczenie |
| --- | --- |
| `source_class_id` | Identyfikator klasy w konkretnym źródle, np. `pzo:<admissionPointId>`. |
| `source_school_id`, `SzkolaIdentyfikator` | Powiązanie klasy ze szkołą i między latami. |
| `OddzialNazwa` | Czytelna nazwa klasy/oddziału. |
| `OddzialKod` | Kod oddziału z PZO, np. `1A1_1`. |
| `TypOddzialu` | Typ oddziału w ujednoliconym formacie. |
| `LiczbaMiejsc` | Liczba miejsc w klasie. |
| `LiczbaOddzialow` | Liczba oddziałów/grup, jeśli źródło ją podaje. |
| `PrzedmiotyRozszerzone` | Rozszerzenia albo główne przedmioty profilu. |
| `Zawod`, `DyscyplinaSportowa` | Informacje dla techników, branżowych albo klas sportowych. |
| `JezykiObce`, `PierwszyJezykObcy`, `DrugiJezykObcy` | Języki obce w formie tekstowej. |
| `JezykiObceIkony`, `JezykiObceIkonyOpis` | Techniczne/ikonowe oznaczenia języków z PZO. |
| `Prog_min_klasa` | Próg użyty dla klasy: dla 2026 jest to próg referencyjny z dopasowania do 2025/2024. |
| `ProgUsedLevel` | Czytelny status progu, np. `klasowy 2025 - dokładny`. |
| `ProgMatchStatus`, `ProgMatchScore`, `ProgMatchOldClass` | Informacje o dopasowaniu obecnej klasy do historycznej klasy. |
| `Prog_min_szkola`, `Prog_max_szkola` | Fallback szkolny, gdy nie ma sensownego progu klasowego. |
| `RankingPoz`, `RankingRok` | Ranking szkoły przypięty do klasy. |
| Kolumny przedmiotowe 0/1 | Np. `matematyka`, `fizyka`, `geografia`, `angielski`; używane do filtrowania. |

### Arkusze szczegółów 2026

#### `school_details`

Szczegóły szkoły do panelu pod mapą. Zawiera m.in. `source_school_id`,
`OpisSzkolyPreview`, `OpisSzkolyMarkdown`, kontakt, stronę WWW i link do PZO.
Nie powinien zawierać surowego HTML jako głównej treści użytkowej.

#### `class_details`

Szczegóły wybranej klasy 2026. Zawiera m.in. miejsca, typ grupy, języki,
rozszerzenia/zawód, opis profilu, punktowane przedmioty, kryteria punktowane
oraz status progu referencyjnego.

#### `threshold_matches`

Tabela kandydatów dopasowania między klasami 2026 i klasami historycznymi.
Najważniejsze kolumny:

| Kolumna | Znaczenie |
| --- | --- |
| `source_class_id` | Obecna klasa 2026. |
| `OldOddzialNazwa`, `OldSymbolOddzialu` | Historyczna klasa kandydatka. |
| `Prog_min_klasa` | Próg historycznej klasy. |
| `threshold_year` | Rok progu, np. `2025`. |
| `match_status` | Status dopasowania, np. dokładne/przybliżone/kandydat. |
| `match_score`, `match_gap` | Techniczne miary dopasowania. |
| `used_for_scoring` | Czy ten próg został użyty w rankingu/scoringu. |

### Arkusze źródłowe i pomocnicze

#### `rankings`

Ranking Perspektyw według roku. Służy do przypisania najnowszego rankingu
szkole oraz do historii rankingu.

#### `thresholds`

Historyczne progi punktowe z plików źródłowych. Dla 2026 pełnią rolę progów
referencyjnych, nie faktycznych progów rekrutacji 2026.

#### `plan_naboru`

Starszy arkusz planu naboru. Może być pusty w aktualnym trybie 2026, bo głównym
źródłem oferty 2026 jest PZO/Omikron.

### Zasady analizy dla LLM

* Rok 2025 traktuj jako historyczne pełne dane z Vulcan i faktyczne progi 2025.
* Rok 2026 traktuj jako aktualną oficjalną ofertę PZO/Omikron.
* Dla 2026 progi są referencyjne: patrz `threshold_year`, `threshold_label` i
  `ProgUsedLevel`.
* Do filtrowania przedmiotów używaj kolumn binarnych 0/1 albo tekstu z
  `PrzedmiotyRozszerzone`.
* Do szczegółów szkoły używaj `school_details`, a do szczegółów klasy
  `class_details`.
* Do wyjaśniania progu klasy 2026 używaj `threshold_matches` i pól
  `ProgMatch*`.
* Linkiem głównym do szkoły jest `url`/`WWW`; link do wyszukiwarki PZO jest
  pomocniczy.
