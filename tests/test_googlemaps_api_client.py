import pytest
import googlemaps
from scripts.api_clients.googlemaps_api import (
    get_travel_time,
    get_travel_times_batch,
    get_coordinates_for_addresses_batch,
    get_next_weekday_time,
)
from unittest.mock import Mock
import datetime


def _freeze_time(monkeypatch, ts: str) -> None:
    dt = datetime.datetime.fromisoformat(ts)

    class FrozenDate(datetime.date):
        @classmethod
        def today(cls):
            return dt.date()

    class FrozenDateTime(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return dt if tz is None else dt.astimezone(tz)

    monkeypatch.setattr(datetime, "date", FrozenDate)
    monkeypatch.setattr(datetime, "datetime", FrozenDateTime)

def test_get_travel_time(monkeypatch):
    # Przygotowanie mockowanego obiektu gmaps
    mock_gmaps = Mock()
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
    mock_gmaps.distance_matrix.return_value = mock_result
    
    # Wywołanie funkcji z mockowanym obiektem
    travel_time = get_travel_time(
        mock_gmaps, 
        "Adres początkowy", 
        "Adres docelowy", 
        sleep_s=0  # Wyłączamy opóźnienie w teście
    )
    
    # Sprawdzenie wyników
    assert travel_time == 30  # 30 minut
    mock_gmaps.distance_matrix.assert_called_once_with(
        origins=["Adres początkowy"],
        destinations=["Adres docelowy"],
        mode="transit",
        language="pl"
    )

def test_get_travel_time_with_departure_time(monkeypatch):
    # Przygotowanie mockowanego obiektu gmaps
    mock_gmaps = Mock()
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
    mock_gmaps.distance_matrix.return_value = mock_result
    departure_time = 1621234567  # przykładowy timestamp
    
    # Wywołanie funkcji z mockowanym obiektem
    travel_time = get_travel_time(
        mock_gmaps, 
        "Adres początkowy", 
        "Adres docelowy", 
        sleep_s=0,  # Wyłączamy opóźnienie w teście
        departure_time=departure_time
    )
    
    # Sprawdzenie wyników
    assert travel_time == 30  # 30 minut
    mock_gmaps.distance_matrix.assert_called_once_with(
        origins=["Adres początkowy"],
        destinations=["Adres docelowy"],
        mode="transit",
        language="pl",
        departure_time=departure_time
    )

def test_get_travel_time_exception(monkeypatch):
    # Przygotowanie mockowanego obiektu gmaps, który zgłasza wyjątek
    mock_gmaps = Mock()
    mock_gmaps.distance_matrix.side_effect = Exception("API Error")
    
    # Wywołanie funkcji z mockowanym obiektem
    travel_time = get_travel_time(
        mock_gmaps, 
        "Adres początkowy", 
        "Adres docelowy", 
        sleep_s=0  # Wyłączamy opóźnienie w teście
    )
    
    # Sprawdzenie wyników
    assert travel_time is None

def test_get_travel_times_batch(monkeypatch):
    # Przygotowanie mockowanego obiektu gmaps
    mock_gmaps = Mock()
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
    mock_gmaps.distance_matrix.return_value = mock_result
    
    # Dane wejściowe
    origin = "Adres początkowy"
    destinations = ["Miejsce 1", "Miejsce 2", "Miejsce niedostępne"]
    
    # Wywołanie funkcji z mockowanym obiektem
    travel_times = get_travel_times_batch(mock_gmaps, origin, destinations)
    
    # Sprawdzenie wyników
    assert travel_times == {
        "Miejsce 1": 30,
        "Miejsce 2": 40,
        "Miejsce niedostępne": None
    }
    mock_gmaps.distance_matrix.assert_called_once_with(
        origins=[origin],
        destinations=destinations,
        mode="transit",
        language="pl"
    )

def test_get_travel_times_batch_with_departure_time(monkeypatch):
    # Przygotowanie mockowanego obiektu gmaps
    mock_gmaps = Mock()
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
    mock_gmaps.distance_matrix.return_value = mock_result
    
    # Dane wejściowe
    origin = "Adres początkowy"
    destinations = ["Miejsce 1", "Miejsce 2"]
    departure_time = 1621234567  # przykładowy timestamp
    
    # Wywołanie funkcji z mockowanym obiektem
    travel_times = get_travel_times_batch(
        mock_gmaps, 
        origin, 
        destinations, 
        departure_time=departure_time
    )
    
    # Sprawdzenie wyników
    assert travel_times == {
        "Miejsce 1": 30,
        "Miejsce 2": 40
    }
    mock_gmaps.distance_matrix.assert_called_once_with(
        origins=[origin],
        destinations=destinations,
        mode="transit",
        language="pl",
        departure_time=departure_time
    )

def test_get_travel_times_batch_exception(monkeypatch):
    # Przygotowanie mockowanego obiektu gmaps, który zgłasza wyjątek
    mock_gmaps = Mock()
    mock_gmaps.distance_matrix.side_effect = Exception("API Error")
    
    # Dane wejściowe
    origin = "Adres początkowy"
    destinations = ["Miejsce 1", "Miejsce 2"]
    
    # Wywołanie funkcji z mockowanym obiektem
    travel_times = get_travel_times_batch(mock_gmaps, origin, destinations)
    
    # Sprawdzenie wyników - funkcja zwraca słownik z None dla wszystkich adresów
    assert travel_times == {
        "Miejsce 1": None,
        "Miejsce 2": None
    }

def test_get_coordinates_for_addresses_batch(monkeypatch):
    # Przygotowanie mockowanego obiektu gmaps
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
    
    # Mockujemy funkcję geocode, aby zwracała odpowiednie wartości
    def mock_geocode(address):
        return mock_responses.get(address, [])
    
    mock_gmaps.geocode = mock_geocode
    
    # Dane wejściowe
    addresses = ["Adres 1", "Adres 2", "Niepoprawny adres"]
    
    # Wywołanie funkcji z mockowanym obiektem
    coordinates = get_coordinates_for_addresses_batch(mock_gmaps, addresses, batch_size=2)
    
    # Sprawdzenie wyników
    expected_coordinates = {
        "Adres 1": (52.2297, 21.0122),
        "Adres 2": (50.0647, 19.9450),
        "Niepoprawny adres": (None, None)
    }
    assert coordinates == expected_coordinates

def test_get_coordinates_for_addresses_batch_exception(monkeypatch):
    # Przygotowanie mockowanego obiektu gmaps
    mock_gmaps = Mock()
    
    # Mock funkcji geocode, która rzuca wyjątek
    mock_gmaps.geocode.side_effect = Exception("API Error")
    
    # Dane wejściowe
    addresses = ["Adres 1", "Adres 2"]
    
    # Wywołanie funkcji z mockowanym obiektem
    coordinates = get_coordinates_for_addresses_batch(mock_gmaps, addresses, batch_size=2)
    
    # Sprawdzenie wyników - funkcja powinna zwrócić None dla wszystkich adresów
    expected_coordinates = {
        "Adres 1": (None, None),
        "Adres 2": (None, None)
    }
    assert coordinates == expected_coordinates

def test_get_next_weekday_time_weekend(monkeypatch):
    _freeze_time(monkeypatch, "2025-05-17")  # Sobota
    # Funkcja powinna zwrócić timestamp dla poniedziałku (19.05.2025) o 7:30
    expected_date = datetime.datetime(2025, 5, 19, 7, 30)
    expected_timestamp = int(expected_date.timestamp())
    
    # Wywołanie funkcji
    result_timestamp = get_next_weekday_time(hour=7, minute=30)
    
    # Sprawdzenie wyników
    assert result_timestamp == expected_timestamp

def test_get_next_weekday_time_weekday_before_hour(monkeypatch):
    _freeze_time(monkeypatch, "2025-05-19 06:30:00")  # Poniedziałek, przed 7:30
    # Funkcja powinna zwrócić timestamp dla tego samego dnia (19.05.2025) o 7:30
    expected_date = datetime.datetime(2025, 5, 19, 7, 30)
    expected_timestamp = int(expected_date.timestamp())
    
    # Wywołanie funkcji
    result_timestamp = get_next_weekday_time(hour=7, minute=30)
    
    # Sprawdzenie wyników
    assert result_timestamp == expected_timestamp

def test_get_next_weekday_time_weekday_after_hour(monkeypatch):
    _freeze_time(monkeypatch, "2025-05-19 08:00:00")  # Poniedziałek, po 7:30
    # Funkcja powinna zwrócić timestamp dla następnego dnia (20.05.2025) o 7:30
    expected_date = datetime.datetime(2025, 5, 20, 7, 30)
    expected_timestamp = int(expected_date.timestamp())
    
    # Wywołanie funkcji
    result_timestamp = get_next_weekday_time(hour=7, minute=30)
    
    # Sprawdzenie wyników
    assert result_timestamp == expected_timestamp

def test_get_next_weekday_time_friday_after_hour(monkeypatch):
    _freeze_time(monkeypatch, "2025-05-23 08:00:00")  # Piątek, po 7:30
    # Funkcja powinna zwrócić timestamp dla poniedziałku (26.05.2025) o 7:30
    expected_date = datetime.datetime(2025, 5, 26, 7, 30)
    expected_timestamp = int(expected_date.timestamp())
    
    # Wywołanie funkcji
    result_timestamp = get_next_weekday_time(hour=7, minute=30)
    
    # Sprawdzenie wyników
    assert result_timestamp == expected_timestamp