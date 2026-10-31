"""The group's activity in the test data (DEC-235): health forms, events, fees, notices,
the sentiero of a guida, a registration code.

Everything goes through the API as the capo who would do it, so it passes the same
rules and permissions as the app. Dates are relative to today: the screenshots always
show an ongoing year.
"""

import json
from datetime import date, datetime, time, timedelta

from django.core.management.base import CommandError
from django.test import Client
from django.utils import timezone

from apps.accounts.models import User
from apps.anagrafica.models import Persona
from apps.core.anno import AnnoAssociativo
from apps.iscrizioni.models import CodiceIscrizione
from apps.organizzazione.models import Unita

# Fixed, so that the manual can show the page it opens.
CODICE_ISCRIZIONE = "CERCHIO2027"


class Api:
    """Calls to /api/v1 as one user; any error stops the command."""

    def __init__(self, email: str) -> None:
        self.client = Client(SERVER_NAME="localhost")
        self.client.force_login(
            User.objects.get(email=email), backend="django.contrib.auth.backends.ModelBackend"
        )

    def __call__(self, metodo: str, percorso: str, dati=None):
        risposta = getattr(self.client, metodo)(
            f"/api/v1{percorso}",
            data=json.dumps(dati) if dati is not None else None,
            content_type="application/json",
        )
        if risposta.status_code >= 400:
            raise CommandError(
                f"{metodo.upper()} {percorso}: {risposta.status_code} {risposta.content[:300]!r}"
            )
        return risposta.json() if risposta.content else None


def _giorno(giorni: int, ora: time) -> str:
    giorno = datetime.combine(date.today() + timedelta(days=giorni), ora)
    return timezone.make_aware(giorno).isoformat()


def _sabato(settimane: int) -> int:
    """Days from today to the Saturday `settimane` weeks ahead (0 = this one or next)."""
    return (5 - date.today().weekday()) % 7 + 7 * settimane


def crea_attivita(email) -> None:
    persona = {f"{p.nome} {p.cognome}": p for p in Persona.objects.all()}
    reparto = Unita.objects.get(nome="Antares")
    cerchio = Unita.objects.get(nome="Fiordaliso")
    anno = AnnoAssociativo.corrente()

    capo_reparto = Api(email("Marco", "Ferri"))
    capogruppo = Api(email("Laura", "Bianchi"))
    tesoriera = Api(email("Francesca", "Gallo"))
    capo_cerchio = Api(email("Elena", "Conti"))

    # Health essentials, written by the unit staff (DEC-113).
    giulia = persona["Giulia Rossi"].pk
    capo_reparto(
        "put",
        f"/persone/{giulia}/sanitarie",
        {
            "allergie": [
                {
                    "tipo": "ALLERGIA",
                    "sostanza": "Graminacee",
                    "gravita": "LIEVE",
                    "reazione": "Starnuti e occhi arrossati",
                    "cosa_fare": "Antistaminico",
                },
                {"tipo": "INTOLLERANZA", "sostanza": "Lattosio", "gravita": "MODERATA"},
            ],
            "farmaci": [
                {
                    "nome": "Antistaminico in compresse",
                    "posologia": "1 compressa",
                    "orari": "Al bisogno",
                    "autonomo": True,
                }
            ],
            "esigenze_alimentari": "Niente latte e latticini",
            "reperibilita_nome": "Mario Rossi",
            "reperibilita_telefono": "3330000001",
        },
    )
    capo_reparto(
        "put",
        f"/persone/{persona['Luca Rossi'].pk}/sanitarie",
        {"nessuna_allergia": True, "nessun_farmaco": True},
    )

    # Events: a meeting, an outing with its fee, a group party.
    capo_reparto(
        "post",
        "/eventi",
        {
            "titolo": "Riunione di reparto",
            "tipo": "RIUNIONE",
            "livello": "UNITA",
            "unita": [reparto.pk],
            "inizio": _giorno(_sabato(0), time(15, 30)),
            "fine": _giorno(_sabato(0), time(18, 0)),
            "luogo": "Sede del gruppo",
        },
    )
    uscita = capo_reparto(
        "post",
        "/eventi",
        {
            "titolo": "Uscita di reparto",
            "tipo": "USCITA",
            "livello": "UNITA",
            "unita": [reparto.pk],
            "inizio": _giorno(_sabato(2), time(9, 0)),
            "fine": _giorno(_sabato(2) + 1, time(17, 0)),
            "luogo": "Monti Picentini",
            "descrizione": "Zaino, sacco a pelo, pranzo al sacco per sabato.",
        },
    )
    capo_reparto(
        "put",
        f"/eventi/{uscita['id']}/quota",
        {
            "nome": "Quota dell'uscita",
            "rate": [
                {
                    "descrizione": "Viaggio e cibo",
                    "importo": "25.00",
                    "scadenza": uscita["inizio"][:10],
                }
            ],
        },
    )
    capogruppo(
        "post",
        "/eventi",
        {
            "titolo": "Festa di apertura dell'anno",
            "tipo": "ALTRO",
            "livello": "GRUPPO",
            "inizio": _giorno(_sabato(1), time(16, 0)),
            "fine": _giorno(_sabato(1), time(19, 0)),
            "luogo": "Parrocchia",
        },
    )

    # Fees: the national census and the group fee, with the family discount (DEC-80,
    # DEC-81); Giulia's census already paid.
    scadenza = (date.today() + timedelta(days=30)).isoformat()
    censimento = tesoriera(
        "post",
        "/quote/tipi",
        {
            "nome": "Censimento",
            "categoria": "CENSIMENTO",
            "anno": anno.anno_fine,
            "importo": "40.00",
            "destinatari": "TUTTI",
            "scadenza": scadenza,
        },
    )
    di_gruppo = tesoriera(
        "post",
        "/quote/tipi",
        {
            "nome": "Quota di gruppo",
            "categoria": "GRUPPO",
            "anno": anno.anno_fine,
            "importo": "60.00",
            "sconto_famiglia": "10.00",
            "destinatari": "RAGAZZI",
            "scadenza": scadenza,
        },
    )
    # How families pay (DEC-253): cash, transfer to an example IBAN (valid check digits,
    # no real account), PayPal with 2 € for its costs, as the Avellino 1 does.
    tesoriera(
        "put",
        "/quote/impostazioni",
        {
            "contanti_attivo": True,
            "bonifico_attivo": True,
            "iban": "IT60X0542811101000000123456",
            "intestatario_conto": "AGESCI Gruppo Prova 1",
            "paypal_attivo": True,
            "link_pagamento": "https://example.invalid/paga",
            "paypal_maggiorazione": "FISSA",
            "paypal_valore": "2",
        },
    )
    for tipo in (censimento, di_gruppo):
        tesoriera("post", f"/quote/tipi/{tipo['id']}/emetti")
    quote = tesoriera("get", f"/persone/{giulia}/quote")
    del_censimento = next(q for q in quote["quote"] if q["categoria"] == "CENSIMENTO")
    tesoriera(
        "post",
        "/pagamenti",
        {
            "data": (date.today() - timedelta(days=3)).isoformat(),
            "metodo": "BONIFICO",
            "versato_da": "Mario Rossi",
            "righe": [{"quota_id": del_censimento["id"], "importo": del_censimento["dovuto"]}],
        },
    )

    # Notices: one for the reparto families, one for the whole group (DEC-218).
    capo_reparto(
        "post",
        "/avvisi",
        {
            "titolo": "Uscita di reparto: cosa portare",
            "testo": "Zaino, sacco a pelo, torcia e pranzo al sacco per sabato. "
            "Ritrovo alle 9 davanti alla sede.",
            "unita_id": reparto.pk,
            "destinatari": "FAMIGLIE",
            "scade_il": uscita["inizio"][:10],
        },
    )
    capogruppo(
        "post",
        "/avvisi",
        {
            "titolo": "Assemblea dei genitori",
            "testo": "Venerdì alle 19 in sede presentiamo il programma dell'anno.",
            "destinatari": "GENITORI",
            "scade_il": (date.today() + timedelta(days=_sabato(1))).isoformat(),
        },
    )

    # Giulia's sentiero: open, Scoperta recognised, one goal (DEC-57…DEC-61).
    inizio = {"data": date(anno.anno_fine - 2, 10, 15).isoformat(), "precisione": "MESE"}
    scheda = capo_reparto("post", f"/persone/{giulia}/progressione/sentiero", inizio)
    tappa = scheda["periodi"][-1]["tappe"][0]["id"]
    capo_reparto(
        "post",
        f"/progressione/tappe/{tappa}/riconosci",
        {"data": date(anno.anno_fine - 1, 5, 20).isoformat(), "precisione": "GIORNO"},
    )
    periodo = scheda["periodi"][-1]["id"]
    capo_reparto(
        "post",
        f"/progressione/periodi/{periodo}/promessa",
        {"data": date(anno.anno_fine - 1, 3, 8).isoformat(), "precisione": "GIORNO"},
    )
    scheda = capo_reparto(
        "post",
        f"/persone/{giulia}/progressione/mete",
        {"testo": "Imparare a orientarmi con la cartina", "termine": None, "riservata": False},
    )
    meta = scheda["mete"][-1]["id"]
    capo_reparto("post", f"/progressione/mete/{meta}/concorda", {})
    capo_reparto(
        "post",
        f"/persone/{giulia}/progressione/impegni",
        {
            "testo": "Guidare la squadriglia con la bussola nell'uscita di novembre",
            "termine": (date.today() + timedelta(days=_sabato(2) + 1)).isoformat(),
            "criterio_verifica": "Arriviamo al rifugio seguendo il percorso che ho tracciato",
            "mete": [meta],
        },
    )

    # A registration code for the cerchio (DEC-120).
    codice = capo_cerchio(
        "post", f"/unita/{cerchio.pk}/codici-iscrizione", {"tipo": "UNITA", "scadenza": scadenza}
    )
    CodiceIscrizione.objects.filter(pk=codice["id"]).update(codice=CODICE_ISCRIZIONE)
