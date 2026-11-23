"""The exit from the group recorded in the app (DEC-420): online only."""

from datetime import date, datetime
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from ninja import Router, Schema
from ninja.errors import HttpError

from apps.permessi import policy

from . import uscita as servizi
from .models import Persona

router = Router(tags=["anagrafica"])


class QuotaAnnullabile(Schema):
    id: int
    descrizione: str
    importo: Decimal


class UscitaRegistrata(Schema):
    data: date
    registrata_il: datetime
    registrata_da: str
    # Where the correction to forward to the office stands.
    stato: str
    puo_annullare: bool


class UscitaOut(Schema):
    puo_registrare: bool
    # Unpaid fees that may be cancelled with the exit.
    quote: list[QuotaAnnullabile]
    uscita: UscitaRegistrata | None


def _out(request, persona: Persona) -> dict:
    utente = request.auth
    attiva = servizi.attiva(persona)
    registra = attiva is None and (
        policy.puo_registrare_uscita(utente, persona) and servizi.puo_essere_registrata(persona)
    )
    annulla = attiva is not None and policy.puo_annullare_uscita(utente, attiva)
    if not registra and not annulla:
        raise HttpError(404, "Non trovato.")
    return {
        "puo_registrare": registra,
        "quote": (
            [
                {"id": q.pk, "descrizione": q.descrizione, "importo": q.dovuto}
                for q in servizi.quote_annullabili(persona)
            ]
            if registra
            else []
        ),
        "uscita": (
            {
                "data": attiva.data,
                "registrata_il": attiva.creato_il,
                "registrata_da": (
                    str(policy.persona_di(attiva.registrata_da) or "")
                    if attiva.registrata_da
                    else ""
                ),
                "stato": attiva.correzione.get_stato_display() if attiva.correzione else "",
                "puo_annullare": annulla,
            }
            if attiva is not None
            else None
        ),
    }


@router.get("/persone/{persona_id}/uscita", response=UscitaOut)
def leggi(request, persona_id: int):
    return _out(request, get_object_or_404(Persona, pk=persona_id))


class UscitaIn(Schema):
    data: date
    quote: list[int] = []


@router.post("/persone/{persona_id}/uscita", response=UscitaOut)
def registra(request, persona_id: int, dati: UscitaIn):
    persona = get_object_or_404(Persona, pk=persona_id)
    if not policy.puo_registrare_uscita(request.auth, persona):
        raise HttpError(403, "L'uscita la registrano lo staff dell'unità e i capigruppo.")
    try:
        servizi.registra(persona, dati.data, request.auth, dati.quote)
    except ValidationError as errore:
        raise HttpError(400, " ".join(errore.messages)) from errore
    return _out(request, persona)


@router.post("/persone/{persona_id}/uscita/annulla", response=UscitaOut)
def annulla(request, persona_id: int):
    persona = get_object_or_404(Persona, pk=persona_id)
    attiva = servizi.attiva(persona)
    if attiva is None:
        raise HttpError(400, "Non c'è un'uscita da annullare.")
    if not policy.puo_annullare_uscita(request.auth, attiva):
        raise HttpError(403, "L'uscita la annullano lo staff dell'unità e i capigruppo.")
    try:
        servizi.annulla(attiva, request.auth)
    except ValidationError as errore:
        raise HttpError(400, " ".join(errore.messages)) from errore
    return _out(request, persona)
