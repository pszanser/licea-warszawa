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

def test_parse_school_html_valid_case():
    """Test poprawnego przetwarzania HTML-a z ofertą szkoły i grupami rekrutacyjnymi."""
    school_id = 123
    results = parse_school_html(VALID_SCHOOL_HTML, school_id)
    
    # Sprawdź czy zwrócono poprawną liczbę wierszy (2 oddziały)
    assert len(results) == 2
    
    # Sprawdź pierwszy wiersz (oddział 1A)
    # Pobierz faktyczną nazwę szkoły i adres z wyniku funkcji
    actual_school_name = results[0][1]
    actual_school_address = results[0][2]
    
    assert results[0][0] == 123  # ID szkoły
    assert "XCIX Liceum Ogólnokształcące z Oddziałami Dwujęzycznymi im. Zbigniewa Herberta" in actual_school_name  # Nazwa szkoły
    assert "ul. Fundamentowa 38/42, 04-036 Warszawa" in actual_school_address  # Adres szkoły
    assert results[0][3] == "1A - klasa matematyczna"  # Nazwa oddziału
    assert "matematyka" in results[0][4] and "fizyka" in results[0][4] and "informatyka" in results[0][4]  # Przedmioty rozszerzone
    assert "język angielski" in results[0][5] and "język niemiecki" in results[0][5]  # Języki obce
    assert results[0][6] == "30"  # Liczba miejsc
    assert "groupId=456" in results[0][7]  # URL grupy zawiera poprawne ID
    
    # Sprawdź drugi wiersz (oddział 1B)
    # Używamy tych samych informacji o szkole, ponieważ to ten sam HTML
    assert results[1][0] == 123  # ID szkoły
    assert "XCIX Liceum Ogólnokształcące z Oddziałami Dwujęzycznymi im. Zbigniewa Herberta" in results[1][1]  # Nazwa szkoły
    assert "ul. Fundamentowa 38/42, 04-036 Warszawa" in results[1][2]  # Adres szkoły
    assert results[1][3] == "1B - klasa humanistyczna"  # Nazwa oddziału
    assert "język polski" in results[1][4] and "historia" in results[1][4] and "wiedza o społeczeństwie" in results[1][4]  # Przedmioty rozszerzone
    assert "język angielski" in results[1][5] and "język francuski" in results[1][5]  # Języki obce
    assert results[1][6] == "28"  # Liczba miejsc
    assert "groupId=457" in results[1][7]  # URL grupy zawiera poprawne ID

def test_parse_school_html_error_page():
    """Test przetwarzania HTML-a z błędem wewnętrznym aplikacji."""
    school_id = 456
    results = parse_school_html(ERROR_SCHOOL_HTML, school_id)
    
    # Gdy wykryto błąd wewnętrzny aplikacji, funkcja powinna zwrócić pustą listę
    assert results == []

def test_parse_school_html_no_groups():
    """Test przetwarzania HTML-a bez tabeli grup rekrutacyjnych."""
    school_id = 789
    results = parse_school_html(NO_GROUPS_SCHOOL_HTML, school_id)
    
    # Gdy nie ma nagłówka "Lista grup rekrutacyjnych/oddziałów", funkcja powinna zwrócić pustą listę
    assert results == []

def test_parse_school_html_header_no_table():
    """Test przetwarzania HTML-a z nagłówkiem grupy rekrutacyjnej, ale bez tabeli."""
    school_id = 101
    results = parse_school_html(HEADER_NO_TABLE_HTML, school_id)
    
    # Gdy jest nagłówek, ale nie ma tabeli, funkcja powinna zwrócić pustą listę
    assert results == []

def test_parse_school_html_incomplete_data():
    """Test przetwarzania HTML-a z tabelą zawierającą niepełne dane."""
    school_id = 102
    # Ta funkcja powinna obsłużyć przypadek, gdy brakuje jakiejś kolumny w tabeli
    # Oczekujemy, że funkcja przeanalizuje dane, ale pominie wiersz z niepełnymi danymi
    results = parse_school_html(INCOMPLETE_DATA_HTML, school_id)
    
    # Tabela ma mniej kolumn niż oczekiwano (brak kolumny "Liczba miejsc"),
    # więc wiersz ten zostanie pominięty (len(cells) < 4)
    assert results == []

def test_parse_real_school_html():
    """Test przetwarzania rzeczywistego HTML-a ze strony szkoły Vulcan."""
    school_id = 999
    results = parse_school_html(REAL_SCHOOL_HTML, school_id)
    
    # Sprawdź czy zwrócono poprawną liczbę wierszy (2 oddziały)
    assert len(results) == 2
    
    # Sprawdź czy nazwa szkoły i adres zostały poprawnie wyodrębnione
    assert "VI Liceum Ogólnokształcące im. Tadeusza Reytana" in results[0][1]  # Nazwa szkoły
    assert "ul. Wiktorska 30/32, 02-587 Warszawa" in results[0][2]  # Adres szkoły
    
    # Sprawdź pierwszy oddział
    assert results[0][0] == 999  # ID szkoły
    assert results[0][3] == "1/1 [O] fiz-ang-mat (ang-niem)"  # Nazwa oddziału
    assert "fizyka" in results[0][4] and "język angielski" in results[0][4] and "matematyka" in results[0][4]  # Przedmioty rozszerzone
    assert "język angielski" in results[0][5] and "język niemiecki" in results[0][5]  # Języki obce
    assert results[0][6] == "32"  # Liczba miejsc
    assert "groupId=9364" in results[0][7]  # URL grupy zawiera poprawne ID
    
    # Sprawdź drugi oddział
    assert results[1][3] == "1/2 [O] fiz-ang-mat (ang-hisz)"  # Nazwa oddziału
    assert "fizyka" in results[1][4] and "język angielski" in results[1][4] and "matematyka" in results[1][4]  # Przedmioty rozszerzone
    assert "język angielski" in results[1][5] and "język hiszpański" in results[1][5]  # Języki obce
    assert results[1][6] == "32"  # Liczba miejsc
    assert "groupId=9379" in results[1][7]  # URL grupy zawiera poprawne ID