from pathlib import Path
import re

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RELEASE_NOTES_PATH = REPO_ROOT / "HISTORIA_ZMIAN.md"


def extract_latest_release_notes(markdown_text: str) -> str:
    """Zwraca pierwszą sekcję drugiego poziomu z pliku historii zmian."""
    heading_pattern = re.compile(r"^##(?!#)\s+")
    lines = markdown_text.splitlines()
    start_index = next(
        (index for index, line in enumerate(lines) if heading_pattern.match(line)),
        None,
    )
    if start_index is None:
        return ""

    end_index = next(
        (
            index
            for index, line in enumerate(lines[start_index + 1 :], start_index + 1)
            if heading_pattern.match(line)
        ),
        len(lines),
    )
    return "\n".join(lines[start_index:end_index]).strip()


def load_latest_release_notes(
    path: Path | str = DEFAULT_RELEASE_NOTES_PATH,
) -> str:
    """Wczytuje najnowszy wpis historii zmian; brak pliku traktuje jako brak wpisu."""
    try:
        markdown_text = Path(path).read_text(encoding="utf-8")
    except OSError:
        return ""
    return extract_latest_release_notes(markdown_text)
