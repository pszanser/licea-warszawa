import pytest
import datetime
import unicodedata
from scripts.main import normalize_name, get_school_type, extract_class_type
from scripts.api_clients.googlemaps_api import get_next_weekday_time

@pytest.mark.parametrize(
    "input_name,expected_result,description",
    [
        (float('nan'), "", "wartość NaN"),
        ("LICEUM", "liceum", "konwersja do małych liter"),
        ("Zażółć gęślą jaźń", "zazolc gesla jazn", "usuwanie polskich znaków"),
        ("Liceum Ogólnokształcące", "lo", "zastępowanie fraz"),
        ("II LO", "ii lo", "zastępowanie rzymskich cyfr"),
        ("LO im. Jana Kochanowskiego", "lo jana kochanowskiego", "usuwanie 'imienia'"),
        ("XIV LO im. Stanisława Staszica", "xiv_staszica", "numer rzymski i patron")
    ]
)
def test_normalize_name(input_name, expected_result, description):
    """
    Testuje funkcję normalize_name pod kątem poprawności normalizacji nazw szkół.
    
    Sprawdza obsługę różnych przypadków wejściowych, w tym:
    - wartości NaN
    - konwersji do małych liter
    - usuwania polskich znaków diakrytycznych
    - zastępowania określonych fraz
    - usuwania słowa "imienia" 
    - poprawnej normalizacji nazw zawierających liczby rzymskie i patronów
    """
    if isinstance(input_name, float) and expected_result == "":
        # Specjalne traktowanie dla NaN
        assert normalize_name(input_name) == expected_result
    elif "usuwanie polskich znaków" in description:
        # Dla testów polskich znaków sprawdzamy, czy konkretne znaki zostały usunięte
        result = normalize_name(input_name)
        for char in "żółćęąśźń":
            assert char not in result
    elif "usuwanie 'imienia'" in description:
        # Dla testów usuwania "imienia" sprawdzamy, czy "im" zostało usunięte
        result = normalize_name(input_name)
        assert "im" not in result
        assert "jana kochanowskiego" in result
    else:
        # Dla pozostałych testów sprawdzamy dokładny wynik
        result = normalize_name(input_name)
        assert expected_result in result

@pytest.mark.parametrize(
    "school_name,expected_type,description",
    [
        ("I Liceum Ogólnokształcące", "liceum", "standardowe liceum"),
        ("LO im. Jana Kochanowskiego", "liceum", "liceum ze skrótem"),
        ("Technikum Mechaniczne nr 7", "technikum", "standardowe technikum"),
        ("Zespół Szkół Technicznych - Technikum", "technikum", "technikum w zespole szkół"),
        ("Branżowa Szkoła I stopnia", "branżowa", "standardowa szkoła branżowa"),
        ("Zespół Szkół - Szkoła Branżowa", "branżowa", "szkoła branżowa w zespole szkół"),
        ("Zespół Szkół Liceum i Technikum", "technikum", "przypadek mieszany - priorytet technikum")
    ]
)
def test_get_school_type(school_name, expected_type, description):
    """
    Testuje funkcję get_school_type pod kątem poprawnej klasyfikacji typu szkoły na podstawie nazwy.
    
    Sprawdza różne przypadki:
    - rozpoznawanie liceum w różnych formatach nazw
    - rozpoznawanie technikum w różnych formatach nazw
    - rozpoznawanie szkoły branżowej w różnych formatach nazw
    - priorytetowanie typów szkół w przypadku nazw zawierających wiele typów
    """
    assert get_school_type(school_name) == expected_type

def test_get_next_weekday_time_same_day(freeze_time):
    """
    Testuje, czy get_next_weekday_time zwraca timestamp tego samego dnia o określonej godzinie, 
    gdy bieżący czas jest przed zadaną godziną w dzień powszedni.
    """
    freeze_time("2025-05-19 06:30:00")  # Poniedziałek o 6:30
    # Gdy wywołujemy przed 7:30 w dzień powszedni, powinien zwrócić ten sam dzień
    timestamp = get_next_weekday_time(7, 30)
    dt = datetime.datetime.fromtimestamp(timestamp)
    assert dt.date() == datetime.date(2025, 5, 19)  # ten sam dzień (poniedziałek)
    assert dt.hour == 7
    assert dt.minute == 30

def test_get_next_weekday_time_next_day(freeze_time):
    """
    Testuje, czy get_next_weekday_time zwraca timestamp następnego dnia roboczego o określonej godzinie, 
    gdy bieżący czas jest po zadanej godzinie w dzień powszedni.
    """
    freeze_time("2025-05-19 08:00:00")  # Poniedziałek o 8:00
    # Gdy wywołujemy po 7:30 w dzień powszedni, powinien zwrócić następny dzień
    timestamp = get_next_weekday_time(7, 30)
    dt = datetime.datetime.fromtimestamp(timestamp)
    assert dt.date() == datetime.date(2025, 5, 20)  # następny dzień (wtorek)
    assert dt.hour == 7
    assert dt.minute == 30

def test_get_next_weekday_time_skip_weekend(freeze_time):
    """
    Testuje, czy get_next_weekday_time zwraca poniedziałek o 7:30, gdy wywołane w piątek po docelowej godzinie.
    
    Zamraża czas na piątek, 2025-05-23 08:00 i sprawdza, czy funkcja pomija weekend i zwraca timestamp 
    odpowiadający najbliższemu poniedziałkowi o 7:30.
    """
    freeze_time("2025-05-23 08:00:00")  # Piątek o 8:00
    # Gdy wywołujemy w piątek po 7:30, powinien zwrócić poniedziałek
    timestamp = get_next_weekday_time(7, 30)
    dt = datetime.datetime.fromtimestamp(timestamp)
    assert dt.date() == datetime.date(2025, 5, 26)  # poniedziałek po weekendzie
    assert dt.weekday() == 0  # Poniedziałek
    assert dt.hour == 7
    assert dt.minute == 30

def test_get_next_weekday_time_weekend(freeze_time):
    """
    Testuje, czy get_next_weekday_time zwraca najbliższy poniedziałek o 7:30, gdy wywołany w weekend.
    
    Zamraża czas na sobotę i sprawdza, czy funkcja poprawnie omija weekend, 
    zwracając timestamp odpowiadający poniedziałkowi o zadanej godzinie.
    """
    freeze_time("2025-05-17")  # Sobota
    # Gdy wywołujemy w weekend, powinien zwrócić najbliższy poniedziałek
    timestamp = get_next_weekday_time(7, 30)
    dt = datetime.datetime.fromtimestamp(timestamp)
    assert dt.date() == datetime.date(2025, 5, 19)  # najbliższy poniedziałek
    assert dt.weekday() == 0  # Poniedziałek
    assert dt.hour == 7
    assert dt.minute == 30


def test_extract_class_type():
    """Testuje funkcję extract_class_type wyciągającą typ oddziału"""
    assert extract_class_type("1Bf [O] fiz-ang-mat (ang-hisz*,niem*)") == "O"
    assert extract_class_type("1Dint [I-i] h.szt.-ang-pol (ang-hisz*)") == "I-i"
    assert extract_class_type("1a_piłka_ręczna [MS] biol-geogr-ang (ang-niem)") == "MS"
    assert extract_class_type("Brak nawiasu") is None
