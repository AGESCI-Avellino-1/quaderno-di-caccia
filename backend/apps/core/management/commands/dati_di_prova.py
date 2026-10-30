"""Fill an empty development database with invented people, for the user manual.

The manual's screenshots come from the development environment with test data, never
real data (DEC-235); its examples use these people (DEC-236). The data go through the
real BuonaStrada import (a synthetic export, as in the tests), then every profile of
the manual gets an account with the same password:

    python manage.py dati_di_prova            # empty database only
    python manage.py dati_di_prova --azzera   # wipes the database first

Refused unless DEBUG is on: it must never run on a server with real data.
"""

from datetime import date

from allauth.account.models import EmailAddress
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import Invito, User
from apps.anagrafica.models import AppartenenzaSquadriglia, Persona
from apps.core.anno import AnnoAssociativo
from apps.importazione.buonastrada import codice_cognome, codice_nome, leggi_ricerca_soci
from apps.importazione.servizi import applica
from apps.organizzazione.models import Gruppo, Incarico, RuoloIncarico, Squadriglia, Unita

PASSWORD = "manuale-di-prova"  # noqa: S105 - invented people on a development database
DOMINIO = "example.invalid"

# Month letters of the Italian fiscal code.
_MESI = "ABCDEHLMPRST"


def codice_fiscale(cognome: str, nome: str, nascita: date, sesso: str) -> str:
    """A fiscal code with the right shape (BuonaStrada would reject it: invented)."""
    giorno = nascita.day + (40 if sesso == "F" else 0)
    return (
        f"{codice_cognome(cognome)}{codice_nome(nome)}{nascita.year % 100:02d}"
        f"{_MESI[nascita.month - 1]}{giorno:02d}A509X"
    )


def email(nome: str, cognome: str) -> str:
    return f"{nome.lower().replace(' ', '')}.{cognome.lower().replace(' ', '')}@{DOMINIO}"


def genitore(cognome: str, nome: str, nascita: date, sesso: str, cellulare: str) -> str:
    """One guardian as BuonaStrada writes it in RESP.GENITORIALE DATI."""
    cf = codice_fiscale(cognome, nome, nascita, sesso)
    return (
        f"{cognome} {nome} [C.F.{cf}] - Nato/a a: AVELLINO (AV) - il: "
        f"{nascita:%d/%m/%Y} e-mail: {email(nome, cognome)} Cellulare: {cellulare}"
    )


GENITORI_ROSSI = "; ".join(
    [
        genitore("Rossi", "Mario", date(1980, 1, 1), "M", "3330000001"),
        genitore("De Luca", "Anna Maria", date(1982, 3, 1), "F", "3330000002"),
    ]
)
GENITORI_ESPOSITO = genitore("Esposito", "Giovanni", date(1984, 7, 12), "M", "3330000005")
GENITORI_MARINO = genitore("Marino", "Teresa", date(1981, 11, 3), "F", "3330000006")
GENITORI_VERDI = genitore("Verdi", "Carla", date(1979, 4, 5), "F", "3330000003")

UNITA = {
    # key: (BRANCA, TIPO UNITA, CUN, AMBIENTE UNITA, name given by the group)
    "cerchio": ("Branca L/C", "BRANCO/CERCHIO MISTO", "L", "BOSCO", "Fiordaliso"),
    "reparto": ("Branca E/G", "REPARTO MISTO", "N", "NESSUNO", "Antares"),
    "clan": ("Branca R/S", "CLAN/FUOCO", "T", "", "Hirpinia"),
    "coca": ("Adulti", "COMUNITA` CAPI", "G", "", ""),
}

# nome, cognome, sesso, nascita, unit, extra columns
PERSONE = [
    ("Sofia", "Esposito", "F", date(2017, 3, 14), "cerchio", {"RESP.GENITORIALE DATI": GENITORI_ESPOSITO}),
    ("Tommaso", "Esposito", "M", date(2018, 9, 2), "cerchio", {"RESP.GENITORIALE DATI": GENITORI_ESPOSITO}),
    ("Giulia", "Rossi", "F", date(2012, 5, 10), "reparto", {"RESP.GENITORIALE DATI": GENITORI_ROSSI}),
    ("Luca", "Rossi", "M", date(2014, 2, 2), "reparto", {"RESP.GENITORIALE DATI": GENITORI_ROSSI}),
    ("Alice", "Marino", "F", date(2013, 6, 21), "reparto", {"RESP.GENITORIALE DATI": GENITORI_MARINO}),
    ("Matteo", "Greco", "M", date(2012, 12, 8), "reparto", {}),
    ("Paolo", "Verdi", "M", date(2010, 9, 20), "clan", {"COMUNITA SOCIO": "NOVIZIATO", "RESP.GENITORIALE DATI": GENITORI_VERDI}),
    ("Chiara", "Russo", "F", date(2007, 4, 18), "clan", {"CELLULARE": "3330000010"}),
    ("Laura", "Bianchi", "F", date(1985, 6, 15), "coca", {"LIVELLO FOCA": "5", "INGRESSO COCA": "2010"}),
    ("Marco", "Ferri", "M", date(1990, 2, 11), "coca", {"LIVELLO FOCA": "4", "INGRESSO COCA": "2015"}),
    ("Elena", "Conti", "F", date(1993, 8, 30), "coca", {"LIVELLO FOCA": "3", "INGRESSO COCA": "2018"}),
    ("Francesca", "Gallo", "F", date(1988, 10, 5), "coca", {"LIVELLO FOCA": "4", "INGRESSO COCA": "2012"}),
    ("Davide", "Ricci", "M", date(1991, 1, 23), "coca", {"LIVELLO FOCA": "4", "INGRESSO COCA": "2016"}),
]  # fmt: skip

# Who logs in, one account per profile of the manual (DEC-233, DEC-237).
ACCOUNT = [
    ("Mario", "Rossi"),  # parent of Giulia and Luca
    ("Giovanni", "Esposito"),  # parent of Sofia and Tommaso (L/C)
    ("Sofia", "Esposito"),  # coccinella
    ("Luca", "Rossi"),  # esploratore
    ("Giulia", "Rossi"),  # capo squadriglia
    ("Chiara", "Russo"),  # scolta
    ("Laura", "Bianchi"),  # capogruppo
    ("Marco", "Ferri"),  # capo reparto
    ("Elena", "Conti"),  # capo cerchio
    ("Francesca", "Gallo"),  # cerchio staff, group treasurer
    ("Davide", "Ricci"),  # capo clan, technical administrator
]


class Command(BaseCommand):
    help = "Riempie il database di sviluppo con persone inventate, per il manuale."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--azzera", action="store_true", help="Cancella prima tutto il database."
        )

    def handle(self, *args, azzera: bool, **options) -> None:
        if not settings.DEBUG:
            raise CommandError("Solo in sviluppo (DEBUG attivo): mai su un server con dati veri.")
        if azzera:
            call_command("flush", interactive=False, verbosity=0)
        elif Persona.objects.exists():
            raise CommandError("Il database contiene già persone: usa --azzera per ripartire.")
        self._crea()
        self.stdout.write(
            self.style.SUCCESS(f"Dati di prova pronti; password di tutti: {PASSWORD}")
        )
        for nome, cognome in ACCOUNT:
            self.stdout.write(f"  {email(nome, cognome)}")

    @transaction.atomic
    def _crea(self) -> None:
        from tests.export_sintetico import costruisci_csv, riga

        anno = AnnoAssociativo.corrente()
        righe = []
        for numero, (nome, cognome, sesso, nascita, unita, altro) in enumerate(PERSONE, 1):
            branca, tipo, cun, ambiente, _ = UNITA[unita]
            adulto = unita in ("coca", "clan") and not altro.get("RESP.GENITORIALE DATI")
            valori = {
                "ANNO SCOUT": str(anno.anno_fine),
                "CODICE SOCIO": f"{9000000 + numero}",
                "NOME": nome,
                "COGNOME": cognome,
                "SESSO": sesso,
                "DATA NASCITA": f"{nascita:%d/%m/%Y}",
                "COMUNE NASCITA": "AVELLINO",
                "CODICE FISCALE": codice_fiscale(cognome, nome, nascita, sesso),
                "COMUNE RESIDENZA": "AVELLINO",
                "PROVINCIA RESIDENZA": "AV",
                "CAP": "83100",
                "BRANCA": branca,
                "TIPO UNITA": tipo,
                "CUN": cun,
                "AMBIENTE UNITA": ambiente,
                "DURATA": "5",
                "EMAIL": email(nome, cognome) if adulto else "",
            }
            if altro.get("RESP.GENITORIALE DATI"):
                valori["RESP.GENITORIALE TIPO"] = (
                    "Genitori" if ";" in altro["RESP.GENITORIALE DATI"] else "Unico genitore"
                )
            valori.update(altro)
            righe.append(riga(**valori))
        applica(leggi_ricerca_soci(costruisci_csv(righe)))

        inizio = anno.inizio
        gruppo = Gruppo.objects.get()
        unita = {}
        for chiave, (_, _, cun, _, nome) in UNITA.items():
            unita[chiave] = Unita.objects.get(codice_unita=cun, progressivo=1)
            if nome:
                unita[chiave].nome = nome
                unita[chiave].save(update_fields=["nome"])
        persona = {f"{p.nome} {p.cognome}": p for p in Persona.objects.all()}

        def incarico(chi: str, ruolo: str, **dove) -> None:
            nuovo = Incarico(persona=persona[chi], ruolo=ruolo, data_inizio=inizio, **dove)
            nuovo.full_clean()
            nuovo.save()

        incarico("Laura Bianchi", RuoloIncarico.CAPOGRUPPO, gruppo=gruppo)
        incarico("Francesca Gallo", RuoloIncarico.TESORIERE_GRUPPO, gruppo=gruppo)
        incarico("Davide Ricci", RuoloIncarico.AMMINISTRATORE, gruppo=gruppo)
        incarico("Marco Ferri", RuoloIncarico.CAPO_UNITA, unita=unita["reparto"])
        incarico("Elena Conti", RuoloIncarico.CAPO_UNITA, unita=unita["cerchio"])
        incarico("Francesca Gallo", RuoloIncarico.STAFF, unita=unita["cerchio"])
        incarico("Davide Ricci", RuoloIncarico.CAPO_UNITA, unita=unita["clan"])

        pantere = Squadriglia.objects.create(unita=unita["reparto"], nome="Pantere", sesso="F")
        volpi = Squadriglia.objects.create(unita=unita["reparto"], nome="Volpi", sesso="M")
        for chi, squadriglia in [
            ("Giulia Rossi", pantere),
            ("Alice Marino", pantere),
            ("Luca Rossi", volpi),
            ("Matteo Greco", volpi),
        ]:
            AppartenenzaSquadriglia.objects.create(
                persona=persona[chi], squadriglia=squadriglia, data_inizio=inizio
            )
        incarico("Giulia Rossi", RuoloIncarico.CSQ, squadriglia=pantere)
        incarico("Matteo Greco", RuoloIncarico.CSQ, squadriglia=volpi)

        for nome, cognome in ACCOUNT:
            indirizzo = email(nome, cognome)
            utente = User.objects.create_user(email=indirizzo, password=PASSWORD)
            EmailAddress.objects.create(user=utente, email=indirizzo, verified=True, primary=True)
            chi = persona[f"{nome} {cognome}"]
            chi.utente = utente
            chi.save(update_fields=["utente"])
        # The other parent of Giulia and Luca has no account yet: the manual shows the
        # page her invitation opens.
        Invito.objects.create(
            email=email("Anna Maria", "De Luca"),
            persona=persona["Anna Maria De Luca"],
            token="invito-di-prova",  # noqa: S106 - a fixed link for the screenshots
            creato_da=persona["Marco Ferri"].utente,
        )
