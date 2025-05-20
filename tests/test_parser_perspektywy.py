import pandas as pd
import pytest
from scripts.data_processing.parser_perspektywy import (
    parse_ranking_perspektywy_html,
    parse_ranking_perspektywy_pdf,
)


def test_parse_ranking_perspektywy_html(tmp_path):
    """
    Testuje funkcję parsującą ranking szkół z pliku HTML.
    
    Tworzy tymczasowy plik HTML z przykładową tabelą rankingową, uruchamia parser i sprawdza, czy wynikowy DataFrame zawiera oczekiwane kolumny, kształt oraz poprawne dane.
    """
    html = """
    <html><body><table>
    <tr><th>Poz</th><th>Nazwa</th><th>Dzielnica</th><th>h</th><th>x</th><th>Wsk</th></tr>
    <tr><td>1</td><td>LO im. A</td><td>Mokotów</td><td>10</td><td></td><td>70</td></tr>
    <tr><td>2</td><td>LO im. B</td><td>Wola</td><td>20</td><td></td><td>60</td></tr>
    </table></body></html>
    """
    html_file = tmp_path / "ranking.html"
    html_file.write_text(html, encoding="utf-8")
    df = parse_ranking_perspektywy_html(str(html_file))
    assert list(df.columns) == ["RankingPoz", "NazwaSzkoly", "Dzielnica", "Historia24", "WSK"]
    assert df.shape == (2, 5)
    assert df["RankingPoz"].tolist() == [1, 2]
    assert df["NazwaSzkoly"].tolist() == ["LO im. A", "LO im. B"]
    assert df["Dzielnica"].tolist() == ["Mokotów", "Wola"]


def test_parse_ranking_perspektywy_pdf(monkeypatch):
    """
    Testuje funkcję parse_ranking_perspektywy_pdf pod kątem poprawnego przetwarzania tabeli rankingowej z pliku PDF.
    
    Tworzy sztuczny obiekt PDF z jedną stroną zawierającą przykładową tabelę rankingową, zastępuje funkcję otwierającą pliki PDF za pomocą monkeypatch, a następnie sprawdza, czy parser zwraca DataFrame o oczekiwanych kolumnach, kształcie i zawartości.
    """
    table = [
        ["Poz", "Nazwa", "Dzielnica"],
        ["1", "LO im. A", "Mokotów"],
        ["2", "LO im. B", "Wola"],
    ]

    class FakePage:
        def extract_table(self):
            """
            Zwraca tabelę przechowywaną w obiekcie.
            
            Returns:
                Tabela przypisana do obiektu.
            """
            return table

    class FakePDF:
        def __init__(self):
            """
            Inicjalizuje obiekt z jedną stroną testową typu FakePage.
            """
            self.pages = [FakePage()]
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, tb):
            pass

    def fake_open(path):
        """
        Zwraca instancję klasy FakePDF niezależnie od podanej ścieżki pliku.
        
        Funkcja służy do zastępowania otwierania plików PDF w testach, umożliwiając użycie sztucznego obiektu PDF zamiast rzeczywistego pliku.
        """
        return FakePDF()

    monkeypatch.setattr("pdfplumber.open", fake_open)

    df = parse_ranking_perspektywy_pdf("dummy.pdf")
    assert list(df.columns) == ["RankingPoz", "NazwaSzkoly", "Dzielnica"]
    assert df.shape == (2, 3)
    assert df["RankingPoz"].tolist() == [1, 2]
    assert df["NazwaSzkoly"].tolist() == ["LO im. A", "LO im. B"]
    assert df["Dzielnica"].tolist() == ["Mokotów", "Wola"]
