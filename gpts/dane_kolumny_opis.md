### 🏫 **Arkusz `szkoly`** – zbiorcze dane o liceach publicznych w Warszawie

| Kolumna               | Typ            | Opis                                                                |
| --------------------- | -------------- | ------------------------------------------------------------------- |
| `SzkolaIdentyfikator` | tekst          | Unikalny identyfikator szkoły, używany do powiązań między arkuszami |
| `NazwaSzkoly`         | tekst          | Pełna nazwa                                                         |
| `AdresSzkoly`         | tekst          | Adres (ulica, kod pocztowy)                                         |
| `TypSzkoly`           | tekst          | Typ szkoły = `liceum`                                               |
| `Dzielnica`           | tekst          | Dzielnica Warszawy, np. `Mokotów`, `Śródmieście`                    |
| `RankingPoz`          | liczba (int)   | Miejsce szkoły w rankingu Perspektyw 2025 (1 = najlepsza)           |
| `Prog_min_szkola`     | liczba (float) | Min liczba punktów do szkoły (dolny przedział)                      |
| `Prog_max_szkola`     | liczba (float) | Min liczba punktów do szkoły (górny przedział)                      |
| `CzasDojazdu`         | liczba (int)   | Szacowany czas dojazdu w minutach                                   |
| `SzkolaLat`           | liczba (float) | Szerokość geograficzna szkoły (np. 52.2297)                         |
| `SzkolaLon`           | liczba (float) | Długość geograficzna szkoły (np. 21.0122)                           |
| `url`                 | tekst (URL)    | Link do oferty szkoły w systemie rekrutacyjnym edu.com.pl           |

### 🧾 **Arkusz `klasy`** – dane o konkretnych oddziałach (klasach) licealnych

| Kolumna                 | Typ            | Opis                                                             |
| ----------------------- | -------------- | ---------------------------------------------------------------- |
| `IdSzkoly`              | liczba (int)   | Pomocniczy ID szkoły                                             |
| `SzkolaIdentyfikator`   | tekst          | Identyfikator szkoły (do łączenia z innymi arkuszami)            |
| `NazwaSzkoly`           | tekst          | Pełna nazwa                                                      |
| `AdresSzkoly`           | tekst          | Adres (ulica, kod pocztowy)                                      |
| `Dzielnica`             | tekst          | Dzielnica Warszawy, np. `Mokotów`, `Śródmieście`                 |
| `OddzialNazwa`          | tekst          | Pełna nazwa klasy z oznaczeniem typu (np. \[O], \[DW]) i języków |
| `PrzedmiotyRozszerzone` | tekst          | Lista przedmiotów w zakresie rozszerzonym                        |
| `JezykiObce`            | tekst          | Języki nauczane w klasie (np. `1: angielski 2: niemiecki`)       |
| `Profil`                | tekst          | Skrócona forma profilu klasy (np. `mat-fiz`, `bio-chem`)         |
| `RankingPoz`            | liczba (int)   | Pozycja szkoły w rankingu Perspektyw 2025                        |
| `Prog_min_klasa`        | liczba (float) | Minimalna liczba punktów do tej klasy w 2024                     |
| `Prog_min_szkola`       | liczba (float) | Min liczba punktów do szkoły w 2024 (dolny przedział)          |
| `Prog_max_szkola`       | liczba (float) | Min liczba punktów do szkoły w 2024 (górny przedział)            |
| `CzasDojazdu`           | liczba (int)   | Czas dojazdu do szkoły z Metra Wilanowska                        |
| `SzkolaLat`             | liczba (float) | Szerokość geograficzna szkoły                                    |
| `SzkolaLon`             | liczba (float) | Długość geograficzna szkoły                                      |
| `Kod`                   | tekst          | Kod pocztowy szkoły                                              |
| `LiczbaMiejsc`          | liczba (int)   | Liczba miejsc w klasie                                           |
| `TypSzkoly`             | tekst          | Typ szkoły (= `liceum`)                                          |
| `UrlGrupy`              | tekst (URL)    | Link do oferty tej konkretnej klasy w edu.com.pl                 |

#### ➕ Kolumny binarne (0/1): czy dany przedmiot jest w zakresie rozszerzonym

| Przedmiot (kolumna)                                         | Znaczenie                       |
| ----------------------------------------------------------- | ------------------------------- |
| `matematyka`, `fizyka`, `chemia`, `biologia`, `informatyka` | Przedmioty ścisłe               |
| `angielski`, `hiszpański`, `niemiecki`, `francuski`         | Języki obce                     |
| `polski`, `historia`, `wos`, `geografia`                    | Humanistyczne i społeczne       |
| `biznes`                                                    | Przedmioty ekonomiczne (np. PP) |

### 🏆 **Arkusz `ranking`** – uproszczony ranking szkół Perspektywy 2025
(tu są też szkoły prywatne i społeczne)
| Kolumna               | Typ          | Opis                                 |
| --------------------- | ------------ | ------------------------------------ |
| `RankingPoz`          | liczba (int) | Miejsce szkoły w rankingu Perspektyw |
| `NazwaSzkoly`         | tekst        | Nazwa                                |
| `Dzielnica`           | tekst        | Dzielnica szkoły                     |
| `SzkolaIdentyfikator` | tekst        | Identyfikator szkoły                 |

### 📉 **Arkusz `min pkt`** – progi punktowe z 2024

| Kolumna               | Typ            | Opis                                           |
| --------------------- | -------------- | ---------------------------------------------- |
| `Dzielnica`           | tekst          | Dzielnica szkoły                               |
| `Typ szkoły`          | tekst          | Typ szkoły                                     |
| `NazwaSzkoly`         | tekst          | Nazwa szkoły                                   |
| `Adres`               | tekst          | Adres szkoły                                   |
| `OddzialNazwa`        | tekst          | Nazwa klasy (oddziału)                         |
| `Prog_min_klasa`      | liczba (float) | Minimalna liczba punktów do tej klasy w 2024   |
| `SzkolaIdentyfikator` | tekst          | Id szkoły (do łączenia)                        |

🧠 **Zasady analizy dla LLM:**
* Filtrowanie klas wg przedmiotów → używaj kolumn binarnych np. `matematyka=1 AND fizyka=1`
* Ranking szkół → sortowanie po `RankingPoz`
* Progi punktowe → `Prog_min_klasa`, dla szkoły od: `Prog_min_szkola` do: `Prog_max_szkola`
* Dojazd → `CzasDojazdu`
* Dzielenie wg dzielnicy → `Dzielnica`
* Oferty klas/szkół → `url`, `UrlGrupy`
