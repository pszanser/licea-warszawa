# Historia zmian

Krótka historia zmian w aplikacji.

## 2026-04-29 - Dopasowanie szkół

### Nowe

- Nowa zakładka **Moje dopasowanie** pomaga porównać klasy według punktów,
  rankingu szkoły, progu i odległości.
- Punkt startowy można ustawić z mapy, adresu albo środka widoku.
- Przy szkołach pojawiają się linki do trasy w Google Maps z wybranego punktu.

### Poprawione

- Mapa nie wraca już do starego kliknięcia po zmianie punktu startowego.
- Pinezka i linki dojazdu aktualizują się od razu.

### Dane

- W wynikach widać **brak rankingu** i **brak progu**.
- Brakująca składowa dopasowania liczy się jako 0.

## 2026-04-24 - Dane 2025/2026 i model wieloletni

### Nowe

- Aplikacja potrafi przełączać rok danych.
- Dane 2025 i plan naboru 2026 są przygotowane w jednym, stabilnym pliku dla
  aplikacji.
- Przy szkołach można zobaczyć historię rankingu.

### Dane

- Dodano progi 2025, ranking 2025/2026 i plan naboru 2026/2027.
- Dane źródłowe są uporządkowane rocznikami, co ułatwi kolejne aktualizacje.

### Technicznie

- Zmiana była częścią PR #42: **Aktualizacja do modelu wieloletniego**.
