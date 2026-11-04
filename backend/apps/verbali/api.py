"""The minutes of a meeting (DEC-322…DEC-331): online only, never kept on the device."""

from datetime import datetime

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404
from ninja import File, Form, Router, Schema, Status, UploadedFile
from ninja.errors import HttpError

from apps.anagrafica.models import Appartenenza, Persona, RuoloAppartenenza
from apps.archivio import drive
from apps.eventi.models import Evento
from apps.permessi import policy
from apps.permessi.models import Azione, registra_accesso_verbale

from . import servizi, stampa
from .models import AllegatoVerbale, TipoVerbale, Verbale

router = Router(tags=["verbali"])


class PersonaVerbale(Schema):
    id: int
    nome: str
    cognome: str


class AllegatoOut(Schema):
    id: int
    nome_file: str
    dimensione: int


class AccessoOut(Schema):
    chi: str
    azione: str
    quando: datetime


class VerbaleOut(Schema):
    tipo: str
    stato: str
    testo: str
    non_previsto: bool
    # Only the Co.Ca. has reminders, so only there it can be said there are none.
    puo_dire_non_previsto: bool
    redattore: PersonaVerbale | None
    autore_nome: str
    definitivo_il: datetime | None
    puo_scrivere: bool
    puo_indicare: bool
    puo_riaprire: bool
    puo_stampare: bool
    # Who may be chosen to write: for who chooses only.
    candidati: list[PersonaVerbale]
    allegati: list[AllegatoOut]
    massimo_allegato: int
    pezzo: int
    zip_possibile: bool
    accessi: list[AccessoOut] | None


def _azione(funzione, *argomenti):
    """A refused step or a Drive that does not answer: a sentence for who is using it."""
    try:
        with transaction.atomic():
            return funzione(*argomenti)
    except ValidationError as errore:
        raise HttpError(400, " ".join(errore.messages)) from errore
    except drive.ErroreDrive as errore:
        raise HttpError(503, str(errore)) from errore


def _riunione(evento_id: int) -> Evento:
    evento = get_object_or_404(Evento.objects.select_related("squadriglia__unita"), pk=evento_id)
    if servizi.tipo_di(evento) is None:
        raise HttpError(404, "Questa riunione non ha un verbale.")
    return evento


def _leggibile(request, evento_id: int) -> Verbale:
    verbale = servizi.verbale_di(_riunione(evento_id))
    if not policy.puo_leggere_verbale(request.auth, verbale):
        # 404: who may not read does not learn whether there is anything.
        raise HttpError(404, "Non trovato.")
    return verbale


def _scrivibile(request, evento_id: int) -> Verbale:
    verbale = servizi.verbale_di(_riunione(evento_id))
    if not policy.puo_scrivere_verbale(request.auth, verbale):
        raise HttpError(403, "Non puoi scrivere questo verbale.")
    return verbale


def _gestibile(request, evento_id: int) -> Verbale:
    evento = _riunione(evento_id)
    if not policy.puo_indicare_redattore(request.auth, evento):
        raise HttpError(403, "Non puoi farlo su questo verbale.")
    return servizi.verbale_di(evento)


def _candidati(evento: Evento) -> list[Persona]:
    """The invited and the capi (DEC-324)."""
    capi = Appartenenza.objects.attive().filter(ruolo=RuoloAppartenenza.CAPO)
    return list(
        Persona.objects.filter(
            Q(pk__in=evento.partecipazioni.values("persona_id"))
            | Q(pk__in=capi.values("persona_id"))
        ).order_by("cognome", "nome")
    )


def _out(request, verbale: Verbale) -> dict:
    utente = request.auth
    evento = verbale.evento
    tipo = servizi.tipo_di(evento)
    indica = policy.puo_indicare_redattore(utente, evento)
    accessi = None
    if verbale.pk and policy.puo_vedere_accessi_verbale(utente) and tipo == TipoVerbale.COCA:
        accessi = [
            {
                "chi": a.utente.email if a.utente else "—",
                "azione": a.get_azione_display(),
                "quando": a.creato_il,
            }
            for a in verbale.accessi.select_related("utente")[:50]
        ]
    return {
        "tipo": tipo,
        "stato": verbale.stato,
        "testo": verbale.testo,
        "non_previsto": verbale.non_previsto,
        "puo_dire_non_previsto": indica and tipo == TipoVerbale.COCA and not verbale.definitivo,
        "redattore": verbale.redattore,
        "autore_nome": verbale.autore_nome,
        "definitivo_il": verbale.definitivo_il,
        "puo_scrivere": policy.puo_scrivere_verbale(utente, verbale),
        "puo_indicare": indica and not verbale.definitivo,
        "puo_riaprire": indica and verbale.definitivo,
        "puo_stampare": verbale.definitivo,
        "candidati": _candidati(evento) if indica and not verbale.definitivo else [],
        "allegati": list(servizi.allegati_completi(verbale)),
        "massimo_allegato": servizi.massimo_allegato(),
        "pezzo": servizi.PEZZO if drive.configurato() else servizi.MASSIMO_SUL_SERVER,
        "zip_possibile": verbale.definitivo
        and servizi.dimensione_zip(verbale) <= servizi.MASSIMO_ZIP,
        "accessi": accessi,
    }


def _registra(request, verbale: Verbale, azione: str) -> None:
    if verbale.pk and servizi.tipo_di(verbale.evento) == TipoVerbale.COCA and verbale.testo:
        registra_accesso_verbale(request, verbale, azione)


@router.get("/eventi/{evento_id}/verbale", response=VerbaleOut)
def leggi(request, evento_id: int, testo: bool = False):
    """Without the text unless asked for: opening a meeting is not reading its minutes, and
    only reading goes to the access log (DEC-329)."""
    verbale = _leggibile(request, evento_id)
    if not testo:
        return {**_out(request, verbale), "testo": ""}
    _registra(request, verbale, Azione.LETTURA)
    return _out(request, verbale)


class TestoIn(Schema):
    testo: str


@router.put("/eventi/{evento_id}/verbale", response=VerbaleOut)
def scrivi(request, evento_id: int, dati: TestoIn):
    verbale = _scrivibile(request, evento_id)
    autore = policy.persona_di(request.auth)
    return _out(request, _azione(servizi.salva_testo, verbale, dati.testo, autore))


class RedattoreIn(Schema):
    persona_id: int | None = None


@router.put("/eventi/{evento_id}/verbale/redattore", response=VerbaleOut)
def indica(request, evento_id: int, dati: RedattoreIn):
    verbale = _gestibile(request, evento_id)
    persona = None
    if dati.persona_id is not None:
        persona = get_object_or_404(Persona, pk=dati.persona_id)
        if persona not in _candidati(verbale.evento):
            raise HttpError(400, "Puoi scegliere una persona invitata alla riunione o un capo.")
    return _out(request, _azione(servizi.indica_redattore, verbale, persona))


class NonPrevistoIn(Schema):
    non_previsto: bool


@router.put("/eventi/{evento_id}/verbale/non-previsto", response=VerbaleOut)
def non_previsto(request, evento_id: int, dati: NonPrevistoIn):
    verbale = _gestibile(request, evento_id)
    if servizi.tipo_di(verbale.evento) != TipoVerbale.COCA:
        raise HttpError(400, "Per questa riunione il verbale è già facoltativo.")
    return _out(request, _azione(servizi.segna_non_previsto, verbale, dati.non_previsto))


@router.post("/eventi/{evento_id}/verbale/definitivo", response=VerbaleOut)
def definitivo(request, evento_id: int):
    verbale = _gestibile(request, evento_id)
    return _out(request, _azione(servizi.rendi_definitivo, verbale, request.auth))


class RiaperturaIn(Schema):
    motivo: str


@router.post("/eventi/{evento_id}/verbale/riapri", response=VerbaleOut)
def riapri(request, evento_id: int, dati: RiaperturaIn):
    verbale = _gestibile(request, evento_id)
    return _out(request, _azione(servizi.riapri, verbale, dati.motivo))


@router.get("/eventi/{evento_id}/verbale.pdf")
def pdf(request, evento_id: int):
    verbale = _leggibile(request, evento_id)
    if not verbale.definitivo:
        raise HttpError(400, "Il PDF si scarica quando il verbale è definitivo.")
    contenuto = stampa.pdf(verbale, servizi.tipo_di(verbale.evento))
    _registra(request, verbale, Azione.STAMPA)
    risposta = HttpResponse(contenuto, content_type="application/pdf")
    risposta["Content-Disposition"] = f'attachment; filename="verbale-{evento_id}.pdf"'
    risposta["Cache-Control"] = "private, no-store"
    return risposta


def _flusso(generatore, tipo: str, nome: str) -> StreamingHttpResponse:
    risposta = StreamingHttpResponse(generatore, content_type=tipo)
    risposta["Content-Disposition"] = f'attachment; filename="{nome}"'
    risposta["Cache-Control"] = "private, no-store"
    risposta["X-Content-Type-Options"] = "nosniff"
    # Passed on as it arrives: the proxies must not store a 2 GB file first.
    risposta["X-Accel-Buffering"] = "no"
    return risposta


@router.get("/eventi/{evento_id}/verbale.zip")
def zip_verbale(request, evento_id: int):
    verbale = _leggibile(request, evento_id)
    if not verbale.definitivo:
        raise HttpError(400, "Lo ZIP si scarica quando il verbale è definitivo.")
    if servizi.dimensione_zip(verbale) > servizi.MASSIMO_ZIP:
        raise HttpError(400, "Gli allegati superano 2 GB: scaricali uno per uno.")
    _registra(request, verbale, Azione.STAMPA)
    tipo = servizi.tipo_di(verbale.evento)
    return _flusso(
        servizi.zip_del_verbale(verbale, tipo), "application/zip", f"verbale-{evento_id}.zip"
    )


class NuovoAllegato(Schema):
    nome: str
    dimensione: int


@router.post("/eventi/{evento_id}/verbale/allegati", response={201: AllegatoOut})
def nuovo_allegato(request, evento_id: int, dati: NuovoAllegato):
    verbale = _scrivibile(request, evento_id)
    allegato = _azione(
        servizi.inizia_caricamento, verbale, dati.nome, dati.dimensione, request.auth
    )
    return Status(201, allegato)


def _allegato(allegato_id: int) -> AllegatoVerbale:
    return get_object_or_404(
        AllegatoVerbale.objects.select_related("verbale__evento__squadriglia__unita"),
        pk=allegato_id,
    )


class EsitoPezzo(Schema):
    ricevuti: int
    completo: bool


@router.post("/allegati-verbale/{allegato_id}/pezzo", response=EsitoPezzo)
def pezzo(request, allegato_id: int, inizio: Form[int], file: File[UploadedFile]):
    allegato = _allegato(allegato_id)
    if not policy.puo_scrivere_verbale(request.auth, allegato.verbale):
        raise HttpError(403, "Non puoi scrivere questo verbale.")
    return _azione(servizi.ricevi_pezzo, allegato, inizio, file)


@router.delete("/allegati-verbale/{allegato_id}", response={204: None})
def togli(request, allegato_id: int):
    allegato = _allegato(allegato_id)
    if not policy.puo_scrivere_verbale(request.auth, allegato.verbale):
        raise HttpError(403, "Non puoi scrivere questo verbale.")
    _azione(servizi.togli_allegato, allegato)
    return Status(204, None)


@router.get("/allegati-verbale/{allegato_id}")
def scarica(request, allegato_id: int):
    """Always through the app, which checks who may read: never a link to the Drive
    (DEC-330). Served as an attachment: the file comes from outside."""
    allegato = _allegato(allegato_id)
    if not allegato.completo or not policy.puo_leggere_verbale(request.auth, allegato.verbale):
        raise HttpError(404, "Non trovato.")
    try:
        flusso = servizi.contenuto(allegato)
    except drive.ErroreDrive as errore:
        raise HttpError(503, str(errore)) from errore
    _registra(request, allegato.verbale, Azione.LETTURA)
    risposta = _flusso(flusso, allegato.tipo_file, f"allegato-{allegato.pk}")
    risposta["Content-Disposition"] = _disposizione(allegato.nome_file)
    risposta["Content-Length"] = str(allegato.dimensione)
    return risposta


def _disposizione(nome: str) -> str:
    from django.utils.encoding import escape_uri_path

    semplice = nome.encode("ascii", "replace").decode().replace("?", "_")
    return f"attachment; filename=\"{semplice}\"; filename*=UTF-8''{escape_uri_path(nome)}"
