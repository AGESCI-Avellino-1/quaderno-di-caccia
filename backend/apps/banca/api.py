"""The bank statement (see models): loading, the lines to match with their proposals,
the confirmations; the debit cards of the units. Who: apps.permessi.policy. Online
only."""

from datetime import date, datetime
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from ninja import File, Router, Schema, Status
from ninja.errors import HttpError
from ninja.files import UploadedFile

from apps.cassa.models import Cassa, TipoCassa
from apps.eventi.models import Evento
from apps.organizzazione.models import Unita
from apps.permessi import policy
from apps.quote.models import Quota
from apps.quote.servizi import Riga

from . import servizi
from .models import CartaUnita, RigaBanca

router = Router(tags=["banca"])

DIMENSIONE_MASSIMA = 5 * 1024 * 1024


def _gestore(request) -> None:
    if not policy.puo_gestire_estratto_conto(request.auth):
        raise HttpError(
            403, "L'estratto conto lo gestiscono il tesoriere di gruppo e i capigruppo."
        )


def _conto(cassa_id: int) -> Cassa:
    return get_object_or_404(Cassa, pk=cassa_id, tipo=TipoCassa.BANCA)


def _esegui(funzione, *argomenti, **opzioni):
    try:
        return funzione(*argomenti, **opzioni)
    except ValidationError as errore:
        raise HttpError(400, " ".join(errore.messages)) from errore


# --- Cards of the units ------------------------------------------------------------------


class CartaOut(Schema):
    id: int
    unita_id: int
    unita: str
    ultime_cifre: str


class CarteOut(Schema):
    carte: list[CartaOut]
    puo_configurare: bool


def _carte(request) -> dict:
    return {
        "carte": [
            {
                "id": c.pk,
                "unita_id": c.unita_id,
                "unita": str(c.unita),
                "ultime_cifre": c.ultime_cifre,
            }
            for c in CartaUnita.objects.select_related("unita")
        ],
        "puo_configurare": policy.puo_configurare_carte(request.auth),
    }


@router.get("/banca/carte", response=CarteOut)
def carte(request):
    _gestore(request)
    return _carte(request)


class CartaIn(Schema):
    unita_id: int
    ultime_cifre: str


@router.post("/banca/carte", response={201: CarteOut})
def nuova_carta(request, dati: CartaIn):
    if not policy.puo_configurare_carte(request.auth):
        raise HttpError(403, "Le carte delle unità le registrano i capigruppo.")
    carta = CartaUnita(
        unita=get_object_or_404(Unita, pk=dati.unita_id), ultime_cifre=dati.ultime_cifre.strip()
    )
    _esegui(carta.full_clean)
    carta.save()
    return Status(201, _carte(request))


@router.delete("/banca/carte/{carta_id}", response=CarteOut)
def togli_carta(request, carta_id: int):
    if not policy.puo_configurare_carte(request.auth):
        raise HttpError(403, "Le carte delle unità le registrano i capigruppo.")
    get_object_or_404(CartaUnita, pk=carta_id).delete()
    return _carte(request)


# --- Loading ----------------------------------------------------------------------------


class SaldoOut(Schema):
    al: date
    banca: Decimal
    prima_nota: Decimal
    differenza: Decimal


class EsitoOut(Schema):
    righe_nuove: int
    righe_gia_presenti: int
    saldo_iniziale: Decimal
    saldo_finale: Decimal
    data_finale: date | None


@router.post("/banca/{cassa_id}/estratti", response={201: EsitoOut})
def carica(request, cassa_id: int, file: File[UploadedFile]):
    """The bank's "Lista Movimenti" (XLSX). The file itself is not kept."""
    _gestore(request)
    if file.size > DIMENSIONE_MASSIMA:
        raise HttpError(400, "Il file è troppo grande.")
    estratto = _esegui(servizi.carica, _conto(cassa_id), file.read(), request.auth)
    return Status(201, estratto)


# --- Lines to match ---------------------------------------------------------------------


class QuotaProposta(Schema):
    id: int
    persona: str
    descrizione: str
    residuo: Decimal
    # The share proposed for this line; 0 when the treasurer splits it.
    proposto: Decimal


class FamigliaProposta(Schema):
    quote: list[QuotaProposta]


class RegistratoProposto(Schema):
    movimenti: list[int]
    descrizione: str
    data: date


class UscitaProposta(Schema):
    tipo: str
    unita_id: int | None
    voce_id: str = ""
    cassa_destinazione_id: int | None = None


class RigaOut(Schema):
    id: int
    data: date
    operazione: str
    dettaglio: str
    importo: Decimal
    ordinante: str
    registrati: list[RegistratoProposto]
    famiglie: list[FamigliaProposta]
    uscita: UscitaProposta | None


class RigheOut(Schema):
    righe: list[RigaOut]
    confermate: int
    saldo: SaldoOut | None


def _riga_out(riga: RigaBanca) -> dict:
    uscita = None
    famiglie = []
    if riga.importo < 0:
        p = servizi.proposta_uscita(riga)
        uscita = {
            "tipo": p["tipo"],
            "unita_id": p["unita"].pk if p.get("unita") else None,
            "voce_id": p.get("voce_id", ""),
            "cassa_destinazione_id": (
                p["cassa_destinazione"].pk if p.get("cassa_destinazione") else None
            ),
        }
    else:
        famiglie = [
            {
                "quote": [
                    {
                        "id": q.pk,
                        "persona": f"{q.persona.cognome} {q.persona.nome}",
                        "descrizione": q.descrizione,
                        "residuo": q.residuo,
                        "proposto": f["ripartizione"].get(q.pk, Decimal("0")),
                    }
                    for q in f["quote"]
                ]
            }
            for f in servizi.quote_proposte(riga)
        ]
    return {
        "id": riga.pk,
        "data": riga.data,
        "operazione": riga.operazione,
        "dettaglio": riga.dettaglio,
        "importo": riga.importo,
        "ordinante": servizi.ordinante(riga),
        "registrati": servizi.movimenti_registrati(riga),
        "famiglie": famiglie,
        "uscita": uscita,
    }


@router.get("/banca/{cassa_id}/righe", response=RigheOut)
def righe(request, cassa_id: int):
    _gestore(request)
    conto = _conto(cassa_id)
    da_fare = list(servizi.da_abbinare(conto))
    return {
        "righe": [_riga_out(r) for r in da_fare],
        "confermate": RigaBanca.objects.filter(cassa=conto).count() - len(da_fare),
        "saldo": servizi.verifica_saldo(conto),
    }


class QuotaIn(Schema):
    quota_id: int
    importo: Decimal


class ConfermaIn(Schema):
    # "collega": movements recorded by hand; "quote": a fee payment; "movimento": a new
    # income or outflow; "giroconto": to a cash box.
    azione: str
    movimenti: list[int] = []
    quote: list[QuotaIn] = []
    versato_da: str = ""
    descrizione: str = ""
    voce_id: str = ""
    unita_id: int | None = None
    evento_id: int | None = None
    cassa_destinazione_id: int | None = None


class ConfermataOut(Schema):
    id: int
    confermata_il: datetime | None


@router.post("/banca/righe/{riga_id}/conferma", response=ConfermataOut)
def conferma(request, riga_id: int, dati: ConfermaIn):
    _gestore(request)
    riga = get_object_or_404(RigaBanca, pk=riga_id)
    utente = request.auth
    unita = get_object_or_404(Unita, pk=dati.unita_id) if dati.unita_id else None
    evento = get_object_or_404(Evento, pk=dati.evento_id) if dati.evento_id else None
    if dati.azione == "collega":
        return _esegui(servizi.collega, riga, dati.movimenti, utente)
    if dati.azione == "quote":
        righe_quote = [
            Riga(get_object_or_404(Quota, pk=q.quota_id), q.importo)
            for q in dati.quote
            if q.importo
        ]
        return _esegui(servizi.paga_quote, riga, righe_quote, dati.versato_da, utente)
    if dati.azione == "movimento":
        return _esegui(
            servizi.nuovo_movimento,
            riga,
            utente=utente,
            descrizione=dati.descrizione,
            voce_id=dati.voce_id,
            unita=unita,
            evento=evento,
        )
    if dati.azione == "giroconto":
        destinazione = get_object_or_404(
            Cassa, pk=dati.cassa_destinazione_id, tipo=TipoCassa.CONTANTI, attiva=True
        )
        return _esegui(
            servizi.nuovo_movimento,
            riga,
            utente=utente,
            descrizione=dati.descrizione or "Prelievo con la carta",
            unita=destinazione.unita,
            cassa_destinazione=destinazione,
        )
    raise HttpError(400, "Scegli cosa fare di questa riga.")
