import pytest
import datetime
import unicodedata
from scripts.main import normalize_name, get_school_type
from scripts.api_clients.googlemaps_api import get_next_weekday_time


def _freeze_time(monkeypatch, ts: str) -> None:
    """
    Zamraża bieżącą datę i czas na określony moment podczas testów.
    
    Ustawia klasy `datetime.date` i `datetime.datetime` tak, aby zawsze zwracały podany czas `ts` jako bieżącą datę i godzinę, umożliwiając deterministyczne testowanie funkcji zależnych od czasu.
    """
    dt = datetime.datetime.fromisoformat(ts)

    class FrozenDate(datetime.date):
        @classmethod
        def today(cls):
            """
            Zwraca bieżącą datę jako obiekt `date`.
            """
            return dt.date()

    class FrozenDateTime(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            """
            Zwraca zamrożony czas jako obiekt datetime.
            
            Jeśli podano strefę czasową, zwraca czas przekształcony do tej strefy.
            """
            return dt if tz is None else dt.astimezone(tz)

    monkeypatch.setattr(datetime, "date", FrozenDate)
    monkeypatch.setattr(datetime, "datetime", FrozenDateTime)

def test_normalize_name():
    # Test przypadku z NaN
    """
    Testuje funkcję normalize_name pod kątem poprawności normalizacji nazw szkół.
    
    Sprawdza obsługę wartości NaN, konwersję do małych liter, usuwanie polskich znaków diakrytycznych, zastępowanie określonych fraz, usuwanie słowa "imienia" oraz poprawną normalizację nazw zawierających liczby rzymskie i patronów.
    """
    assert normalize_name(float('nan')) == ""
    
    # Test zamiany na małe litery
    assert normalize_name("LICEUM") != "LICEUM"
    
    # Test usuwania polskich znaków
    result = normalize_name("Zażółć gęślą jaźń")
    assert "ż" not in result
    assert "ł" not in result
    assert "ś" not in result
    assert "ź" not in result
    
    # Test zastępowania fraz
    assert "lo" in normalize_name("Liceum Ogólnokształcące")
    assert "ii" in normalize_name("II Liceum Ogólnokształcące")
    
    # Test usuwania "imienia"
    result = normalize_name("LO im. Jana Kochanowskiego")
    assert "im" not in result
    assert "jana kochanowskiego" in result
    
    # Test numeru rzymskiego i patrona
    result = normalize_name("XIV LO im. Stanisława Staszica")
    assert result == "xiv_staszica"

def test_get_school_type():
    # Test liceum
    """
    Testuje funkcję get_school_type pod kątem poprawnej klasyfikacji typu szkoły na podstawie nazwy.
    
    Sprawdza rozpoznawanie liceum, technikum oraz szkoły branżowej, a także priorytetowanie technikum w przypadku nazw zawierających wiele typów szkół.
    """
    assert get_school_type("I Liceum Ogólnokształcące") == "liceum"
    assert get_school_type("LO im. Jana Kochanowskiego") == "liceum"
    
    # Test technikum
    assert get_school_type("Technikum Mechaniczne nr 7") == "technikum"
    assert get_school_type("Zespół Szkół Technicznych - Technikum") == "technikum"
    
    # Test szkoła branżowa
    assert get_school_type("Branżowa Szkoła I stopnia") == "branżowa"
    assert get_school_type("Zespół Szkół - Szkoła Branżowa") == "branżowa"
    
    # Test przypadku mieszanego (priorytet dla technikum)
    assert get_school_type("Zespół Szkół Liceum i Technikum") == "technikum"

def test_get_next_weekday_time_same_day(monkeypatch):
    _freeze_time(monkeypatch, "2025-05-19 06:30:00")  # Poniedziałek o 6:30
    # Gdy wywołujemy przed 7:30 w dzień powszedni, powinien zwrócić ten sam dzień
    timestamp = get_next_weekday_time(7, 30)
    dt = datetime.datetime.fromtimestamp(timestamp)
    assert dt.date() == datetime.date(2025, 5, 19)  # ten sam dzień (poniedziałek)
    assert dt.hour == 7
    assert dt.minute == 30

def test_get_next_weekday_time_next_day(monkeypatch):
    """
    Testuje, czy get_next_weekday_time zwraca timestamp następnego dnia roboczego o określonej godzinie, gdy bieżący czas jest po zadanej godzinie w dzień powszedni.
    """
    _freeze_time(monkeypatch, "2025-05-19 08:00:00")  # Poniedziałek o 8:00
    # Gdy wywołujemy po 7:30 w dzień powszedni, powinien zwrócić następny dzień
    timestamp = get_next_weekday_time(7, 30)
    dt = datetime.datetime.fromtimestamp(timestamp)
    assert dt.date() == datetime.date(2025, 5, 20)  # następny dzień (wtorek)
    assert dt.hour == 7
    assert dt.minute == 30

def test_get_next_weekday_time_skip_weekend(monkeypatch):
    """
    Testuje, czy get_next_weekday_time zwraca poniedziałek o 7:30, gdy wywołane w piątek po docelowej godzinie.
    
    Zamraża czas na piątek, 2025-05-23 08:00 i sprawdza, czy funkcja pomija weekend i zwraca timestamp odpowiadający najbliższemu poniedziałkowi o 7:30.
    """
    _freeze_time(monkeypatch, "2025-05-23 08:00:00")  # Piątek o 8:00
    # Gdy wywołujemy w piątek po 7:30, powinien zwrócić poniedziałek
    timestamp = get_next_weekday_time(7, 30)
    dt = datetime.datetime.fromtimestamp(timestamp)
    assert dt.date() == datetime.date(2025, 5, 26)  # poniedziałek po weekendzie
    assert dt.weekday() == 0  # Poniedziałek
    assert dt.hour == 7
    assert dt.minute == 30

def test_get_next_weekday_time_weekend(monkeypatch):
    """
    Testuje, czy get_next_weekday_time zwraca najbliższy poniedziałek o 7:30, gdy wywołany w weekend.
    
    Zamraża czas na sobotę i sprawdza, czy funkcja poprawnie omija weekend, zwracając timestamp odpowiadający poniedziałkowi o zadanej godzinie.
    """
    _freeze_time(monkeypatch, "2025-05-17")  # Sobota
    # Gdy wywołujemy w weekend, powinien zwrócić najbliższy poniedziałek
    timestamp = get_next_weekday_time(7, 30)
    dt = datetime.datetime.fromtimestamp(timestamp)
    assert dt.date() == datetime.date(2025, 5, 19)  # najbliższy poniedziałek
    assert dt.weekday() == 0  # Poniedziałek
    assert dt.hour == 7
    assert dt.minute == 30