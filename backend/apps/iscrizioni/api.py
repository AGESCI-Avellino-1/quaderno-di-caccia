"""Joining from the app: codes, requests, approval (maintainer, 2026-10-29)."""

import io
from dataclasses import asdict
from datetime import date, datetime

import segno
from django.conf import settings
from django.core.exceptions import ValidationError
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404
from ninja import File, Form, Router, Schema, Status
from ninja.errors import HttpError
from ninja.files import UploadedFile
from ninja.throttling import AnonRateThrottle, AuthRateThrottle

from apps.organizzazione.models import Unita
from apps.permessi import policy
from apps.permessi.models import Azione, Categoria, registra_accessi

from . import servizi
from .models import (
    CAMPI_SOCIO,
    DA_COMPLETARE,
    AllegatoIscrizione,
    CodiceIscrizione,
    ModuloVuoto,
    RichiestaIscrizione,
    StatoIscrizione,
    TipoCodice,
    normalizza_codice,
    tipo_file,
)

router = Router(tags=["iscrizioni"])

# Codes can be guessed only by trying: few attempts per hour from the same address.
LIMITI = [AnonRateThrottle("30/h"), AuthRateThrottle("60/h")]
CHIAVE_SESSIONE_ISCRIZIONE = servizi.CHIAVE_SESSIONE_ISCRIZIONE


def _salva(oggetto) -> None:
    try:
        oggetto.full_clean()
    except ValidationError as errore:
        raise HttpError(400, " ".join(errore.messages)) from errore
    oggetto.save()


def _errore(funzione, *args):
    try:
        return funzione(*args)
    except ValidationError as errore:
        raise HttpError(400, " ".join(errore.messages)) from errore


# --- Codes (capi) ---------------------------------------------------------------------


class CodiceOut(Schema):
    id: int
    codice: str
    link: str
    tipo: str
    tipo_nome: str
    scadenza: date
    usi: int
    valido: bool
    creato_il: datetime


class CodiceIn(Schema):
    tipo: TipoCodice
    scadenza: date


class CodiciUnita(Schema):
    puo_creare: bool
    codici: list[CodiceOut]


def _link(codice: CodiceIscrizione) -> str:
    return f"{settings.FRONTEND_URL}/iscrizione/{codice.codice}"


def _codice_out(c: CodiceIscrizione) -> dict:
    return {
        "id": c.pk,
        "codice": c.codice,
        "link": _link(c),
        "tipo": c.tipo,
        "tipo_nome": c.get_tipo_display(),
        "scadenza": c.scadenza,
        "usi": c.usi,
        "valido": c.valido,
        "creato_il": c.creato_il,
    }


@router.get("/unita/{unita_id}/codici-iscrizione", response=CodiciUnita)
def codici_unita(request, unita_id: int):
    unita = get_object_or_404(Unita, pk=unita_id)
    if not policy.puo_creare_codici(request.auth, unita):
        return {"puo_creare": False, "codici": []}
    codici = CodiceIscrizione.objects.filter(unita=unita).select_related("unita")[:50]
    return {"puo_creare": True, "codici": [_codice_out(c) for c in codici]}


@router.post("/unita/{unita_id}/codici-iscrizione", response={201: CodiceOut})
def crea_codice(request, unita_id: int, dati: CodiceIn):
    unita = get_object_or_404(Unita, pk=unita_id)
    if not policy.puo_creare_codici(request.auth, unita):
        raise HttpError(403, "Non puoi creare codici di iscrizione per questa unità.")
    codice = CodiceIscrizione(
        unita=unita, tipo=dati.tipo, scadenza=dati.scadenza, creato_da=request.auth
    )
    _salva(codice)
    return Status(201, _codice_out(codice))


def _codice_gestibile(request, codice_id: int) -> CodiceIscrizione:
    codice = get_object_or_404(CodiceIscrizione.objects.select_related("unita"), pk=codice_id)
    if not policy.puo_creare_codici(request.auth, codice.unita):
        raise HttpError(404, "Codice non trovato.")
    return codice


@router.post("/codici-iscrizione/{codice_id}/disattiva", response=CodiceOut)
def disattiva_codice(request, codice_id: int):
    codice = _codice_gestibile(request, codice_id)
    codice.attivo = False
    codice.save(update_fields=["attivo", "aggiornato_il"])
    return _codice_out(codice)


@router.get("/codici-iscrizione/{codice_id}/qr.svg")
def qr_codice(request, codice_id: int):
    """The QR code of the link, to print or show on a phone."""
    codice = _codice_gestibile(request, codice_id)
    svg = io.BytesIO()
    segno.make(_link(codice), error="m").save(svg, kind="svg", scale=8, border=2, xmldecl=False)
    return HttpResponse(svg.getvalue(), content_type="image/svg+xml")


# --- Using a code (public, then the account) -----------------------------------------


class InfoCodice(Schema):
    codice: str
    unita: str
    per_capi: bool


class DatiIscrizioneIn(Schema):
    nome: str
    cognome: str
    data_nascita: date
    codice_fiscale: str
    email: str = ""
    genitore_nome: str = ""
    genitore_cognome: str = ""
    genitore_codice_fiscale: str = ""


class EsitoRichiesta(Schema):
    # True: the request waits in this browser session until the account is created.
    serve_account: bool
    richiesta_id: int | None = None


def _codice_valido(testo: str) -> CodiceIscrizione:
    codice = (
        CodiceIscrizione.objects.select_related("unita")
        .filter(codice=normalizza_codice(testo))
        .first()
    )
    if codice is None or not codice.valido:
        raise HttpError(404, "Codice di iscrizione non valido o scaduto.")
    return codice


@router.get("/iscrizione/{codice}", response=InfoCodice, auth=None, throttle=LIMITI)
def info_codice(request, codice: str):
    c = _codice_valido(codice)
    return {"codice": c.codice, "unita": str(c.unita), "per_capi": c.per_capi}


@router.post("/iscrizione/{codice}", response=EsitoRichiesta, auth=None, throttle=LIMITI)
def chiedi_iscrizione(request, codice: str, dati: DatiIscrizioneIn):
    """With an account: the request is created now. Without: it is kept in this browser
    session and created when the account is (accounts.adapters)."""
    c = _codice_valido(codice)
    valori = servizi.DatiIscrizione(**dati.dict())
    utente = request.user
    if getattr(utente, "is_authenticated", False):
        richiesta = _errore(servizi.crea_richiesta, c, valori, utente)
        return {"serve_account": False, "richiesta_id": richiesta.pk}
    _errore(servizi.prepara, c, valori)
    dati_sessione = asdict(valori.pulisci())
    dati_sessione["data_nascita"] = valori.data_nascita.isoformat()
    request.session[CHIAVE_SESSIONE_ISCRIZIONE] = {"codice": c.codice, "dati": dati_sessione}
    return {"serve_account": True}


# --- Requests -------------------------------------------------------------------------


class RichiestaOut(Schema):
    id: int
    unita: str
    unita_id: int
    stato: str
    stato_nome: str
    nome: str
    cognome: str
    data_nascita: date
    codice_fiscale: str
    email: str
    per_minore: bool
    genitore: str | None
    richiesta_da: str | None
    creata_il: datetime
    scadenza_completamento: date | None
    motivo_rifiuto: str
    persona_id: int | None
    # What the family still has to complete, in words.
    mancanti: list[str]


class Decisione(Schema):
    scadenza_completamento: date | None = None
    motivo: str = ""


def _richiesta_out(r: RichiestaIscrizione) -> dict:
    return {
        "id": r.pk,
        "unita": str(r.unita),
        "unita_id": r.unita_id,
        "stato": r.stato,
        "stato_nome": r.get_stato_display(),
        "nome": r.nome,
        "cognome": r.cognome,
        "data_nascita": r.data_nascita,
        "codice_fiscale": r.codice_fiscale,
        "email": r.email,
        "per_minore": r.per_minore,
        "genitore": f"{r.genitore_nome} {r.genitore_cognome}".strip() or None,
        "richiesta_da": r.utente.email if r.utente else None,
        "creata_il": r.creato_il,
        "scadenza_completamento": r.scadenza_completamento,
        "motivo_rifiuto": r.motivo_rifiuto,
        "persona_id": r.persona_id,
        "mancanti": servizi.mancanti(r) if r.stato in DA_COMPLETARE else [],
    }


@router.get("/mie-iscrizioni", response=list[RichiestaOut])
def mie_iscrizioni(request):
    """The requests made from this account (the only thing a waiting account sees)."""
    richieste = RichiestaIscrizione.objects.filter(utente=request.auth).select_related(
        "unita", "utente"
    )
    return [_richiesta_out(r) for r in richieste]


@router.get("/iscrizioni", response=list[RichiestaOut])
def richieste_da_decidere(request, tutte: bool = False):
    unita = policy.unita_da_approvare(request.auth)
    richieste = RichiestaIscrizione.objects.filter(unita__in=unita).select_related(
        "unita", "utente"
    )
    if not tutte:
        richieste = richieste.filter(stato=StatoIscrizione.IN_ATTESA)
    return [_richiesta_out(r) for r in richieste[:200]]


def _richiesta_decidibile(request, richiesta_id: int) -> RichiestaIscrizione:
    richiesta = get_object_or_404(
        RichiestaIscrizione.objects.select_related("unita", "utente"), pk=richiesta_id
    )
    if not policy.puo_approvare_iscrizione(request.auth, richiesta.unita):
        raise HttpError(404, "Richiesta non trovata.")
    return richiesta


@router.post("/iscrizioni/{richiesta_id}/approva", response=RichiestaOut)
def approva(request, richiesta_id: int, dati: Decisione):
    richiesta = _richiesta_decidibile(request, richiesta_id)
    if dati.scadenza_completamento is None:
        raise HttpError(400, "Indica entro quando completare dati e moduli.")
    _errore(servizi.approva, richiesta, request.auth, dati.scadenza_completamento)
    return _richiesta_out(richiesta)


@router.post("/iscrizioni/{richiesta_id}/rifiuta", response=RichiestaOut)
def rifiuta(request, richiesta_id: int, dati: Decisione):
    richiesta = _richiesta_decidibile(request, richiesta_id)
    _errore(servizi.rifiuta, richiesta, request.auth, dati.motivo)
    return _richiesta_out(richiesta)


# --- Completion -------------------------------------------------------------------------


class Completamento(Schema):
    sesso: str = ""
    luogo_nascita: str = ""
    indirizzo: str = ""
    civico: str = ""
    comune: str = ""
    provincia: str = ""
    cap: str = ""
    # For a minor: the parent's mobile; None when the member is an adult.
    cellulare_genitore: str | None = None


class StatoCompletamento(Completamento):
    richiesta: RichiestaOut


def _richiesta_da_completare(request, richiesta_id: int) -> RichiestaIscrizione:
    richiesta = get_object_or_404(
        RichiestaIscrizione.objects.select_related("unita", "utente", "persona"),
        pk=richiesta_id,
    )
    propria = request.auth is not None and richiesta.utente_id == request.auth.pk
    if not (propria or policy.puo_approvare_iscrizione(request.auth, richiesta.unita)):
        raise HttpError(404, "Iscrizione non trovata.")
    if richiesta.persona is None:
        raise HttpError(409, "La richiesta non è ancora stata accolta.")
    return richiesta


def _completamento(richiesta: RichiestaIscrizione) -> dict:
    socio = richiesta.persona
    padre_o_madre = servizi.genitore(richiesta)
    return {campo: getattr(socio, campo) for campo in CAMPI_SOCIO} | {
        "cellulare_genitore": padre_o_madre.cellulare if padre_o_madre else None,
        "richiesta": _richiesta_out(richiesta),
    }


@router.get("/iscrizioni/{richiesta_id}/completamento", response=StatoCompletamento)
def completamento(request, richiesta_id: int):
    return _completamento(_richiesta_da_completare(request, richiesta_id))


@router.put("/iscrizioni/{richiesta_id}/completamento", response=StatoCompletamento)
def completa(request, richiesta_id: int, dati: Completamento):
    """The family (or who approved) completes the data still missing."""
    richiesta = _richiesta_da_completare(request, richiesta_id)
    _errore(servizi.completa, richiesta, dati.dict(exclude_none=True))
    richiesta.refresh_from_db()
    return _completamento(richiesta)


# --- Blank forms (capigruppo) and signed forms -------------------------------------


class ModuloOut(Schema):
    id: int
    titolo: str
    attivo: bool


class Modulistica(Schema):
    puo_gestire: bool
    moduli: list[ModuloOut]


@router.get("/modulistica", response=Modulistica)
def modulistica(request):
    """Blank forms: every account may download them (they hold no personal data)."""
    gestisce = policy.puo_gestire_modulistica(request.auth)
    moduli = ModuloVuoto.objects.all() if gestisce else ModuloVuoto.objects.filter(attivo=True)
    return {"puo_gestire": gestisce, "moduli": list(moduli)}


@router.post("/modulistica", response={201: ModuloOut})
def carica_modulo(request, titolo: Form[str], file: File[UploadedFile]):
    if not policy.puo_gestire_modulistica(request.auth):
        raise HttpError(403, "La modulistica la curano i capigruppo.")
    if not titolo.strip():
        raise HttpError(400, "Scrivi il titolo del modulo.")
    if tipo_file(file.read(8)) != "application/pdf":
        raise HttpError(400, "Il modulo vuoto va caricato in PDF.")
    file.seek(0)
    modulo = ModuloVuoto.objects.create(titolo=titolo.strip(), file=file, caricato_da=request.auth)
    return Status(201, modulo)


class Attivo(Schema):
    attivo: bool


@router.post("/modulistica/{modulo_id}/attivo", response=ModuloOut)
def attiva_modulo(request, modulo_id: int, dati: Attivo):
    if not policy.puo_gestire_modulistica(request.auth):
        raise HttpError(403, "La modulistica la curano i capigruppo.")
    modulo = get_object_or_404(ModuloVuoto, pk=modulo_id)
    modulo.attivo = dati.attivo
    modulo.save(update_fields=["attivo", "aggiornato_il"])
    return modulo


@router.get("/modulistica/{modulo_id}/file")
def scarica_modulo(request, modulo_id: int):
    modulo = get_object_or_404(ModuloVuoto, pk=modulo_id, attivo=True)
    return FileResponse(modulo.file.open("rb"), as_attachment=True, filename=f"{modulo.titolo}.pdf")


class AllegatoOut(Schema):
    id: int
    nome_file: str
    tipo_contenuto: str
    caricato_il: datetime


class Moduli(Schema):
    allegati: list[AllegatoOut]
    verificati_il: datetime | None
    puo_verificare: bool


class Verifica(Schema):
    consenso_iscrizione: bool = False
    consenso_foto: bool = False
    consenso_commerciale: bool = False
    consenso_riviste: bool = False


def _moduli(request, richiesta: RichiestaIscrizione) -> dict:
    return {
        "allegati": [
            {
                "id": a.pk,
                "nome_file": a.nome_file,
                "tipo_contenuto": a.tipo_contenuto,
                "caricato_il": a.creato_il,
            }
            for a in richiesta.allegati.all()
        ],
        "verificati_il": richiesta.moduli_verificati_il,
        "puo_verificare": policy.puo_approvare_iscrizione(request.auth, richiesta.unita),
    }


@router.get("/iscrizioni/{richiesta_id}/moduli", response=Moduli)
def moduli_firmati(request, richiesta_id: int):
    return _moduli(request, _richiesta_da_completare(request, richiesta_id))


@router.post("/iscrizioni/{richiesta_id}/moduli", response=Moduli)
def carica_moduli(request, richiesta_id: int, file: File[UploadedFile]):
    richiesta = _richiesta_da_completare(request, richiesta_id)
    _errore(servizi.carica_allegato, richiesta, file, request.auth)
    return _moduli(request, richiesta)


def _allegato(request, allegato_id: int) -> AllegatoIscrizione:
    allegato = get_object_or_404(
        AllegatoIscrizione.objects.select_related("richiesta__unita", "richiesta__persona"),
        pk=allegato_id,
    )
    _richiesta_da_completare(request, allegato.richiesta_id)  # same rules as the request
    return allegato


@router.get("/moduli-firmati/{allegato_id}/file")
def scarica_modulo_firmato(request, allegato_id: int):
    """A signed scan: the family that uploaded it, who approves; capi reads go to the
    access log."""
    allegato = _allegato(request, allegato_id)
    if allegato.richiesta.utente_id != request.auth.pk:
        registra_accessi(request, [allegato.richiesta.persona], Categoria.MODULI, Azione.LETTURA)
    return FileResponse(
        allegato.file.open("rb"), content_type=allegato.tipo_contenuto, filename=allegato.nome_file
    )


@router.delete("/moduli-firmati/{allegato_id}", response=Moduli)
def togli_modulo_firmato(request, allegato_id: int):
    allegato = _allegato(request, allegato_id)
    richiesta = allegato.richiesta
    _errore(servizi.togli_allegato, allegato)
    return _moduli(request, richiesta)


@router.post("/iscrizioni/{richiesta_id}/verifica-moduli", response=RichiestaOut)
def verifica_moduli(request, richiesta_id: int, dati: Verifica):
    """A capo of the unit (or a capogruppo) checked the signed forms and reports the
    consents."""
    richiesta = _richiesta_decidibile(request, richiesta_id)
    _errore(servizi.verifica_moduli, richiesta, request.auth, dati.dict())
    registra_accessi(request, [richiesta.persona], Categoria.MODULI, Azione.MODIFICA)
    return _richiesta_out(richiesta)
