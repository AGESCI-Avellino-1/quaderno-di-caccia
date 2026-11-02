"""Sending with Gmail, no password (DEC-278).

The technical administrator links a Google mailbox once, from the settings: OAuth 2.0 with
the group's own client (created in Google Cloud), asking only to send mail
(`gmail.send`) plus the address it belongs to. The refresh token is kept encrypted
(`segreti`); every email goes out through the Gmail API as the RFC 822 bytes Django
builds, so attachments and inline images stay as they are.
"""

import contextlib
import time

import jwt
import requests
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

from . import segreti

AUTORIZZA = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN = "https://oauth2.googleapis.com/token"  # noqa: S105 - a URL, not a secret
REVOCA = "https://oauth2.googleapis.com/revoke"
INVIA = "https://gmail.googleapis.com/upload/gmail/v1/users/me/messages/send"
AMBITI = "openid email https://www.googleapis.com/auth/gmail.send"


class ErroreGmail(Exception):
    """Said in plain words to the technical administrator."""


def indirizzo_di_ritorno() -> str:
    """To register as an authorised redirect URI of the OAuth client."""
    return f"{settings.FRONTEND_URL}/api/v1/impostazioni/gmail/ritorno"


def url_autorizzazione(imp, stato: str) -> str:
    from urllib.parse import urlencode

    return f"{AUTORIZZA}?" + urlencode(
        {
            "client_id": imp.gmail_client_id,
            "redirect_uri": indirizzo_di_ritorno(),
            "response_type": "code",
            "scope": AMBITI,
            # A refresh token every time, also when the mailbox was linked before.
            "access_type": "offline",
            "prompt": "consent",
            "state": stato,
        }
    )


def _segreto(imp) -> str:
    segreto = segreti.decifra(imp.gmail_client_secret)
    if not segreto:
        raise ErroreGmail("Manca il segreto del client OAuth: inseriscilo di nuovo.")
    return segreto


def scambia_codice(imp, codice: str) -> tuple[str, str]:
    """(refresh token, address) from the code Google sent back."""
    risposta = requests.post(
        TOKEN,
        data={
            "code": codice,
            "client_id": imp.gmail_client_id,
            "client_secret": _segreto(imp),
            "redirect_uri": indirizzo_di_ritorno(),
            "grant_type": "authorization_code",
        },
        timeout=30,
    )
    if risposta.status_code != 200:
        raise ErroreGmail("Google non ha accettato il collegamento: controlla ID e segreto.")
    dati = risposta.json()
    if "refresh_token" not in dati:
        raise ErroreGmail("Google non ha dato il permesso di inviare: riprova.")
    # Straight from Google over TLS: the identity token needs no signature check here.
    identita = (
        jwt.decode(dati["id_token"], options={"verify_signature": False})
        if dati.get("id_token")
        else {}
    )
    return dati["refresh_token"], identita.get("email", "")


def revoca(imp) -> None:
    token = segreti.decifra(imp.gmail_refresh_token)
    if token:
        # Unlinked here anyway; the owner can also remove it from the Google account.
        with contextlib.suppress(requests.RequestException):
            requests.post(REVOCA, data={"token": token}, timeout=15)


_cache: dict[str, tuple[str, float]] = {}


def _accesso(imp) -> str:
    token = segreti.decifra(imp.gmail_refresh_token)
    if not token:
        raise ErroreGmail("La casella Gmail non è collegata.")
    salvato = _cache.get(token)
    if salvato and salvato[1] > time.time() + 60:
        return salvato[0]
    risposta = requests.post(
        TOKEN,
        data={
            "client_id": imp.gmail_client_id,
            "client_secret": _segreto(imp),
            "refresh_token": token,
            "grant_type": "refresh_token",
        },
        timeout=30,
    )
    if risposta.status_code != 200:
        raise ErroreGmail(
            "Google non accetta più il collegamento (revocato, o app OAuth ancora in prova): "
            "collega di nuovo la casella."
        )
    dati = risposta.json()
    _cache[token] = (dati["access_token"], time.time() + int(dati.get("expires_in", 3600)))
    return dati["access_token"]


class GmailBackend(BaseEmailBackend):
    def __init__(self, imp, **kwargs):
        super().__init__(**kwargs)
        self.imp = imp

    def send_messages(self, email_messages):
        if not email_messages:
            return 0
        accesso = _accesso(self.imp)
        inviate = 0
        for email in email_messages:
            risposta = requests.post(
                INVIA,
                params={"uploadType": "media"},
                headers={"Authorization": f"Bearer {accesso}", "Content-Type": "message/rfc822"},
                data=email.message().as_bytes(),
                timeout=60,
            )
            if risposta.status_code != 200:
                raise ErroreGmail("Gmail non ha accettato l'email: controlla il mittente.")
            inviate += 1
        return inviate
