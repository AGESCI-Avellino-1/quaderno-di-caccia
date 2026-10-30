"""Passkeys are a way in, not a second factor: the emailed code stays the fallback
(DEC-22, DEC-240)."""

import pytest
from allauth.account.models import EmailAddress
from allauth.mfa.models import Authenticator

from apps.accounts.models import User

LOGIN = "/_allauth/browser/v1/auth/login"


@pytest.fixture
def utente(db) -> User:
    utente = User.objects.create_user(email="mario@example.invalid", password="una-password")
    EmailAddress.objects.create(user=utente, email=utente.email, verified=True, primary=True)
    return utente


def accedi(client):
    return client.post(
        LOGIN,
        {"email": "mario@example.invalid", "password": "una-password"},
        content_type="application/json",
    )


def test_a_passkey_does_not_ask_for_a_second_factor(client, utente):
    Authenticator.objects.create(user=utente, type=Authenticator.Type.WEBAUTHN, data={})
    risposta = accedi(client)
    assert risposta.status_code == 200
    assert risposta.json()["meta"]["is_authenticated"]


def test_an_authenticator_app_still_asks_for_its_code(client, utente):
    Authenticator.objects.create(user=utente, type=Authenticator.Type.TOTP, data={})
    risposta = accedi(client)
    assert risposta.status_code == 401
    in_sospeso = [f["id"] for f in risposta.json()["data"]["flows"] if f.get("is_pending")]
    assert in_sospeso == ["mfa_authenticate"]
