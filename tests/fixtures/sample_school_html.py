"""
Przykładowe dane HTML do testowania funkcji parse_school_html.
"""

# Przykład prawidłowego HTML z ofertą szkoły i grupami rekrutacyjnymi
VALID_SCHOOL_HTML = """
<html>
    <body>
        <h2>Oferta szkoły</h2>
        <br />XCIX Liceum Ogólnokształcące z Oddziałami Dwujęzycznymi im. Zbigniewa Herberta<br />ul. Fundamentowa 38/42, 04-036 Warszawa<br />tel. 224579023<br />sekretariat@99lo.edu.pl<br />
        
        <h3>Lista grup rekrutacyjnych/oddziałów</h3>
        <table>
            <thead>
                <tr>
                    <th title="Nazwa oddziału">Nazwa oddziału</th>
                    <th title="Przedmioty rozszerzone" style="width:15%">Przedmioty rozszerzone</th>
                    <th title="Języki obce">Języki obce</th>
                    <th title="Liczba miejsc" style="width:10%">Liczba miejsc</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td data-label="Nazwa oddziału"><a href="/kandydat/app/offer_group_details.xhtml?groupId=456">1A - klasa matematyczna</a></td>
                    <td data-label="Przedmioty rozszerzone">matematyka<br />fizyka<br />informatyka<br />
                    </td>
                    <td data-label="Języki obce"><strong>Pierwszy: </strong>język angielski<br /><strong>Drugi: </strong>język niemiecki<br />
                    </td>
                    <td data-label="Liczba miejsc">30</td>
                </tr>
                <tr>
                    <td data-label="Nazwa oddziału"><a href="/kandydat/app/offer_group_details.xhtml?groupId=457">1B - klasa humanistyczna</a></td>
                    <td data-label="Przedmioty rozszerzone">język polski<br />historia<br />wiedza o społeczeństwie<br />
                    </td>
                    <td data-label="Języki obce"><strong>Pierwszy: </strong>język angielski<br /><strong>Drugi: </strong>język francuski<br />
                    </td>
                    <td data-label="Liczba miejsc">28</td>
                </tr>
            </tbody>
        </table>
    </body>
</html>
"""

# Przykład HTML z błędem wewnętrznym aplikacji
ERROR_SCHOOL_HTML = """
<html>
    <body>
        <h2>Wewnętrzny błąd aplikacji</h2>
        <p>Przepraszamy, wystąpił błąd w działaniu aplikacji.</p>
    </body>
</html>
"""

# Przykład HTML bez tabeli grup rekrutacyjnych
NO_GROUPS_SCHOOL_HTML = """
<html>
    <body>
        <h2>Oferta szkoły</h2>
        XCIX Liceum Ogólnokształcące z Oddziałami Dwujęzycznymi im. Zbigniewa Herberta
        ul. Fundamentowa 38/42, 04-036 Warszawa
        
        <p>Brak informacji o grupach rekrutacyjnych.</p>
    </body>
</html>
"""

# Przykład HTML z nagłówkiem grupy rekrutacyjnej, ale bez tabeli
HEADER_NO_TABLE_HTML = """
<html>
    <body>
        <h2>Oferta szkoły</h2>
        XCIX Liceum Ogólnokształcące z Oddziałami Dwujęzycznymi im. Zbigniewa Herberta
        ul. Fundamentowa 38/42, 04-036 Warszawa
        
        <h3>Lista grup rekrutacyjnych/oddziałów</h3>
        <p>Tabela zostanie udostępniona wkrótce.</p>
    </body>
</html>
"""

# Przykład HTML z tabelą zawierającą niepełne dane
INCOMPLETE_DATA_HTML = """
<html>
    <body>
        <h2>Oferta szkoły</h2>
        XCIX Liceum Ogólnokształcące z Oddziałami Dwujęzycznymi im. Zbigniewa Herberta
        ul. Fundamentowa 38/42, 04-036 Warszawa
        
        <h3>Lista grup rekrutacyjnych/oddziałów</h3>
        <table>
            <thead>
                <tr>
                    <th>Oddział</th>
                    <th>Przedmioty rozszerzone</th>
                    <th>Języki obce</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td><a href="/kandydat/app/offer_details.xhtml?schoolId=123&groupId=456">1A - klasa matematyczna</a></td>
                    <td>matematyka</td>
                    <td>angielski</td>
                </tr>
            </tbody>
        </table>
    </body>
</html>
"""
