from pathlib import Path

import pandas as pd

from scripts.visualization.generate_map import get_default_year


def test_get_default_year_prefers_latest_full_year(monkeypatch):
    metadata = pd.DataFrame(
        {
            "year": [2025, 2026],
            "data_status": ["full", "planned_offer"],
        }
    )
    monkeypatch.setattr(pd, "read_excel", lambda *args, **kwargs: metadata)

    assert get_default_year(Path("ignored.xlsx"), [2026, 2025]) == 2025


def test_get_default_year_falls_back_to_latest_available_year(monkeypatch):
    metadata = pd.DataFrame(
        {
            "year": [2025, 2026],
            "data_status": ["legacy", "planned_offer"],
        }
    )
    monkeypatch.setattr(pd, "read_excel", lambda *args, **kwargs: metadata)

    assert get_default_year(Path("ignored.xlsx"), [2026, 2025]) == 2026
