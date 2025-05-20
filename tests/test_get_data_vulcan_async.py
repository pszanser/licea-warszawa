import pytest
from scripts.data_processing.get_data_vulcan_async import parse_school_html
from tests.fixtures.sample_school_html import (
    VALID_SCHOOL_HTML,
    ERROR_SCHOOL_HTML,
    NO_GROUPS_SCHOOL_HTML,
    HEADER_NO_TABLE_HTML,
    INCOMPLETE_DATA_HTML
)
from tests.fixtures.real_school_html import REAL_SCHOOL_HTML


@pytest.fixture
def valid_school_data():
    """
    Fixture zwracająca dane testowe dla poprawnego HTML-a szkoły.
    
    Zawiera ID szkoły i listę oczekiwanych wyników parsowania.
    """
    school_id = 123
    expected_results = [
        # Pierwszy oddział (1A)
        {
            "id_szkoly": 123,
            "nazwa_szkoly_match": "XCIX Liceum Ogólnokształcące z Oddziałami Dwujęzycznymi im. Zbigniewa Herberta",
            "adres_szkoly_match": "ul. Fundamentowa 38/42, 04-036 Warszawa",
            "nazwa_oddzialu": "1A - klasa matematyczna",
            "przedmioty_rozszerzone": ["matematyka", "fizyka", "informatyka"],
            "jezyki_obce": ["język angielski", "język niemiecki"],
            "liczba_miejsc": "30",
            "url_group_id": "456"
        },
        # Drugi oddział (1B)
        {
            "id_szkoly": 123,
            "nazwa_szkoly_match": "XCIX Liceum Ogólnokształcące z Oddziałami Dwujęzycznymi im. Zbigniewa Herberta",
            "adres_szkoly_match": "ul. Fundamentowa 38/42, 04-036 Warszawa",
            "nazwa_oddzialu": "1B - klasa humanistyczna",
            "przedmioty_rozszerzone": ["język polski", "historia", "wiedza o społeczeństwie"],
            "jezyki_obce": ["język angielski", "język francuski"],
            "liczba_miejsc": "28",
            "url_group_id": "457"
        }
    ]
    return school_id, expected_results


@pytest.fixture
def real_school_data():
    """
    Fixture zwracająca dane testowe dla rzeczywistego HTML-a szkoły.
    
    Zawiera ID szkoły i listę oczekiwanych wyników parsowania.
    """
    school_id = 999
    expected_results = [
        # Pierwszy oddział
        {
            "id_szkoly": 999,
            "nazwa_szkoly_match": "VI Liceum Ogólnokształcące im. Tadeusza Reytana",
            "adres_szkoly_match": "ul. Wiktorska 30/32, 02-587 Warszawa",
            "nazwa_oddzialu": "1/1 [O] fiz-ang-mat (ang-niem)",
            "przedmioty_rozszerzone_contain": ["fizyka", "język angielski", "matematyka"],
            "jezyki_obce_contain": ["język angielski", "język niemiecki"],
            "liczba_miejsc": "32",
            "url_group_id": "9364"
        },
        # Drugi oddział
        {
            "id_szkoly": 999,
            "nazwa_oddzialu": "1/2 [O] fiz-ang-mat (ang-hisz)",
            "przedmioty_rozszerzone_contain": ["fizyka", "język angielski", "matematyka"],
            "jezyki_obce_contain": ["język angielski", "język hiszpański"],
            "liczba_miejsc": "32",
            "url_group_id": "9379"
        }
    ]
    return school_id, expected_results


@pytest.mark.parametrize("html,school_id,expected_result", [
    (ERROR_SCHOOL_HTML, 456, []),
    (NO_GROUPS_SCHOOL_HTML, 789, []),
    (HEADER_NO_TABLE_HTML, 101, []),
    (INCOMPLETE_DATA_HTML, 102, [])
])
def test_parse_school_html_error_cases(html, school_id, expected_result):
    """
    Testuje zachowanie parse_school_html w przypadku niepoprawnych danych wejściowych.
    
    Sprawdza różne przypadki błędów:
    - HTML z błędem wewnętrznym aplikacji
    - HTML bez nagłówka grup rekrutacyjnych
    - HTML z nagłówkiem, ale bez tabeli
    - HTML z niepełnymi danymi w tabeli
    """
    results = parse_school_html(html, school_id)
    assert results == expected_result


def test_parse_school_html_valid_case(valid_school_data):
    """
    Testuje poprawność parsowania HTML-a z ofertą szkoły zawierającą grupy rekrutacyjne.
    
    Funkcja sprawdza, czy parse_school_html zwraca poprawnie sformatowaną listę grup rekrutacyjnych 
    na podstawie przykładowego HTML-a, weryfikując liczbę grup oraz szczegółowe dane każdej z nich, 
    takie jak ID szkoły, nazwa, adres, nazwa oddziału, przedmioty rozszerzone, języki obce, 
    liczba miejsc i poprawność linku do grupy.
    """
    school_id, expected_data = valid_school_data
    results = parse_school_html(VALID_SCHOOL_HTML, school_id)
    
    # Sprawdź czy zwrócono poprawną liczbę wierszy (2 oddziały)
    assert len(results) == 2
    
    for i, expected in enumerate(expected_data):
        # Sprawdź ID szkoły
        assert results[i][0] == expected["id_szkoly"]
        
        # Sprawdź nazwę szkoły
        assert expected["nazwa_szkoly_match"] in results[i][1]
        
        # Sprawdź adres szkoły
        assert expected["adres_szkoly_match"] in results[i][2]
        
        # Sprawdź nazwę oddziału
        assert results[i][3] == expected["nazwa_oddzialu"]
        
        # Sprawdź przedmioty rozszerzone
        for subject in expected["przedmioty_rozszerzone"]:
            assert subject in results[i][4]
        
        # Sprawdź języki obce
        for language in expected["jezyki_obce"]:
            assert language in results[i][5]
        
        # Sprawdź liczbę miejsc
        assert results[i][6] == expected["liczba_miejsc"]
        
        # Sprawdź URL grupy
        assert f"groupId={expected['url_group_id']}" in results[i][7]


def test_parse_real_school_html(real_school_data):
    """
    Testuje poprawność parsowania rzeczywistego HTML-a szkoły Vulcan przez funkcję parse_school_html.
    
    Sprawdza, czy funkcja poprawnie wyodrębnia dane o szkole i dwóch grupach rekrutacyjnych, 
    w tym nazwę szkoły, adres, nazwy oddziałów, przedmioty rozszerzone, języki obce, 
    liczbę miejsc oraz identyfikatory grup w URL-ach.
    """
    school_id, expected_data = real_school_data
    results = parse_school_html(REAL_SCHOOL_HTML, school_id)
    
    # Sprawdź czy zwrócono poprawną liczbę wierszy (2 oddziały)
    assert len(results) == 2
    
    # Sprawdź pierwszy oddział
    for i, expected in enumerate(expected_data):
        # Sprawdź ID szkoły
        assert results[i][0] == expected["id_szkoly"]
        
        # Sprawdź nazwę oddziału
        assert results[i][3] == expected["nazwa_oddzialu"]
        
        # Sprawdź przedmioty rozszerzone
        for subject in expected["przedmioty_rozszerzone_contain"]:
            assert subject in results[i][4]
        
        # Sprawdź języki obce
        for language in expected["jezyki_obce_contain"]:
            assert language in results[i][5]
        
        # Sprawdź liczbę miejsc
        assert results[i][6] == expected["liczba_miejsc"]
        
        # Sprawdź URL grupy
        assert f"groupId={expected['url_group_id']}" in results[i][7]
    
    # Sprawdź wspólne dane dla pierwszego oddziału
    assert expected_data[0]["nazwa_szkoly_match"] in results[0][1]
    assert expected_data[0]["adres_szkoly_match"] in results[0][2]