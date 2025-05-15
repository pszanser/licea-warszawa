import os
import googlemaps
import sys
from pathlib import Path

_current_file_path = Path(__file__).resolve()
_tests_dir = _current_file_path.parent # Licea/scripts/tests/
_scripts_dir = _tests_dir.parent      # Licea/scripts/
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

from api_clients.googlemaps_api import get_travel_time, get_next_weekday_time, get_coordinates_for_addresses_batch

ORIGIN = "Warszawa, Metro Wilanowska"
DESTINATION = "Warszawa, Pałac Kultury i Nauki"
SCHOOL_ADDRESS = "Warszawa, ul. Filtrowa 48"
API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
if not API_KEY:
    print("BŁĄD: Zmienna środowiskowa GOOGLE_MAPS_API_KEY nie jest ustawiona. Testy API nie mogą zostać wykonane.")
    exit(1)

def test_get_travel_time():
    departure_time = get_next_weekday_time(7, 30)
    gmaps = googlemaps.Client(key=API_KEY)
    result = get_travel_time(gmaps, ORIGIN, DESTINATION, mode="transit", departure_time=departure_time)
    print(f"Czas przejazdu o 7:30 w dzień powszedni: {result} minut" if result is not None else "Błąd pobierania czasu przejazdu")

def test_szkolalatlon():
    gmaps = googlemaps.Client(key=API_KEY)
    coords = get_coordinates_for_addresses_batch(gmaps, [SCHOOL_ADDRESS])
    lat, lon = coords[SCHOOL_ADDRESS]
    if lat is not None and lon is not None:
        print(f"Współrzędne szkoły: {lat}, {lon}")
    else:
        print("Błąd pobierania współrzędnych dla adresu.")

if __name__ == "__main__":
    print("--- Test czasu przejazdu ---")
    test_get_travel_time()
    print("\n--- Test współrzędnych szkoły ---")
    test_szkolalatlon()