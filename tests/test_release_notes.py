from pathlib import Path
from unittest.mock import patch

from scripts.visualization.release_notes import (
    extract_latest_release_notes,
    load_latest_release_notes,
)


def test_extract_latest_release_notes_returns_first_second_level_section():
    markdown = """# Historia zmian

Wstęp.

## 2026-04-29 - Najnowsza zmiana

### Nowe

- Najnowszy wpis.

## 2026-04-20 - Starsza zmiana

- Starszy wpis.
"""

    result = extract_latest_release_notes(markdown)

    assert "## 2026-04-29 - Najnowsza zmiana" in result
    assert "- Najnowszy wpis." in result
    assert "2026-04-20" not in result


def test_extract_latest_release_notes_returns_empty_string_without_section():
    markdown = """# Historia zmian

Brak wpisów drugiego poziomu.
"""

    assert extract_latest_release_notes(markdown) == ""


def test_load_latest_release_notes_reads_first_section():
    markdown = """# Historia zmian

## 2026-04-29 - Najnowsza zmiana

- Widoczna zmiana.

## 2026-04-20 - Starsza zmiana

- Niewidoczna zmiana.
"""

    with patch.object(Path, "read_text", return_value=markdown):
        result = load_latest_release_notes("HISTORIA_ZMIAN.md")

    assert "Widoczna zmiana" in result
    assert "Niewidoczna zmiana" not in result


def test_load_latest_release_notes_returns_empty_string_for_missing_file():
    with patch.object(Path, "read_text", side_effect=FileNotFoundError):
        assert load_latest_release_notes("brak.md") == ""
