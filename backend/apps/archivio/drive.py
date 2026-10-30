"""Upload to the group's shared Drive with a Google service account (DEC-196, DEC-212).

The installer creates a service account in Google Cloud, adds it to the shared drive
as content manager and gives the app its JSON key (`QDC_DRIVE_CREDENZIALI`, a path) and
the id of the folder (`QDC_DRIVE_CARTELLA`). No browser authorisation is needed. Plain
HTTPS calls to the Drive API v3: a signed JWT for the token, a multipart upload."""

import hashlib
import json
import time
import uuid
from pathlib import Path

import jwt
import requests
from django.conf import settings

URL_TOKEN = "https://oauth2.googleapis.com/token"  # noqa: S105 - a URL, not a secret
CARICA = "https://www.googleapis.com/upload/drive/v3/files"
AMBITO = "https://www.googleapis.com/auth/drive"


class ErroreDrive(Exception):
    """A message for the capogruppo, in Italian."""


def configurato() -> bool:
    return bool(settings.QDC_DRIVE_CREDENZIALI and settings.QDC_DRIVE_CARTELLA)


def _credenziali() -> dict:
    try:
        return json.loads(Path(settings.QDC_DRIVE_CREDENZIALI).read_text())
    except (OSError, ValueError) as errore:
        raise ErroreDrive(
            "Le credenziali del Drive non si leggono: avvisa chi ha installato l'app."
        ) from errore


def _token() -> str:
    chiave = _credenziali()
    adesso = int(time.time())
    asserzione = jwt.encode(
        {
            "iss": chiave["client_email"],
            "scope": AMBITO,
            "aud": URL_TOKEN,
            "iat": adesso,
            "exp": adesso + 600,
        },
        chiave["private_key"],
        algorithm="RS256",
    )
    risposta = requests.post(
        URL_TOKEN,
        data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": asserzione},
        timeout=30,
    )
    if risposta.status_code != 200:
        raise ErroreDrive("Google non ha accettato le credenziali del Drive.")
    return risposta.json()["access_token"]


def carica(nome: str, contenuto: bytes) -> dict:
    """Upload a ZIP into the configured folder; the checksum Google computes must match
    ours, or the archive does not count as saved."""
    if not configurato():
        raise ErroreDrive(
            "Il Drive del gruppo non è ancora collegato: avvisa chi ha installato l'app."
        )
    confine = uuid.uuid4().hex
    metadati = json.dumps({"name": nome, "parents": [settings.QDC_DRIVE_CARTELLA]})
    corpo = (
        (
            f"--{confine}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n{metadati}\r\n"
            f"--{confine}\r\nContent-Type: application/zip\r\n\r\n"
        ).encode()
        + contenuto
        + f"\r\n--{confine}--".encode()
    )
    risposta = requests.post(
        CARICA,
        params={
            "uploadType": "multipart",
            "supportsAllDrives": "true",
            "fields": "id,md5Checksum,size",
        },
        headers={
            "Authorization": f"Bearer {_token()}",
            "Content-Type": f"multipart/related; boundary={confine}",
        },
        data=corpo,
        timeout=120,
    )
    if risposta.status_code not in (200, 201):
        raise ErroreDrive("Il caricamento sul Drive non è riuscito: riprova più tardi.")
    dati = risposta.json()
    md5 = hashlib.md5(contenuto, usedforsecurity=False).hexdigest()
    if dati.get("md5Checksum") != md5 or int(dati.get("size", -1)) != len(contenuto):
        raise ErroreDrive(
            "Il file sul Drive non corrisponde a quello preparato: niente è stato cancellato."
        )
    return {"id": dati["id"], "md5": md5, "dimensione": len(contenuto)}
