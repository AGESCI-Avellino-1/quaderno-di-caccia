"""Closed years and archiving: the capigruppo (DEC-44, DEC-45, DEC-209…DEC-212)."""

from datetime import date, datetime

from django.conf import settings
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from ninja import Router, Schema
from ninja.errors import HttpError

from apps.anagrafica.models import Persona
from apps.organizzazione import servizi as servizi_unita
from apps.organizzazione.models import Unita
from apps.permessi import policy

from . import drive, servizi
from .models import Archiviazione

router = Router(tags=["archivio"])


def _capogruppo(request) -> None:
    if not policy.puo_gestire_fine_anno(request.auth):
        raise HttpError(403, "Riservato ai capigruppo.")


def _esegui(funzione, *args):
    try:
        return funzione(*args)
    except ValidationError as errore:
        raise HttpError(400, " ".join(errore.messages)) from errore


class AnnoOut(Schema):
    anno: int
    etichetta: str
    in_corso: bool
    chiuso_il: datetime | None
    riaperto_fino_al: datetime | None
    motivo_riapertura: str


class AnniOut(Schema):
    anni: list[AnnoOut]
    # From 1 November, the year just ended still open.
    da_chiudere: int | None


def _anni() -> dict:
    return {"anni": servizi.anni(), "da_chiudere": servizi.anno_da_chiudere()}


@router.get("/gruppo/anni", response=AnniOut)
def anni(request):
    _capogruppo(request)
    return _anni()


@router.post("/gruppo/anni/{anno}/chiudi", response=AnniOut)
def chiudi(request, anno: int):
    _capogruppo(request)
    _esegui(servizi.chiudi_anno, anno, request.auth)
    return _anni()


class RiaperturaIn(Schema):
    fino_al: date
    motivo: str


@router.post("/gruppo/anni/{anno}/riapri", response=AnniOut)
def riapri(request, anno: int, dati: RiaperturaIn):
    _capogruppo(request)
    _esegui(servizi.riapri_anno, anno, dati.fino_al, dati.motivo, request.auth)
    return _anni()


class CandidatoOut(Schema):
    id: int
    nome: str
    uscita: date
    # Parents that go with them (DEC-214).
    genitori: list[str]


class ArchiviazioneOut(Schema):
    nome: str
    nome_file: str
    archiviata_il: datetime


class UnitaArchivioOut(Schema):
    id: int
    nome: str
    archiviata_il: date | None = None


class ArchivioOut(Schema):
    # The shared Drive is set up by who installs the app (DEC-212).
    drive_configurato: bool
    da_archiviare: list[CandidatoOut]
    archiviate: list[ArchiviazioneOut]
    # Closed units with only archived people in their history, and the archived ones
    # (DEC-275).
    unita_da_archiviare: list[UnitaArchivioOut] = []
    unita_archiviate: list[UnitaArchivioOut] = []


def _archivio() -> dict:
    return {
        # Archiving needs the Drive and the fingerprint key (DEC-212, DEC-217).
        "drive_configurato": drive.configurato() and bool(settings.QDC_IMPRONTA_CHIAVE),
        "da_archiviare": [
            {
                "id": p.pk,
                "nome": f"{p.cognome} {p.nome}",
                "uscita": p.uscita,
                "genitori": [f"{g.cognome} {g.nome}" for g in servizi.genitori_da_includere(p)],
            }
            for p in servizi.da_archiviare()
        ],
        "archiviate": [
            {"nome": a.nome, "nome_file": a.nome_file, "archiviata_il": a.creato_il}
            for a in Archiviazione.objects.all()[:50]
        ],
        "unita_da_archiviare": [
            {"id": u.pk, "nome": str(u)} for u in servizi_unita.unita_da_archiviare()
        ],
        "unita_archiviate": [
            {"id": u.pk, "nome": str(u), "archiviata_il": u.archiviata_il}
            for u in Unita.objects.filter(archiviata_il__isnull=False).order_by(
                "tipo", "codice_unita", "progressivo"
            )
        ],
    }


@router.get("/archivio", response=ArchivioOut)
def archivio(request):
    _capogruppo(request)
    return _archivio()


@router.post("/archivio/{persona_id}", response=ArchivioOut)
def archivia(request, persona_id: int):
    """One person at a time: prepared, uploaded, checked, then erased (DEC-211)."""
    _capogruppo(request)
    persona = get_object_or_404(Persona, pk=persona_id)
    _esegui(servizi.archivia, request, persona)
    return _archivio()


@router.post("/archivio/unita/{unita_id}", response=ArchivioOut)
def archivia_unita(request, unita_id: int):
    """A closed unit with only archived people in its history (DEC-275)."""
    _capogruppo(request)
    _esegui(servizi_unita.archivia_unita, get_object_or_404(Unita, pk=unita_id))
    return _archivio()


@router.post("/archivio/unita/{unita_id}/ripristina", response=ArchivioOut)
def ripristina_unita(request, unita_id: int):
    """Back among the closed units (DEC-275)."""
    _capogruppo(request)
    servizi_unita.ripristina_unita(get_object_or_404(Unita, pk=unita_id))
    return _archivio()
