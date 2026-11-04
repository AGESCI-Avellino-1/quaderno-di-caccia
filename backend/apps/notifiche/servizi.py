"""Sending push notifications (DEC-345). The text is read on a locked phone: what it says is the
kind and a title, never names of people, amounts or health data. Callers pass only those."""

import base64
import json
import logging
from collections.abc import Iterable
from email.utils import parseaddr
from urllib.parse import urlsplit

import requests
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from django.conf import settings
from django.contrib.sessions.models import Session
from django.utils import timezone
from py_vapid import Vapid
from pywebpush import WebPushException, webpush

from apps.anagrafica.models import Persona
from apps.impostazioni import segreti

from .models import ChiaviPush, IscrizionePush, PreferenzePush, PushInCoda

logger = logging.getLogger(__name__)

CATEGORIE = ("eventi", "promemoria_quote", "riepiloghi", "avvisi")
# The browsers' push services. The server calls the address a browser gives it: anything else
# would let an account make it call inside its own network.
SERVIZI_PUSH = (
    "fcm.googleapis.com",
    ".push.apple.com",
    ".push.services.mozilla.com",
    ".notify.windows.com",
)
DURATA_SECONDI = 24 * 60 * 60  # A notification still waiting after a day is old news.
BLOCCO_CODA = 200


def endpoint_ammesso(endpoint: str) -> bool:
    parti = urlsplit(endpoint)
    if parti.scheme != "https" or not parti.hostname:
        return False
    return any(parti.hostname == s or parti.hostname.endswith(s) for s in SERVIZI_PUSH)


def configurate() -> bool:
    """Without the key that protects the secrets, no keys can be kept."""
    return segreti.disponibile()


def _b64(dati: bytes) -> str:
    return base64.urlsafe_b64encode(dati).rstrip(b"=").decode()


def chiavi() -> ChiaviPush:
    esistenti = ChiaviPush.objects.first()
    if esistenti is not None:
        return esistenti
    privata = ec.generate_private_key(ec.SECP256R1())
    pubblica = privata.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )
    grezza = privata.private_numbers().private_value.to_bytes(32, "big")
    return ChiaviPush.objects.create(
        pubblica=_b64(pubblica), privata_cifrata=segreti.cifra(_b64(grezza))
    )


def iscrivi(utente, sessione: str, endpoint: str, p256dh: str, auth: str) -> IscrizionePush:
    """The same browser under another account passes to it."""
    iscrizione, _ = IscrizionePush.objects.update_or_create(
        endpoint=endpoint,
        defaults={"utente": utente, "sessione": sessione, "p256dh": p256dh, "auth": auth},
    )
    return iscrizione


def togli_orfane() -> int:
    """Those whose session is over: logged out, device revoked (DEC-23), expired."""
    vive = Session.objects.filter(expire_date__gt=timezone.now()).values("session_key")
    cancellate, _ = IscrizionePush.objects.exclude(sessione__in=vive).delete()
    return cancellate


def vuole(persona: Persona, categoria: str) -> bool:
    if categoria not in CATEGORIE:
        raise ValueError(f"Categoria di notifica sconosciuta: {categoria}")
    preferenze = PreferenzePush.objects.filter(persona=persona).first()
    return preferenze is None or getattr(preferenze, categoria)


def _spedisci(iscrizione: IscrizionePush, dati: dict, firma: Vapid, contatto: str) -> bool:
    try:
        webpush(
            subscription_info={
                "endpoint": iscrizione.endpoint,
                "keys": {"p256dh": iscrizione.p256dh, "auth": iscrizione.auth},
            },
            data=json.dumps(dati),
            vapid_private_key=firma,
            vapid_claims={"sub": contatto},
            ttl=DURATA_SECONDI,
            timeout=10,
        )
    except WebPushException as errore:
        stato = errore.response.status_code if errore.response is not None else None
        if stato in (404, 410):
            # The browser no longer has it: it would never arrive again.
            iscrizione.delete()
        else:
            logger.warning("Notifica non inviata: risposta %s", stato)
        return False
    except requests.RequestException:
        logger.warning("Notifica non inviata: servizio non raggiungibile")
        return False
    return True


def _firma_e_contatto() -> tuple[Vapid, str] | None:
    grezza = segreti.decifra(chiavi().privata_cifrata)
    if grezza is None:
        logger.warning("Notifiche ferme: QDC_CHIAVE_SEGRETI mancante o cambiata")
        return None
    indirizzo = parseaddr(settings.DEFAULT_FROM_EMAIL)[1]
    return Vapid.from_raw(grezza.encode()), f"mailto:{indirizzo}"


def notifica(
    categoria: str, persone: Iterable[Persona], titolo: str, percorso: str, testo: str = ""
) -> int:
    """To who wants this kind, on every browser that said yes. Never in the way of what
    called it: an email has already gone or goes anyway."""
    if not configurate():
        return 0
    utenti = {p.utente_id for p in persone if p.utente_id and vuole(p, categoria)}
    if not utenti:
        return 0
    togli_orfane()
    iscrizioni = list(IscrizionePush.objects.filter(utente_id__in=utenti))
    if not iscrizioni:
        return 0
    dati = {"titolo": titolo, "testo": testo, "percorso": percorso}
    if settings.QDC_EMAIL_IN_CODA:
        PushInCoda.objects.bulk_create(PushInCoda(iscrizione=i, dati=dati) for i in iscrizioni)
        return len(iscrizioni)
    pronta = _firma_e_contatto()
    if pronta is None:
        return 0
    return sum(_spedisci(i, dati, *pronta) for i in iscrizioni)


def smaltisci() -> int:
    """Next block of the queue, from the «posta» service."""
    voci = list(PushInCoda.objects.select_related("iscrizione")[:BLOCCO_CODA])
    if not voci:
        return 0
    pronta = _firma_e_contatto()
    if pronta is None:
        return 0
    inviate = 0
    for voce in voci:
        # Sending may remove the subscription, and with it this row.
        inviate += _spedisci(voce.iscrizione, voce.dati, *pronta)
        PushInCoda.objects.filter(pk=voce.pk).delete()
    return inviate
