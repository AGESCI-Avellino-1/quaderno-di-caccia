import uuid
from datetime import datetime

from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Router, Schema, Status
from ninja.errors import HttpError

from apps.permessi import policy

from .middleware import CODICE_REVOCATO
from .models import CHIAVE_SESSIONE_DISPOSITIVO, Dispositivo
from .servizi import revoca

router = Router(tags=["dispositivi"])


class NuovoDispositivo(Schema):
    nome: str
    # Sent again after a new login on the same phone, to keep the same device.
    id: uuid.UUID | None = None


class DispositivoOut(Schema):
    id: uuid.UUID
    nome: str
    utente: str
    ultimo_contatto: datetime
    revocato_il: datetime | None
    corrente: bool
    offline_fino_al: datetime


def _out(dispositivo: Dispositivo, request) -> dict:
    return {
        "id": dispositivo.pk,
        "nome": dispositivo.nome,
        "utente": dispositivo.utente.email,
        "ultimo_contatto": dispositivo.ultimo_contatto,
        "revocato_il": dispositivo.revocato_il,
        "corrente": str(dispositivo.pk) == request.session.get(CHIAVE_SESSIONE_DISPOSITIVO),
        "offline_fino_al": dispositivo.offline_fino_al(),
    }


@router.post("/dispositivi", response={201: DispositivoOut})
def registra(request, dati: NuovoDispositivo):
    """Register this browser as a device that keeps data offline, and bind it to the
    session (DEC-97). Only possible online and logged in."""
    if not request.session.session_key:
        request.session.save()
    dispositivo = None
    if dati.id is not None:
        dispositivo = Dispositivo.objects.filter(pk=dati.id, utente=request.auth).first()
        if dispositivo is not None and dispositivo.revocato:
            raise HttpError(403, CODICE_REVOCATO)
    nome = dati.nome.strip()[:80] or "Dispositivo"
    if dispositivo is None:
        dispositivo = Dispositivo(utente=request.auth)
    dispositivo.nome = nome
    dispositivo.user_agent = request.headers.get("User-Agent", "")[:300]
    dispositivo.chiave_sessione = request.session.session_key
    dispositivo.ultimo_contatto = timezone.now()
    dispositivo.save()
    request.session[CHIAVE_SESSIONE_DISPOSITIVO] = str(dispositivo.pk)
    request.dispositivo = dispositivo
    return Status(201, _out(dispositivo, request))


@router.get("/dispositivi", response=list[DispositivoOut])
def elenco(request, tutti: bool = False):
    """Own devices; with ?tutti=true a capogruppo sees every device (DEC-23)."""
    dispositivi = Dispositivo.objects.select_related("utente")
    if tutti:
        if not policy.puo_revocare_dispositivi_altrui(request.auth):
            raise HttpError(403, "Solo i capigruppo vedono i dispositivi di tutti.")
    else:
        dispositivi = dispositivi.filter(utente=request.auth)
    return [_out(d, request) for d in dispositivi]


@router.post("/dispositivi/{dispositivo_id}/revoca", response=DispositivoOut)
def revoca_dispositivo(request, dispositivo_id: uuid.UUID):
    dispositivo = get_object_or_404(Dispositivo.objects.select_related("utente"), pk=dispositivo_id)
    if dispositivo.utente_id != request.auth.pk and not policy.puo_revocare_dispositivi_altrui(
        request.auth
    ):
        raise HttpError(404, "Dispositivo non trovato.")
    revoca(dispositivo, da=request.auth)
    return _out(dispositivo, request)


class StatoDispositivo(Schema):
    revocato: bool


@router.get("/dispositivi/{dispositivo_id}/stato", response=StatoDispositivo, auth=None)
def stato_dispositivo(request, dispositivo_id: uuid.UUID):
    """Checked by the app at start-up, before the PIN and without a session: revoking a
    device deletes its session, so this is how a lost phone learns it must wipe itself
    (DEC-97). The id is a random UUID; an unknown id counts as revoked."""
    dispositivo = Dispositivo.objects.filter(pk=dispositivo_id).first()
    return {"revocato": dispositivo is None or dispositivo.revocato}
