import sys
import pytest
import datetime
from pathlib import Path
from unittest.mock import Mock

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


@pytest.fixture
def freeze_time(monkeypatch):
    """
    Fixture do zamrażania czasu w testach.
    
    Zwraca funkcję, która można użyć do ustawienia konkretnej daty i czasu podczas testów.
    
    Przykład użycia:
        def test_something(freeze_time):
            freeze_time("2025-05-17")  # Ustaw datę na 17 maja 2025
            # Teraz datetime.datetime.now() zwróci tę datę
    """
    def _freeze(ts: str) -> None:
        """
        Zamraża bieżący czas na określony moment podczas testów.
        
        Ustawia metody `datetime.date.today()` i `datetime.datetime.now()` tak, aby zawsze 
        zwracały datę i czas określone w parametrze `ts` (w formacie ISO), umożliwiając 
        deterministyczne testowanie funkcji zależnych od aktualnej daty i czasu.
        
        Args:
            ts: Data i czas w formacie ISO (np. "2025-05-17" lub "2025-05-17 08:00:00")
        """
        dt = datetime.datetime.fromisoformat(ts)

        class FrozenDate(datetime.date):
            @classmethod
            def today(cls):
                """Zwraca bieżącą datę jako obiekt `date`."""
                return dt.date()

        class FrozenDateTime(datetime.datetime):
            @classmethod
            def now(cls, tz=None):
                """
                Zwraca zamrożony czas jako obiekt datetime, opcjonalnie w podanej strefie czasowej.
                
                Args:
                    tz: Opcjonalna strefa czasowa. Jeśli podana, czas zostanie przekonwertowany do tej strefy.
                
                Returns:
                    Obiekt datetime reprezentujący zamrożony czas, w odpowiedniej strefie czasowej.
                """
                return dt if tz is None else dt.astimezone(tz)

        monkeypatch.setattr(datetime, "date", FrozenDate)
        monkeypatch.setattr(datetime, "datetime", FrozenDateTime)

    return _freeze


@pytest.fixture
def mock_gmaps_distance_matrix():
    """
    Fixture tworząca mockowany klient Google Maps dla testów funkcji distance_matrix.
    
    Zwraca mockowany obiekt klienta Google Maps, który można skonfigurować 
    dla różnych przypadków testowych.
    
    Przykład użycia:
        def test_something(mock_gmaps_distance_matrix):
            # Konfiguracja odpowiedzi
            mock_gmaps_distance_matrix.return_value = {...}
            
            # Test funkcji używającej klienta
            result = my_function(mock_gmaps_distance_matrix)
    """
    mock_gmaps = Mock()
    mock_gmaps.distance_matrix = Mock()
    return mock_gmaps


@pytest.fixture
def mock_gmaps_geocode():
    """
    Fixture tworząca mockowany klient Google Maps dla testów funkcji geocode.
    
    Zwraca mockowany obiekt klienta Google Maps, który można skonfigurować 
    dla różnych przypadków testowych związanych z geokodowaniem.
    
    Przykład użycia:
        def test_something(mock_gmaps_geocode):
            # Konfiguracja odpowiedzi
            mock_gmaps_geocode.geocode.return_value = [...]
            
            # Test funkcji używającej klienta
            result = my_function(mock_gmaps_geocode)
    """
    mock_gmaps = Mock()
    mock_gmaps.geocode = Mock()
    return mock_gmaps
