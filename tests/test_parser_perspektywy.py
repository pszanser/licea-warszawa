from scripts.data_processing.parser_perspektywy import (
    parse_ranking_perspektywy_html_text,
    parse_ranking_perspektywy_pdf,
)


def test_parse_ranking_perspektywy_html():
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
    df = parse_ranking_perspektywy_html_text(html)
    assert list(df.columns) == [
        "RankingPoz",
        "NazwaSzkoly",
        "Dzielnica",
        "Historia24",
        "WSK",
        "RankingPozTekst",
    ]
    assert df.shape == (2, 6)
    assert df["RankingPoz"].tolist() == [1, 2]
    assert df["NazwaSzkoly"].tolist() == ["LO im. A", "LO im. B"]
    assert df["Dzielnica"].tolist() == ["Mokotów", "Wola"]
    assert df["WSK"].tolist() == ["70", "60"]


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


def test_parse_ranking_perspektywy_html_without_table_keeps_schema():
    df = parse_ranking_perspektywy_html_text(
        "<html><body>brak tabeli</body></html>", year=2027
    )

    assert list(df.columns) == [
        "RankingPoz",
        "NazwaSzkoly",
        "Dzielnica",
        "Historia24",
        "WSK",
        "RankingPozTekst",
        "year",
    ]
    assert df.empty


def test_parse_ranking_perspektywy_html_embedded_payload():
    html = """
    <html><body>
    &quot;rank&quot;:[1,[[0,{&quot;2026&quot;:[0,&quot;1&quot;],
    &quot;name&quot;:[0,&quot;&lt;a href=&#39;http://example.test&#39;&gt;XIV LO im. Stanisława Staszica&lt;/a&gt;&quot;],
    &quot;dzielnica&quot;:[0,&quot;Ochota&quot;],
    &quot;wsk&quot;:[0,100]}],
    [0,{&quot;2026&quot;:[0,&quot;4=&quot;],
    &quot;name&quot;:[0,&quot;VIII LO im. Władysława IV&quot;],
    &quot;dzielnica&quot;:[0,&quot;Praga Płn.&quot;],
    &quot;wsk&quot;:[0,&quot;70.5&quot;]}]]]
    </body></html>
    """
    df = parse_ranking_perspektywy_html_text(html, year=2026)

    assert df["RankingPoz"].tolist() == [1, 4]
    assert df["RankingPozTekst"].tolist() == ["1", "4="]
    assert df["NazwaSzkoly"].tolist() == [
        "XIV LO im. Stanisława Staszica",
        "VIII LO im. Władysława IV",
    ]
    assert df["Dzielnica"].tolist() == ["Ochota", "Praga Płn."]
    assert df["year"].tolist() == [2026, 2026]
