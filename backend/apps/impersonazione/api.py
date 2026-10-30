"""Using the app as another user (see models). Who may: apps.permessi.policy."""

from datetime import datetime

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from ninja import Router, Schema
from ninja.errors import HttpError
from ninja.responses import Status

from apps.accounts.models import User
from apps.anagrafica.models import Persona
from apps.permessi import policy

from . import servizi
from .models import Impersonazione

router = Router(tags=["impersonazione"])


class Candidato(Schema):
    utente_id: int
    persona_id: int | None
    nome: str
    email: str


def _candidato(utente) -> dict:
    persona = Persona.objects.filter(utente=utente).first()
    return {
        "utente_id": utente.pk,
        "persona_id": persona.pk if persona else None,
        "nome": f"{persona.cognome} {persona.nome}" if persona else "Account senza scheda",
        "email": utente.email,
    }


@router.get("/impersonazione/candidati", response=list[Candidato])
def candidati(request, cerca: str = ""):
    """Accounts the user may act as, by name or email (at least 2 letters)."""
    if not policy.puo_impersonare_qualcuno(request.auth):
        raise HttpError(403, "Non puoi usare l'app al posto di altri.")
    cerca = cerca.strip()
    if len(cerca) < 2:
        return []
    filtro = Q(email__icontains=cerca)
    for parola in cerca.split():
        filtro |= Q(persona__nome__icontains=parola) | Q(persona__cognome__icontains=parola)
    utenti = User.objects.filter(filtro, is_active=True).distinct().order_by("email")[:200]
    trovati = [_candidato(u) for u in utenti if policy.puo_impersonare(request.auth, u)]
    return sorted(trovati, key=lambda c: c["nome"])[:30]


class Possibile(Schema):
    puo: bool


@router.get("/persone/{persona_id}/impersonabile", response=Possibile)
def impersonabile(request, persona_id: int):
    persona = get_object_or_404(Persona, pk=persona_id)
    return {
        "puo": persona.utente_id is not None
        and policy.puo_impersonare(request.auth, persona.utente)
    }


class InizioIn(Schema):
    utente_id: int | None = None
    persona_id: int | None = None
    motivo: str


class ImpersonazioneOut(Schema):
    id: int
    impersonatore: str
    impersonato: str
    motivo: str
    iniziata_il: datetime
    scade_il: datetime
    finita_il: datetime | None


def _out(i: Impersonazione) -> dict:
    return {
        "id": i.pk,
        "impersonatore": i.nome_impersonatore,
        "impersonato": servizi.nome(i.impersonato),
        "motivo": i.motivo,
        "iniziata_il": i.creato_il,
        "scade_il": i.scade_il,
        "finita_il": i.finita_il,
    }


@router.post("/impersonazione", response={201: ImpersonazioneOut})
def inizia(request, dati: InizioIn):
    if dati.persona_id is not None:
        bersaglio = get_object_or_404(Persona, pk=dati.persona_id).utente
    else:
        bersaglio = User.objects.filter(pk=dati.utente_id).first()
    if bersaglio is None:
        raise HttpError(404, "Questa persona non ha un account nell'app.")
    try:
        impersonazione = servizi.inizia(request, bersaglio, dati.motivo)
    except ValidationError as errore:
        raise HttpError(400, " ".join(errore.messages)) from errore
    except PermissionError as errore:
        raise HttpError(403, "Non puoi usare l'app al posto di questa persona.") from errore
    return Status(201, _out(impersonazione))


@router.post("/impersonazione/fine", response=dict)
def fine(request):
    """ "Torna a te": back to one's own account."""
    servizi.termina(request)
    return {"ok": True}


@router.get("/impersonazioni/mie", response=list[ImpersonazioneOut])
def mie(request):
    """Who used the app in my place, when and why."""
    return [
        _out(i)
        for i in Impersonazione.objects.filter(impersonato=request.auth).select_related(
            "impersonato"
        )[:200]
    ]


@router.get("/impersonazioni", response=list[ImpersonazioneOut])
def tutte(request):
    if not policy.puo_vedere_impersonazioni(request.auth):
        raise HttpError(403, "L'elenco lo vede la Co.Ca.")
    return [_out(i) for i in Impersonazione.objects.select_related("impersonato")[:500]]
