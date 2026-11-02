"""Secrets kept in the database, encrypted (DEC-277): the SMTP password.

The key comes from QDC_CHIAVE_SEGRETI in the server's configuration, never from the
database: a dump alone does not reveal the password. Without the key the secrets cannot
be saved. Changing the key makes the saved ones unreadable: they are entered again.
"""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


def disponibile() -> bool:
    return bool(settings.QDC_CHIAVE_SEGRETI)


def _fernet() -> Fernet:
    # Any string generated at installation: a 32-byte key derived from it.
    chiave = hashlib.sha256(settings.QDC_CHIAVE_SEGRETI.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(chiave))


def cifra(testo: str) -> str:
    return _fernet().encrypt(testo.encode()).decode()


def decifra(cifrato: str) -> str | None:
    """None when the key is missing or changed."""
    if not cifrato or not disponibile():
        return None
    try:
        return _fernet().decrypt(cifrato.encode()).decode()
    except InvalidToken:
        return None
