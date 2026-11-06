"""Push notifications: this browser's yes or no, and what the person wants (DEC-345)."""

from django.core.exceptions import ValidationError
from ninja import Router, Schema, Status
from ninja.errors import HttpError

from apps.permessi import policy

from . import servizi
from .models import IscrizionePush, PreferenzePush

router = Router(tags=["notifiche"])


class PreferenzeIO(Schema):
    eventi: bool = True
    promemoria_quote: bool = True
    riepiloghi: bool = True
    avvisi: bool = True


class PushOut(Schema):
    disponibili: bool
    chiave_pubblica: str
    # The browser may keep its yes after the session is over.
    questo_browser: bool
    preferenze: PreferenzeIO


class IscrizioneIn(Schema):
    endpoint: str
    p256dh: str
    auth: str


class EndpointIn(Schema):
    endpoint: str


class EsitoProvaOut(Schema):
    servizio: str
    accettata: bool
    # What the push service answered; None: it could not be reached.
    codice: int | None


@router.get("/push", response=PushOut)
def stato(request, endpoint: str = ""):
    persona = policy.persona_di(request.auth)
    preferenze = None
    if persona is not None:
        preferenze = PreferenzePush.objects.filter(persona=persona).first()
    disponibili = servizi.configurate()
    return {
        "disponibili": disponibili,
        "chiave_pubblica": servizi.chiavi().pubblica if disponibili else "",
        "questo_browser": bool(endpoint)
        and IscrizionePush.objects.filter(utente=request.auth, endpoint=endpoint).exists(),
        "preferenze": preferenze or PreferenzeIO(),
    }


@router.put("/push/preferenze", response=PreferenzeIO)
def scegli(request, dati: PreferenzeIO):
    persona = policy.persona_di(request.auth)
    if persona is None:
        raise HttpError(400, "Il tuo account non è collegato a una persona del gruppo.")
    preferenze, _ = PreferenzePush.objects.update_or_create(
        persona=persona, defaults=dati.model_dump()
    )
    return preferenze


@router.post("/push/iscrizioni", response={204: None})
def iscrivi(request, dati: IscrizioneIn):
    if not servizi.configurate():
        raise HttpError(400, "Le notifiche non sono attive su questa installazione.")
    if not servizi.endpoint_ammesso(dati.endpoint):
        raise HttpError(400, "Questo browser usa un servizio di notifiche non riconosciuto.")
    if not request.session.session_key:
        raise HttpError(400, "Accedi di nuovo per attivare le notifiche.")
    try:
        servizi.iscrivi(
            request.auth, request.session.session_key, dati.endpoint, dati.p256dh, dati.auth
        )
    except ValidationError as errore:
        raise HttpError(400, " ".join(errore.messages)) from errore
    return Status(204, None)


@router.post("/push/iscrizioni/togli", response={204: None})
def togli(request, dati: EndpointIn):
    IscrizionePush.objects.filter(utente=request.auth, endpoint=dati.endpoint).delete()
    return Status(204, None)


@router.post("/push/prova", response=list[EsitoProvaOut])
def prova(request):
    """DEC-377: only to oneself, and never while acting as another user (`BLOCCATE`)."""
    if not policy.puo_provare_notifiche(request.auth):
        raise HttpError(403, "La notifica di prova la usa l'amministratore tecnico.")
    if not servizi.configurate():
        raise HttpError(400, "Le notifiche non sono attive su questa installazione.")
    try:
        return servizi.prova(request.auth)
    except servizi.ChiaviNonUtilizzabili as errore:
        raise HttpError(
            400, "Le chiavi delle notifiche non si leggono: controlla la configurazione del server."
        ) from errore
