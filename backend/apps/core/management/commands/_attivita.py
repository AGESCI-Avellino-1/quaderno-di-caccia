"""The group's activity in the test data (DEC-235): health forms, events, fees, notices,
the sentiero of a guida, a registration code, a child on the waiting list.

Everything goes through the API as the capo who would do it, so it passes the same
rules and permissions as the app. Dates are relative to today: the screenshots always
show an ongoing year.
"""

import io
import json
from datetime import date, datetime, time, timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import CommandError
from django.test import Client
from django.utils import timezone

from apps.accounts.models import User
from apps.anagrafica.models import Persona
from apps.attesa.models import InAttesa
from apps.core.anno import AnnoAssociativo
from apps.core.codice_fiscale import calcola
from apps.iscrizioni.models import CodiceIscrizione
from apps.organizzazione.models import Unita

# Fixed, so that the manual can show the page it opens.
CODICE_ISCRIZIONE = "CERCHIO2027"
LINK_ATTESA = "attesa-di-prova"


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

    def carica(self, percorso: str, file: SimpleUploadedFile, **campi: str):
        """A file sent as a form, as the app's upload fields do."""
        risposta = self.client.post(f"/api/v1{percorso}", {"file": file, **campi})
        if risposta.status_code >= 400:
            raise CommandError(
                f"POST {percorso}: {risposta.status_code} {risposta.content[:300]!r}"
            )
        return risposta.json()


def _foto_di_prova(colore: str, iniziali: str) -> SimpleUploadedFile:
    """A coloured square with initials: never a real face."""
    from PIL import Image, ImageDraw

    immagine = Image.new("RGB", (600, 600), colore)
    ImageDraw.Draw(immagine).text((250, 280), iniziali, fill="white", font_size=96)
    contenuto = io.BytesIO()
    immagine.save(contenuto, "JPEG")
    return SimpleUploadedFile("foto.jpg", contenuto.getvalue(), "image/jpeg")


def _pdf_di_prova(testo: str, nome: str = "liberatoria.pdf") -> SimpleUploadedFile:
    """A one-page PDF standing for a real form (no real model is copied)."""
    from reportlab.pdfgen.canvas import Canvas

    contenuto = io.BytesIO()
    pagina = Canvas(contenuto)
    pagina.drawString(72, 770, testo)
    pagina.save()
    return SimpleUploadedFile(nome, contenuto.getvalue(), "application/pdf")


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
    capo_clan = Api(email("Davide", "Ricci"))

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
    # How families pay (DEC-253): cash and cards to the capi, transfer to an example IBAN (valid check digits,
    # no real account), PayPal with 2 € for its costs, as the Avellino 1 does.
    tesoriera(
        "put",
        "/quote/impostazioni",
        {
            "contanti_attivo": True,
            "carte_attivo": True,
            "bonifico_attivo": True,
            "iban": "IT60X0542811101000000123456",
            "intestatario_conto": "AGESCI Gruppo Prova 1",
            "paypal_attivo": True,
            "link_pagamento": "https://example.invalid/paga",
            "paypal_maggiorazione": "FISSA",
            "paypal_valore": "2",
        },
    )
    # The cash book (DEC-85): the group's bank account and the reparto's cash box, from
    # the start of the year, before any payment comes in.
    inizio_casse = date(anno.anno_fine - 1, 10, 1).isoformat()
    conto = tesoriera(
        "post",
        "/casse",
        {
            "nome": "Conto del gruppo",
            "tipo": "BANCA",
            "saldo_iniziale": "1250.00",
            "data_saldo_iniziale": inizio_casse,
        },
    )
    cassa_reparto = tesoriera(
        "post",
        "/casse",
        {
            "nome": "Cassa del reparto",
            "tipo": "CONTANTI",
            "unita_id": reparto.pk,
            "saldo_iniziale": "80.00",
            "data_saldo_iniziale": inizio_casse,
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

    # A purchase for the reparto, and a transfer the family reports for Luca (DEC-255).
    capo_reparto(
        "post",
        "/movimenti",
        {
            "cassa_id": cassa_reparto["id"],
            "tipo": "USCITA",
            "data": (date.today() - timedelta(days=5)).isoformat(),
            "importo": "23.40",
            "descrizione": "Corde e picchetti per l'uscita",
            "voce_id": "U:A.1:0",
        },
    )
    luca = persona["Luca Rossi"].pk
    di_luca = tesoriera("get", f"/persone/{luca}/quote")
    del_gruppo = next(q for q in di_luca["quote"] if q["categoria"] == "GRUPPO")
    Api(email("Mario", "Rossi"))(
        "post",
        "/mie-quote/segnalazioni",
        {
            "metodo": "BONIFICO",
            "quote": [del_gruppo["id"]],
            "data": (date.today() - timedelta(days=1)).isoformat(),
        },
    )

    # The bank's statement (DEC-221…DEC-223), invented: the transfer already recorded by
    # hand, the one the family reported for Luca, the account's monthly fee.
    from tests.estratto_sintetico import bonifico_ricevuto, costruisci_xlsx, movimento

    estratto = costruisci_xlsx(
        "1250",
        [
            movimento(
                date.today() - timedelta(days=3),
                "ACCREDITO BEU CON CONTABILE",
                "40",
                bonifico_ricevuto("CENSIMENTO GIULIA ROSSI", "ROSSI MARIO"),
            ),
            movimento(
                date.today() - timedelta(days=1),
                "ACCREDITO BEU CON CONTABILE",
                "50",
                bonifico_ricevuto("QUOTA DI GRUPPO LUCA ROSSI", "ROSSI MARIO", "0000000002"),
            ),
            movimento(
                date.today() - timedelta(days=1),
                "CANONE MENSILE BASE E SERVIZI AGGIUNTIVI",
                "-5",
                "CANONE MENSILE",
            ),
        ],
        dal=f"{date(anno.anno_fine - 1, 10, 1):%d.%m.%Y}",
        al=f"{date.today():%d.%m.%Y}",
    )
    tesoriera.carica(
        f"/banca/{conto['id']}/estratti",
        SimpleUploadedFile(
            "lista-movimenti.xlsx",
            estratto,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ),
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
    scheda = capo_reparto(
        "post",
        f"/persone/{giulia}/progressione/impegni",
        {
            "testo": "Guidare la squadriglia con la bussola nell'uscita di novembre",
            "termine": (date.today() + timedelta(days=_sabato(2) + 1)).isoformat(),
            "criterio_verifica": "Arriviamo al rifugio seguendo il percorso che ho tracciato",
            "mete": [meta],
        },
    )
    # Two profile photos of Giulia: the capi see the earlier one too (DEC-42).
    capo_reparto.carica(f"/persone/{giulia}/foto", _foto_di_prova("#3d63ad", "GR"))
    capo_reparto.carica(f"/persone/{giulia}/foto", _foto_di_prova("#2f8f4e", "GR"))

    # Under way, so that the guida can say she is ready for the verification.
    impegno = scheda["impegni"][-1]["id"]
    capo_reparto("post", f"/progressione/impegni/{impegno}/concorda", {})
    capo_reparto("post", f"/progressione/impegni/{impegno}/avvia", {})
    scheda = capo_reparto(
        "post",
        f"/persone/{giulia}/progressione/competenze",
        {
            "tipo": "SPECIALITA",
            "codice": "EGSP064",  # Topografo
            "carta": "Disegnare la cartina del quartiere e guidare un'uscita con la bussola",
            "maestro": "Marco Ferri",
        },
    )
    capo_reparto("post", f"/competenze/{scheda['competenze'][-1]['id']}/avvia", {})

    # A registration code for the cerchio (DEC-120).
    codice = capo_cerchio(
        "post", f"/unita/{cerchio.pk}/codici-iscrizione", {"tipo": "UNITA", "scadenza": scadenza}
    )
    CodiceIscrizione.objects.filter(pk=codice["id"]).update(codice=CODICE_ISCRIZIONE)

    # A child on the waiting list (DEC-258), with the link of the family's email fixed.
    capogruppo(
        "post",
        "/attesa",
        {
            "nome": "Pietro",
            "cognome": "Colombo",
            "sesso": "M",
            "data_nascita": date(date.today().year - 7, 3, 12).isoformat(),
            "luogo_nascita": "Avellino",
            "contatto_nome": "Anna",
            "contatto_cognome": "Colombo",
            "telefono": "3337654321",
            "email": email("Anna", "Colombo"),
            "indirizzo": "Via Roma 10",
            "comune": "Avellino",
            "provincia": "AV",
            "cap": "83100",
        },
    )
    InAttesa.objects.filter(cognome="Colombo").update(token=LINK_ATTESA)

    # What the parents wrote on the signed form about Luca, and a staff note shared with
    # them (DEC-43, DEC-197…DEC-199).
    capo_reparto(
        "put",
        f"/persone/{luca}/regole-rapporto",
        {"testo": "All'uscita lo riprendono solo i genitori o la nonna, Rosa Rossi."},
    )
    capo_reparto(
        "post",
        f"/persone/{luca}/note",
        {
            "testo": "All'uscita di ottobre ha aiutato i più piccoli a montare la tenda.",
            "visibile_ragazzo": True,
            "visibile_genitori": True,
        },
    )

    # A request waiting for the cerchio staff (DEC-121): a parent already in the group
    # registers a third child with the code.
    marta = date(date.today().year - 8, 4, 3)
    Api(email("Giovanni", "Esposito"))(
        "post",
        f"/iscrizione/{CODICE_ISCRIZIONE}",
        {
            "nome": "Marta",
            "cognome": "Esposito",
            "data_nascita": marta.isoformat(),
            "codice_fiscale": calcola("Marta", "Esposito", "F", marta, "A509"),
            "sesso": "F",
            "luogo_nascita": "Avellino",
            "genitore_nome": "Giovanni",
            "genitore_cognome": "Esposito",
            "genitore_codice_fiscale": calcola(
                "Giovanni", "Esposito", "M", date(1984, 7, 12), "A509"
            ),
            "genitore_cellulare": "3330000005",
            "responsabilita": "UNICO_GENITORE",
        },
    )

    # A BuonaCaccia event (DEC-158…DEC-163): the reparto staff registered Giulia, the
    # form asks a few questions and a photo, the release form waits for the family.
    scheda = capo_reparto(
        "post",
        "/buonacaccia/schede",
        {
            "nome": "Campo di specialità",
            "domande": [
                {"tipo": "BREVE", "testo": "Taglia della maglietta", "obbligatoria": True},
                {
                    "tipo": "SCELTA_SINGOLA",
                    "testo": "Specialità che vuoi approfondire",
                    "opzioni": ["Pioniere", "Topografo", "Cuciniere"],
                    "obbligatoria": True,
                },
                {"tipo": "SI_NO", "testo": "Sai nuotare?"},
                {"tipo": "FOTO", "testo": "Una tua foto per il cartellino", "obbligatoria": True},
            ],
        },
    )
    campo = capo_reparto(
        "post",
        "/buonacaccia/eventi",
        {
            "titolo": "Campo di specialità di Zona",
            "tipo": "CAMPO",
            "inizio": _giorno(_sabato(4), time(9)),
            "fine": _giorno(_sabato(4) + 1, time(17)),
            "luogo": "Base scout di Montevergine",
        },
    )
    capo_reparto(
        "put", f"/buonacaccia/eventi/{campo['id']}/scheda", {"versione_id": scheda["ultima"]["id"]}
    )
    iscrizione = capo_reparto(
        "post",
        f"/buonacaccia/eventi/{campo['id']}/iscrizioni",
        {
            "persona_id": giulia,
            "iscritto_il": (date.today() - timedelta(days=2)).isoformat(),
            "importo": "35.00",
            "scadenza_quota": (date.today() + timedelta(days=6)).isoformat(),
        },
    )
    capo_reparto.carica(
        f"/buonacaccia/iscrizioni/{iscrizione['id']}/liberatoria",
        _pdf_di_prova("Liberatoria di prova: modulo inventato per il manuale"),
    )

    # The strada of a scolta (DEC-67, DEC-179…DEC-181, DEC-227): the Carta di clan in
    # force and signed, an obiettivo and a service under way, a Punto della Strada with
    # its private part.
    clan = Unita.objects.get(nome="Hirpinia")
    chiara = persona["Chiara Russo"].pk
    inizio_anno = date(anno.anno_fine - 1, 10, 1)
    capo_clan.carica(
        f"/unita/{clan.pk}/carta-clan",
        _pdf_di_prova("Carta di clan di prova: testo inventato per il manuale", "carta.pdf"),
        nota="Scritta alla route estiva",
        in_vigore_dal=date(anno.anno_fine - 2, 9, 1).isoformat(),
    )
    scheda = capo_clan(
        "post",
        f"/persone/{chiara}/progressione/sentiero",
        {"data": date(anno.anno_fine - 2, 10, 1).isoformat()},
    )
    periodo = scheda["periodi"][-1]["id"]
    capo_clan(
        "post",
        f"/progressione/periodi/{periodo}/promessa",
        {"data": date(anno.anno_fine - 2, 12, 8).isoformat()},
    )
    capo_clan("post", f"/progressione/periodi/{periodo}/carta", {"data": inizio_anno.isoformat()})
    scheda = capo_clan(
        "post",
        f"/persone/{chiara}/progressione/mete",
        {"testo": "Prendermi cura di chi è più fragile", "termine": None, "riservata": False},
    )
    obiettivo = scheda["mete"][-1]["id"]
    capo_clan("post", f"/progressione/mete/{obiettivo}/concorda", {})
    capo_clan("post", f"/progressione/mete/{obiettivo}/avvia", {})
    scheda = capo_clan(
        "post",
        f"/persone/{chiara}/progressione/impegni",
        {
            "testo": "Servizio il sabato pomeriggio alla mensa della Caritas",
            "termine": date(anno.anno_fine, 5, 31).isoformat(),
            "criterio_verifica": "Ne parliamo al prossimo Punto della Strada con chi coordina",
            "mete": [obiettivo],
        },
    )
    impegno = scheda["impegni"][-1]["id"]
    capo_clan("post", f"/progressione/impegni/{impegno}/concorda", {})
    capo_clan("post", f"/progressione/impegni/{impegno}/avvia", {})
    capo_clan(
        "post",
        f"/progressione/periodi/{periodo}/punti-strada",
        {
            "data": (date.today() - timedelta(days=10)).isoformat(),
            "sintesi": "Il servizio alla mensa le piace; vuole capire meglio cosa sceglie dopo.",
            "servizio": "Alla mensa da settembre, con costanza",
            "riservato": "Ha parlato con fiducia dei suoi dubbi sulla fede.",
            "obiettivi": [obiettivo],
        },
    )

    # The sentiero of a coccinella (DEC-66, DEC-182…DEC-185): the cerchio's season
    # launched, a volo and a specialità (Giocattolaio) under way.
    sofia = persona["Sofia Esposito"].pk
    stagioni = capo_cerchio(
        "post",
        f"/unita/{cerchio.pk}/stagioni",
        {
            "nome": "Stagione delle foglie",
            "inizio_previsto": (date.today() - timedelta(days=14)).isoformat(),
            "fine_prevista": date(anno.anno_fine - 1, 12, 20).isoformat(),
        },
    )
    stagione = stagioni["stagioni"][-1]["id"]
    capo_cerchio(
        "post",
        f"/stagioni/{stagione}/lancia",
        {"il": (date.today() - timedelta(days=14)).isoformat()},
    )
    scheda = capo_cerchio(
        "post",
        f"/persone/{sofia}/progressione/sentiero",
        {"data": date(anno.anno_fine - 2, 10, 1).isoformat()},
    )
    periodo = scheda["periodi"][-1]["id"]
    capo_cerchio(
        "post",
        f"/progressione/periodi/{periodo}/promessa",
        {"data": date(anno.anno_fine - 1, 2, 22).isoformat()},
    )
    scheda = capo_cerchio(
        "post",
        f"/persone/{sofia}/progressione/impegni",
        {
            "testo": "Imparare a preparare la merenda per tutto il cerchio",
            "termine": None,
            "criterio_verifica": "",
            "mete": [],
            "stagione_id": stagione,
        },
    )
    volo = scheda["impegni"][-1]["id"]
    capo_cerchio("post", f"/progressione/impegni/{volo}/concorda", {})
    capo_cerchio("post", f"/progressione/impegni/{volo}/avvia", {})
    scheda = capo_cerchio(
        "post",
        f"/persone/{sofia}/progressione/competenze",
        {"tipo": "SPECIALITA_LC", "codice": "LCSP023", "carta": "", "maestro": "Elena Conti"},
    )
    capo_cerchio("post", f"/competenze/{scheda['competenze'][-1]['id']}/avvia", {})
