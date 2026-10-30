"""Closed years and archiving: the capigruppo (DEC-44, DEC-45, DEC-209…DEC-212)."""

from datetime import date, datetime

from django.conf import settings
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from ninja import Router, Schema
from ninja.errors import HttpError

from apps.anagrafica.models import Persona
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


class ArchivioOut(Schema):
    # The shared Drive is set up by who installs the app (DEC-212).
    drive_configurato: bool
    da_archiviare: list[CandidatoOut]
    archiviate: list[ArchiviazioneOut]


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
