import pytest
import googlemaps
from unittest.mock import Mock
import datetime

from scripts.api_clients.googlemaps_api import (
    get_travel_time,
    get_travel_times_batch,
    get_coordinates_for_addresses_batch,
    get_next_weekday_time,
)

def test_get_travel_time(mock_gmaps_distance_matrix):
    """
    Testuje podstawową funkcjonalność get_travel_time.
    
    Sprawdza, czy funkcja poprawnie konwertuje czas przejazdu z sekund na minuty 
    i czy prawidłowo wywołuje API Google Maps.
    """
    # Przygotowanie mockowanej odpowiedzi
    mock_result = {
        "rows": [
            {
                "elements": [
                    {
                        "duration": {"value": 1800}  # 30 minut w sekundach
                    }
                ]
            }
        ]
    }
    mock_gmaps_distance_matrix.distance_matrix.return_value = mock_result
    
    # Wywołanie funkcji z mockowanym obiektem
    travel_time = get_travel_time(
        mock_gmaps_distance_matrix, 
        "Adres początkowy", 
        "Adres docelowy", 
        sleep_s=0  # Wyłączamy opóźnienie w teście
    )
    
    # Sprawdzenie wyników
    assert travel_time == 30  # 30 minut
    mock_gmaps_distance_matrix.distance_matrix.assert_called_once_with(
        origins=["Adres początkowy"],
        destinations=["Adres docelowy"],
        mode="transit",
        language="pl"
    )

def test_get_travel_time_with_departure_time(mock_gmaps_distance_matrix):
    """
    Testuje funkcję get_travel_time z parametrem departure_time.
    
    Sprawdza, czy funkcja poprawnie przekazuje departure_time do wywołania API Google Maps 
    oraz czy zwraca prawidłowy czas przejazdu w minutach na podstawie mockowanej odpowiedzi.
    """
    # Przygotowanie mockowanej odpowiedzi
    mock_result = {
        "rows": [
            {
                "elements": [
                    {
                        "duration": {"value": 1800}  # 30 minut w sekundach
                    }
                ]
            }
        ]
    }
    mock_gmaps_distance_matrix.distance_matrix.return_value = mock_result
    departure_time = 1621234567  # przykładowy timestamp
    
    # Wywołanie funkcji z mockowanym obiektem
    travel_time = get_travel_time(
        mock_gmaps_distance_matrix, 
        "Adres początkowy", 
        "Adres docelowy", 
        sleep_s=0,  # Wyłączamy opóźnienie w teście
        departure_time=departure_time
    )
    
    # Sprawdzenie wyników
    assert travel_time == 30  # 30 minut
    mock_gmaps_distance_matrix.distance_matrix.assert_called_once_with(
        origins=["Adres początkowy"],
        destinations=["Adres docelowy"],
        mode="transit",
        language="pl",
        departure_time=departure_time
    )

def test_get_travel_time_exception(mock_gmaps_distance_matrix):
    """
    Testuje zachowanie get_travel_time, gdy API zgłasza wyjątek.
    
    Sprawdza, czy funkcja poprawnie obsługuje wyjątki z API Google Maps,
    zwracając None w przypadku błędu.
    """
    # Przygotowanie mockowanego obiektu gmaps, który zgłasza wyjątek
    mock_gmaps_distance_matrix.distance_matrix.side_effect = Exception("API Error")
    
    # Wywołanie funkcji z mockowanym obiektem
    travel_time = get_travel_time(
        mock_gmaps_distance_matrix, 
        "Adres początkowy", 
        "Adres docelowy", 
        sleep_s=0  # Wyłączamy opóźnienie w teście
    )
    
    # Sprawdzenie wyników
    assert travel_time is None

def test_get_travel_times_batch(mock_gmaps_distance_matrix):
    """
    Testuje funkcję batchowego pobierania czasów podróży dla wielu miejsc docelowych.
    
    Sprawdza, czy funkcja `get_travel_times_batch` poprawnie zwraca słownik z czasami podróży 
    w minutach dla każdego miejsca docelowego lub `None`, gdy trasa nie jest dostępna. 
    Weryfikuje także, czy wywołanie API Google Maps odbywa się z odpowiednimi parametrami.
    """
    # Przygotowanie mockowanej odpowiedzi
    mock_result = {
        "rows": [
            {
                "elements": [
                    {
                        "status": "OK",
                        "duration": {"value": 1800}  # 30 minut w sekundach
                    },
                    {
                        "status": "OK",
                        "duration": {"value": 2400}  # 40 minut w sekundach
                    },
                    {
                        "status": "ZERO_RESULTS",  # Brak trasy
                    }
                ]
            }
        ]
    }
    mock_gmaps_distance_matrix.distance_matrix.return_value = mock_result
    
    # Dane wejściowe
    origin = "Adres początkowy"
    destinations = ["Miejsce 1", "Miejsce 2", "Miejsce niedostępne"]
    
    # Wywołanie funkcji z mockowanym obiektem
    travel_times = get_travel_times_batch(mock_gmaps_distance_matrix, origin, destinations)
    
    # Sprawdzenie wyników
    assert travel_times == {
        "Miejsce 1": 30,
        "Miejsce 2": 40,
        "Miejsce niedostępne": None
    }
    mock_gmaps_distance_matrix.distance_matrix.assert_called_once_with(
        origins=[origin],
        destinations=destinations,
        mode="transit",
        language="pl"
    )

def test_get_travel_times_batch_with_departure_time(mock_gmaps_distance_matrix):
    """
    Testuje funkcję get_travel_times_batch z parametrem departure_time.
    
    Sprawdza, czy funkcja poprawnie zwraca czasy przejazdu w minutach dla wielu miejsc docelowych,
    przekazując departure_time do wywołania API Google Maps oraz czy wyniki są zgodne z oczekiwaniami.
    """
    # Przygotowanie mockowanej odpowiedzi
    mock_result = {
        "rows": [
            {
                "elements": [
                    {
                        "status": "OK",
                        "duration": {"value": 1800}  # 30 minut w sekundach
                    },
                    {
                        "status": "OK",
                        "duration": {"value": 2400}  # 40 minut w sekundach
                    }
                ]
            }
        ]
    }
    mock_gmaps_distance_matrix.distance_matrix.return_value = mock_result
    
    # Dane wejściowe
    origin = "Adres początkowy"
    destinations = ["Miejsce 1", "Miejsce 2"]
    departure_time = 1621234567  # przykładowy timestamp
    
    # Wywołanie funkcji z mockowanym obiektem
    travel_times = get_travel_times_batch(
        mock_gmaps_distance_matrix, 
        origin, 
        destinations, 
        departure_time=departure_time
    )
    
    # Sprawdzenie wyników
    assert travel_times == {
        "Miejsce 1": 30,
        "Miejsce 2": 40
    }
    mock_gmaps_distance_matrix.distance_matrix.assert_called_once_with(
        origins=[origin],
        destinations=destinations,
        mode="transit",
        language="pl",
        departure_time=departure_time
    )

def test_get_travel_times_batch_exception(mock_gmaps_distance_matrix):
    """
    Testuje, czy get_travel_times_batch zwraca None dla wszystkich adresów docelowych,
    gdy wywołanie API zgłasza wyjątek.
    
    Weryfikuje obsługę błędów API, zapewniając, że funkcja zwraca słownik z wartościami None
    dla wszystkich adresów docelowych.
    """
    # Przygotowanie mockowanego obiektu gmaps, który zgłasza wyjątek
    mock_gmaps_distance_matrix.distance_matrix.side_effect = Exception("API Error")
    
    # Dane wejściowe
    origin = "Adres początkowy"
    destinations = ["Miejsce 1", "Miejsce 2"]
    
    # Wywołanie funkcji z mockowanym obiektem
    travel_times = get_travel_times_batch(mock_gmaps_distance_matrix, origin, destinations)
    
    # Sprawdzenie wyników - funkcja zwraca słownik z None dla wszystkich adresów
    assert travel_times == {
        "Miejsce 1": None,
        "Miejsce 2": None
    }

@pytest.fixture
def mock_gmaps_geocode_with_results():
    """
    Fixture tworząca mockowany klient Google Maps z predefiniowanymi wynikami geokodowania.
    
    Zwraca krotę (mock_gmaps, expected_coordinates), gdzie:
    - mock_gmaps to mockowany klient Google Maps
    - expected_coordinates to oczekiwane współrzędne dla testowych adresów
    """
    mock_gmaps = Mock()
    
    # Definiujemy odpowiedzi dla różnych adresów
    mock_responses = {
        "Adres 1": [
            {
                "geometry": {
                    "location": {
                        "lat": 52.2297,
                        "lng": 21.0122
                    }
                }
            }
        ],
        "Adres 2": [
            {
                "geometry": {
                    "location": {
                        "lat": 50.0647,
                        "lng": 19.9450
                    }
                }
            }
        ],
        "Niepoprawny adres": []  # Brak wyników dla niepoprawnego adresu
    }
    
    # Oczekiwane współrzędne
    expected_coordinates = {
        "Adres 1": (52.2297, 21.0122),
        "Adres 2": (50.0647, 19.9450),
        "Niepoprawny adres": (None, None)
    }
    
    # Mockujemy funkcję geocode, aby zwracała odpowiednie wartości
    def mock_geocode(address):
        """
        Zwraca wynik geokodowania dla podanego adresu na podstawie zdefiniowanych odpowiedzi testowych.
        
        Args:
            address: Adres, dla którego ma zostać zwrócona odpowiedź geokodowania.
        
        Returns:
            Lista wyników geokodowania odpowiadająca adresowi lub pusta lista, jeśli brak odpowiedzi.
        """
        return mock_responses.get(address, [])
    
    mock_gmaps.geocode = mock_geocode
    
    return mock_gmaps, expected_coordinates

def test_get_coordinates_for_addresses_batch(mock_gmaps_geocode_with_results):
    """
    Testuje funkcję batchowego pobierania współrzędnych geograficznych dla listy adresów.
    
    Sprawdza, czy funkcja `get_coordinates_for_addresses_batch` poprawnie zwraca słownik 
    mapujący adresy na krotki (lat, lng) lub (None, None) w przypadku braku wyników,
    korzystając z mockowanego klienta Google Maps.
    """
    mock_gmaps, expected_coordinates = mock_gmaps_geocode_with_results
    
    # Dane wejściowe
    addresses = ["Adres 1", "Adres 2", "Niepoprawny adres"]
    
    # Wywołanie funkcji z mockowanym obiektem
    coordinates = get_coordinates_for_addresses_batch(mock_gmaps, addresses, batch_size=2)
    
    # Sprawdzenie wyników
    assert coordinates == expected_coordinates

def test_get_coordinates_for_addresses_batch_exception(mock_gmaps_geocode):
    """
    Testuje zachowanie funkcji get_coordinates_for_addresses_batch w przypadku wyjątku z API.
    
    Sprawdza, czy funkcja poprawnie obsługuje błędy API, zwracając (None, None) dla wszystkich
    adresów w przypadku zgłoszenia wyjątku przez geocode.
    """
    # Przygotowanie mockowanego obiektu gmaps, który zgłasza wyjątek
    mock_gmaps_geocode.geocode.side_effect = Exception("API Error")
    
    # Dane wejściowe
    addresses = ["Adres 1", "Adres 2"]
    
    # Wywołanie funkcji z mockowanym obiektem
    coordinates = get_coordinates_for_addresses_batch(mock_gmaps_geocode, addresses, batch_size=2)
    
    # Sprawdzenie wyników - funkcja powinna zwrócić None dla wszystkich adresów
    expected_coordinates = {
        "Adres 1": (None, None),
        "Adres 2": (None, None)
    }
    assert coordinates == expected_coordinates

def test_get_next_weekday_time_weekend(freeze_time):
    """
    Testuje funkcję get_next_weekday_time w weekend.
    
    Sprawdza, czy funkcja poprawnie zwraca timestamp dla poniedziałku 
    o zadanej godzinie, gdy wywołana w sobotę.
    """
    freeze_time("2025-05-17")  # Sobota
    # Funkcja powinna zwrócić timestamp dla poniedziałku (19.05.2025) o 7:30
    expected_date = datetime.datetime(2025, 5, 19, 7, 30)
    expected_timestamp = int(expected_date.timestamp())
    
    # Wywołanie funkcji
    result_timestamp = get_next_weekday_time(hour=7, minute=30)
    
    # Sprawdzenie wyników
    assert result_timestamp == expected_timestamp

def test_get_next_weekday_time_weekday_before_hour(freeze_time):
    """
    Testuje funkcję get_next_weekday_time w dzień powszedni przed zadaną godziną.
    
    Sprawdza, czy funkcja poprawnie zwraca timestamp dla tego samego dnia
    o zadanej godzinie, gdy wywołana przed tą godziną w dzień powszedni.
    """
    freeze_time("2025-05-19 06:30:00")  # Poniedziałek, przed 7:30
    # Funkcja powinna zwrócić timestamp dla tego samego dnia (19.05.2025) o 7:30
    expected_date = datetime.datetime(2025, 5, 19, 7, 30)
    expected_timestamp = int(expected_date.timestamp())
    
    # Wywołanie funkcji
    result_timestamp = get_next_weekday_time(hour=7, minute=30)
    
    # Sprawdzenie wyników
    assert result_timestamp == expected_timestamp

def test_get_next_weekday_time_weekday_after_hour(freeze_time):
    """
    Testuje funkcję get_next_weekday_time w dzień powszedni po zadanej godzinie.
    
    Sprawdza, czy funkcja poprawnie zwraca timestamp dla następnego dnia powszedniego
    o zadanej godzinie, gdy wywołana po tej godzinie w dzień powszedni.
    """
    freeze_time("2025-05-19 08:00:00")  # Poniedziałek, po 7:30
    # Funkcja powinna zwrócić timestamp dla następnego dnia (20.05.2025) o 7:30
    expected_date = datetime.datetime(2025, 5, 20, 7, 30)
    expected_timestamp = int(expected_date.timestamp())
    
    # Wywołanie funkcji
    result_timestamp = get_next_weekday_time(hour=7, minute=30)
    
    # Sprawdzenie wyników
    assert result_timestamp == expected_timestamp

def test_get_next_weekday_time_friday_after_hour(freeze_time):
    """
    Testuje funkcję get_next_weekday_time w piątek po zadanej godzinie.
    
    Sprawdza, czy funkcja poprawnie zwraca timestamp dla poniedziałku
    o zadanej godzinie, gdy wywołana po tej godzinie w piątek (czyli pomija weekend).
    """
    freeze_time("2025-05-23 08:00:00")  # Piątek, po 7:30
    # Funkcja powinna zwrócić timestamp dla poniedziałku (26.05.2025) o 7:30
    expected_date = datetime.datetime(2025, 5, 26, 7, 30)
    expected_timestamp = int(expected_date.timestamp())
    
    # Wywołanie funkcji
    result_timestamp = get_next_weekday_time(hour=7, minute=30)
    
    # Sprawdzenie wyników
    assert result_timestamp == expected_timestamp