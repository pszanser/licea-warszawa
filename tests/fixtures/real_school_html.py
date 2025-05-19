"""
Rzeczywisty przykład HTML ze strony szkoły w systemie Vulcan.
"""

REAL_SCHOOL_HTML = """
<!DOCTYPE html>
<html lang="pl" data-layout-font-size="normal" xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>Nabór Szkoły ponadpodstawowe Warszawa - Oferta szkoły</title>
</head>
<body>
    <main class="body-content">
        <section class="content">
            <article>
                <h2>Oferta szkoły</h2>
                <br />VI Liceum Ogólnokształcące im. Tadeusza Reytana<br />ul. Wiktorska 30/32, 02-587 Warszawa<br />tel. 228441368<br />rekrutacja@reytan.edu.pl<br />http://www.reytan.edu.pl<br />Dyrektor: Małgorzata Tudek<br />

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
                            <td data-label="Nazwa oddziału"><a href="/kandydat/app/offer_group_details.xhtml?groupId=9364">1/1 [O] fiz-ang-mat (ang-niem)</a></td>
                            <td data-label="Przedmioty rozszerzone">fizyka<br />język angielski<br />matematyka<br />
                            </td>
                            <td data-label="Języki obce"><strong>Pierwszy: </strong>język angielski<br /><strong>Drugi: </strong>język niemiecki<br />
                            </td>
                            <td data-label="Liczba miejsc">32</td>
                        </tr>
                        <tr>
                            <td data-label="Nazwa oddziału"><a href="/kandydat/app/offer_group_details.xhtml?groupId=9379">1/2 [O] fiz-ang-mat (ang-hisz)</a></td>
                            <td data-label="Przedmioty rozszerzone">fizyka<br />język angielski<br />matematyka<br />
                            </td>
                            <td data-label="Języki obce"><strong>Pierwszy: </strong>język angielski<br /><strong>Drugi: </strong>język hiszpański<br />
                            </td>
                            <td data-label="Liczba miejsc">32</td>
                        </tr>
                    </tbody>
                </table>

                <h3>Dodatkowe informacje</h3>
                Status publiczności: Publiczna<br />
                Budynek przystosowany dla osób niepełnosprawnych: Przystosowany częściowo
            </article>
        </section>
    </main>
</body>
</html>
"""
