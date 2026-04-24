import pandas as pd
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
        if kwargs.get("header") is None:
            return pd.DataFrame([["opis"], ["opis"], list(mock_excel_data.columns)])
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


def test_load_min_points_new_2025_layout(monkeypatch):
    mock_excel_data = pd.DataFrame(
        {
            "Dzielnica": ["Bemowo"],
            "Nazwa szkoły": ["LO nr 1"],
            "Symbol oddziału": ["1A"],
            "Nazwa krótka oddziału": ["1A [O] mat-fiz"],
            "Najmniejsza liczba punktów kandydatów zakwalifikowanych": [151.25],
        }
    )

    def mock_read_excel(*args, **kwargs):
        assert args[0] == "test_2025.xlsx"
        if kwargs.get("header") is None:
            return pd.DataFrame([list(mock_excel_data.columns)])
        assert kwargs.get("header") == 0
        return mock_excel_data

    monkeypatch.setattr(pd, "read_excel", mock_read_excel)

    result = load_min_points("test_2025.xlsx", admission_year=2025)

    assert result["NazwaSzkoly"].tolist() == ["LO nr 1"]
    assert result["OddzialNazwa"].tolist() == ["1A [O] mat-fiz"]
    assert result["Prog_min_klasa"].tolist() == [151.25]
    assert result["SymbolOddzialu"].tolist() == ["1A"]
    assert result["admission_year"].tolist() == [2025]
