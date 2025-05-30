import pytest
import pandas as pd
import io
from unittest.mock import MagicMock
from scripts.data_processing.load_minimum_points import load_min_points


def test_load_min_points(monkeypatch):
    # Przygotowanie przykładowych danych Excel
    mock_excel_data = pd.DataFrame(
        {
            "Minimalna": [150, 160, 170],
            "Nazwa szkoły": ["LO nr 1", "LO nr 2", "LO nr 3"],
            "Nazwa krótka oddziału": ["1A mat-fiz", "1B biol-chem", "1C humanistyczna"],
        }
    )

    # Mockowanie funkcji pd.read_excel
    def mock_read_excel(*args, **kwargs):
        """
        Symuluje funkcję pandas.read_excel dla testów, zwracając przygotowany DataFrame.

        Funkcja sprawdza, czy ścieżka pliku to "test_path.xlsx" oraz czy nagłówek ustawiony jest na 2, po czym zwraca wcześniej zdefiniowany obiekt mock_excel_data.
        """
        assert args[0] == "test_path.xlsx"
        assert kwargs.get("header") == 2
        return mock_excel_data

    monkeypatch.setattr(pd, "read_excel", mock_read_excel)

    # Wywołanie testowanej funkcji
    result = load_min_points("test_path.xlsx")

    # Sprawdzenie rezultatów
    assert list(result.columns) == ["Prog_min_klasa", "NazwaSzkoly", "OddzialNazwa"]
    assert result["Prog_min_klasa"].tolist() == [150, 160, 170]
    assert result["NazwaSzkoly"].tolist() == ["LO nr 1", "LO nr 2", "LO nr 3"]
    assert result["OddzialNazwa"].tolist() == [
        "1A mat-fiz",
        "1B biol-chem",
        "1C humanistyczna",
    ]
