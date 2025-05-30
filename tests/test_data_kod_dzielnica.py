import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from scripts.data_processing.get_data_kod_dzielnica import _rows_from_page, build_csv


@pytest.fixture
def mock_html_response():
    """
    Zwraca przykładowy fragment HTML zawierający tabelę z kodami pocztowymi i dzielnicami.

    Funkcja służy jako dane testowe do symulowania odpowiedzi serwera podczas testowania
    parsowania tabeli kodów pocztowych i dzielnic Warszawy.
    """
    return """
    <html>
        <body>
            <table>
                <tr class="_data">
                    <td class="code-row">00-001</td>
                    <td>Nazwa ulicy</td>
                    <td>Śródmieście</td>
                </tr>
                <tr class="_data">
                    <td class="code-row">00-002</td>
                    <td>Inna ulica</td>
                    <td>Mokotów</td>
                </tr>
                <tr>
                    <td>Nagłówek</td>
                    <td>Nagłówek</td>
                    <td>Nagłówek</td>
                </tr>
                <tr class="_data">
                    <td class="code-row">01-001</td>
                    <td>Jeszcze inna</td>
                    <td>Wola</td>
                </tr>
            </table>
        </body>
    </html>
    """


def test_rows_from_page(mock_html_response):
    """Test funkcji _rows_from_page przetwarzającej pojedynczą stronę."""
    with patch("requests.get") as mock_get:
        # Konfiguracja mocka dla requests.get
        mock_response = MagicMock()
        mock_response.text = mock_html_response
        mock_get.return_value = mock_response

        # Wywołanie funkcji i sprawdzenie wyników
        result = _rows_from_page(1)

        # Weryfikacja czy mock był wywołany z poprawnymi argumentami
        mock_get.assert_called_once_with(
            "https://www.kodypocztowe.info/warszawa", timeout=10
        )

        # Sprawdzenie wyników
        expected = [
            ("00-001", "Śródmieście"),
            ("00-002", "Mokotów"),
            ("01-001", "Wola"),
        ]
        assert result == expected


def test_build_csv(tmp_path, monkeypatch):
    """
    Testuje funkcję build_csv pod kątem agregacji danych z wielu stron, usuwania duplikatów,
    sortowania oraz poprawnego zapisu do pliku CSV.

    Test sprawdza, czy plik CSV jest tworzony, zawiera oczekiwaną liczbę wierszy i kolumn,
    dane są posortowane według kodów pocztowych, a duplikaty zostały usunięte.
    """
    # Przykładowe dane do zwrócenia przez _rows_from_page dla różnych stron
    page_data = {
        1: [("00-001", "Śródmieście"), ("00-002", "Mokotów")],
        2: [
            ("00-002", "Mokotów"),
            ("01-001", "Wola"),
        ],  # Duplikat kodu 00-002, powinien być usunięty
        3: [("02-003", "Praga")],
    }

    # Mockowanie funkcji _rows_from_page
    def mock_rows_from_page(page):
        """
        Zwraca dane wierszy dla podanej strony na podstawie zdefiniowanego słownika testowego.

        Args:
                page: Numer strony, dla której mają zostać zwrócone dane.

        Returns:
                Lista krotek z danymi odpowiadającymi podanej stronie lub pusta lista, jeśli brak danych.
        """
        return page_data.get(page, [])

    monkeypatch.setattr(
        "scripts.data_processing.get_data_kod_dzielnica._rows_from_page",
        mock_rows_from_page,
    )

    # Mockowanie stałej LAST_PAGE
    monkeypatch.setattr("scripts.data_processing.get_data_kod_dzielnica.LAST_PAGE", 3)

    # Ścieżka do tymczasowego pliku CSV
    csv_path = str(tmp_path / "test_output.csv")

    # Wywołanie funkcji
    df = build_csv(out_path=csv_path)

    # Sprawdzenie czy plik został utworzony
    assert (tmp_path / "test_output.csv").exists()

    # Sprawdzenie zawartości pliku
    output_df = pd.read_csv(csv_path)

    # Sprawdzenie kształtu DataFrame (4 wiersze, 2 kolumny)
    assert df.shape == (4, 2)
    assert output_df.shape == (4, 2)

    # Sprawdzenie czy dane są posortowane według kodów pocztowych
    assert list(df["Kod"]) == ["00-001", "00-002", "01-001", "02-003"]
    assert list(df["Dzielnica"]) == ["Śródmieście", "Mokotów", "Wola", "Praga"]

    # Sprawdzenie czy duplikaty zostały usunięte (kod 00-002 występuje tylko raz)
    assert len(df[df["Kod"] == "00-002"]) == 1
