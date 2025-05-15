import time
import datetime

def get_travel_time(gmaps, origin_address, destination_address, mode="transit", language="pl", sleep_s=0.2, departure_time=None):
    """
    Zwraca czas dojazdu w minutach lub None, jeżeli coś nie pykło.
    Parametr gmaps to instancja klienta Google Maps API utworzona wcześniej.
    """
    try:
        kwargs = {
            "origins": [origin_address],
            "destinations": [destination_address],
            "mode": mode,
            "language": language
        }
        if departure_time is not None:
            kwargs["departure_time"] = departure_time
        result = gmaps.distance_matrix(**kwargs)
        duration_sec = result["rows"][0]["elements"][0]["duration"]["value"]
        duration_min = round(duration_sec / 60)
        time.sleep(sleep_s)
        return duration_min
    except:
        return None
    
def get_next_weekday_time(hour=7, minute=30):
    # Znajdź najbliższy dzień powszedni (pon-pt) od dziś
    today = datetime.date.today()
    weekday = today.weekday()
    # Jeśli dziś jest sobota (5) lub niedziela (6), przesuń do poniedziałku
    if weekday >= 5:
        days_ahead = 7 - weekday  # do poniedziałku
    else:
        # Jeśli dziś już po 8:00, to następny dzień powszedni
        now = datetime.datetime.now()
        if now.hour >= hour:
            days_ahead = 1
        else:
            days_ahead = 0
    next_weekday = today + datetime.timedelta(days=days_ahead)
    dt = datetime.datetime.combine(next_weekday, datetime.time(hour, minute))
    return int(dt.timestamp())

def get_travel_times_batch(gmaps, origin_address, destination_addresses, mode="transit", language="pl", departure_time=None):
    """
    Zwraca słownik {adres: czas_dojazdu} z czasami dojazdu w minutach dla wielu miejsc docelowych.
    Parametr gmaps to instancja klienta Google Maps API utworzona wcześniej.
    """
    travel_times_dict = {}
    try:
        kwargs = {
            "origins": [origin_address],
            "destinations": destination_addresses,
            "mode": mode,
            "language": language
        }
        if departure_time is not None:
            kwargs["departure_time"] = departure_time

        result = gmaps.distance_matrix(**kwargs)

        if result["rows"] and result["rows"][0]["elements"]:
            elements = result["rows"][0]["elements"]
            # Utwórz słownik mapujący adres -> czas dojazdu
            for addr, element in zip(destination_addresses, elements):
                if element.get("status") == "OK" and "duration" in element:
                    duration_sec = element["duration"]["value"]
                    travel_times_dict[addr] = round(duration_sec / 60)
                else:
                    travel_times_dict[addr] = None

        return travel_times_dict
    except Exception as e:
        print(f"Błąd podczas pobierania czasów dojazdu (batch): {e}")
        # W razie błędu zwróć słownik z None dla wszystkich adresów
        return {addr: None for addr in destination_addresses}

def get_coordinates_for_addresses_batch(gmaps, addresses, batch_size=25):
    """
    Zwraca słownik {adres: (szerokość, długość)} dla listy adresów,
    przetwarzając wiele adresów jednocześnie dla przyspieszenia działania.
    
    Parametry:
    - gmaps: instancja klienta Google Maps API
    - addresses: lista adresów do geokodowania
    - batch_size: maksymalna liczba adresów w jednej porcji (Google Maps ma limity)
    """
    coordinates_dict = {}
    
    # Przetwarzaj adresy w porcjach
    for i in range(0, len(addresses), batch_size):
        batch_addresses = addresses[i:i + batch_size]
        try:
            # Wykonaj jedno zapytanie dla wielu adresów
            geocode_results = []
            for address in batch_addresses:
                # Niestety Google Maps nie pozwala na jednoczesne geokodowanie wielu adresów w jednym wywołaniu API
                # Ale możemy zoptymalizować wydajność eliminując opóźnienie między wywołaniami
                result = gmaps.geocode(address)
                geocode_results.append((address, result))
            
            # Przetwórz wyniki
            for address, result in geocode_results:
                if result and len(result) > 0:
                    lat = result[0]["geometry"]["location"]["lat"]
                    lng = result[0]["geometry"]["location"]["lng"]
                    coordinates_dict[address] = (lat, lng)
                else:
                    coordinates_dict[address] = (None, None)
                    
        except Exception as e:
            print(f"Błąd podczas przetwarzania porcji adresów: {e}")
            # W przypadku błędu ustaw None dla wszystkich adresów w tej porcji
            for address in batch_addresses:
                coordinates_dict[address] = (None, None)
                
        # Dodaj małe opóźnienie między porcjami, aby nie przekroczyć limitów API
        time.sleep(0.5)
        
    return coordinates_dict