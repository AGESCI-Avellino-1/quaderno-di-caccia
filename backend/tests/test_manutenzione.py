"""Maintenance (DEC-268) and login locks (DEC-269): the technical administrator only."""

from datetime import timedelta

import pytest
from allauth.account.models import EmailAddress
from axes.models import AccessAttempt
from django.test import Client
from django.utils import timezone

from apps.accounts.models import User
from apps.impostazioni.models import MESSAGGIO_MANUTENZIONE, Impostazioni
from apps.permessi import policy

URL = "/api/v1/impostazioni"
LOGIN = "/_allauth/browser/v1/auth/login"


@pytest.fixture
def amministratore(db) -> User:
    utente = User.objects.create_user(
        email="admin@example.invalid", password="una-password", amministratore_tecnico=True
    )
    EmailAddress.objects.create(user=utente, email=utente.email, verified=True, primary=True)
    return utente


@pytest.fixture
def tutti(capo, capogruppo, csq, ragazza, genitore, estraneo):
    return (capo, capogruppo, csq, ragazza, genitore, estraneo)


def _client(utente) -> Client:
    client = Client()
    client.force_login(utente)
    return client


def _manutenzione(utente, attiva=True, messaggio=""):
    return _client(utente).put(
        f"{URL}/manutenzione",
        {"attiva": attiva, "messaggio": messaggio},
        content_type="application/json",
    )


def _accendi(messaggio=""):
    imp = Impostazioni.carica()
    imp.manutenzione = True
    imp.messaggio_manutenzione = messaggio
    imp.save()


def _accedi(email):
    client = Client()
    risposta = client.post(
        LOGIN, {"email": email, "password": "una-password"}, content_type="application/json"
    )
    return client, risposta


# --- Maintenance -------------------------------------------------------------------------


def test_solo_l_amministratore_mette_in_manutenzione(gruppo, tutti, amministratore):
    for chi in tutti:
        assert not policy.puo_gestire_manutenzione(chi.utente)
        assert _manutenzione(chi.utente).status_code == 403
    assert not Impostazioni.carica().manutenzione
    risposta = _manutenzione(amministratore, messaggio="  Torniamo alle 18.  ")
    assert risposta.status_code == 200
    assert risposta.json()["manutenzione"] is True
    assert Impostazioni.carica().messaggio_manutenzione == "Torniamo alle 18."
    assert _manutenzione(amministratore, attiva=False).json()["manutenzione"] is False


def test_in_manutenzione_chi_e_dentro_viene_fermato(gruppo, tutti, amministratore):
    _accendi("Torniamo alle 18.")
    for chi in tutti:
        risposta = _client(chi.utente).get("/api/v1/io")
        assert risposta.status_code == 503
        assert risposta.json() == {"detail": "Torniamo alle 18.", "codice": "manutenzione"}
        # Writes too: the PWA keeps them in its queue (a 503 is retried).
        assert _client(chi.utente).put(f"{URL}/sito", {}).status_code == 503
    assert _client(amministratore).get("/api/v1/io").status_code == 200


def test_in_manutenzione_le_pagine_pubbliche_si_fermano(gruppo):
    _accendi()
    anonimo = Client()
    risposta = anonimo.get("/api/v1/lista-attesa/unita")
    assert risposta.status_code == 503
    assert risposta.json()["detail"] == MESSAGGIO_MANUTENZIONE
    assert anonimo.get("/api/v1/calendario/qualcosa.ics").status_code == 503
    assert anonimo.post("/_allauth/browser/v1/auth/signup", {}).status_code == 503
    # Still open: the message itself, privacy and terms, the health check, the login.
    sito = anonimo.get("/api/v1/sito").json()
    assert sito["manutenzione"] is True and sito["messaggio_manutenzione"] == MESSAGGIO_MANUTENZIONE
    assert anonimo.get("/api/v1/pagine/privacy").status_code == 200
    assert anonimo.get("/api/v1/salute").status_code == 200
    assert anonimo.get("/_allauth/browser/v1/config").status_code == 200


def test_in_manutenzione_entra_solo_l_amministratore(gruppo, amministratore):
    altro = User.objects.create_user(email="mario@example.invalid", password="una-password")
    EmailAddress.objects.create(user=altro, email=altro.email, verified=True, primary=True)
    _accendi()
    client, risposta = _accedi("mario@example.invalid")
    assert risposta.status_code == 503 and risposta.json()["codice"] == "manutenzione"
    # Logged out at once: the next request is anonymous.
    assert client.get("/_allauth/browser/v1/auth/session").status_code == 401
    client, risposta = _accedi("admin@example.invalid")
    assert risposta.status_code == 200
    assert client.get("/api/v1/io").status_code == 200


def test_in_manutenzione_si_puo_uscire(gruppo, capo):
    _accendi()
    client = _client(capo.utente)
    assert client.delete("/_allauth/browser/v1/auth/session").status_code == 401
    assert client.get("/_allauth/browser/v1/auth/session").status_code == 401


def test_senza_manutenzione_nessun_messaggio(gruppo, capo):
    sito = Client().get("/api/v1/sito").json()
    assert sito["manutenzione"] is False and sito["messaggio_manutenzione"] == ""
    assert _client(capo.utente).get("/api/v1/io").status_code == 200


# --- Login locks ---------------------------------------------------------------------------


def _tentativi(username, ip, n, user_agent="Firefox", fa=timedelta(minutes=5)):
    tentativo = AccessAttempt.objects.create(
        username=username,
        ip_address=ip,
        user_agent=user_agent,
        http_accept="*/*",
        path_info=LOGIN,
        get_data="",
        post_data="",
        failures_since_start=n,
    )
    # attempt_time is auto_now_add: set it afterwards.
    AccessAttempt.objects.filter(pk=tentativo.pk).update(attempt_time=timezone.now() - fa)


def _blocchi(utente):
    return _client(utente).get(f"{URL}/blocchi-accesso")


def test_solo_l_amministratore_vede_e_toglie_i_blocchi(gruppo, tutti, amministratore):
    _tentativi("mario@example.invalid", "203.0.113.7", 5)
    for chi in tutti:
        assert not policy.puo_sbloccare_accessi(chi.utente)
        assert _blocchi(chi.utente).status_code == 403
        sblocca = _client(chi.utente).post(
            f"{URL}/blocchi-accesso/sblocca",
            {"tipo": "account", "valore": "mario@example.invalid"},
            content_type="application/json",
        )
        assert sblocca.status_code == 403
    assert AccessAttempt.objects.count() == 1
    assert _blocchi(amministratore).status_code == 200


def test_i_blocchi_per_account_e_per_indirizzo(gruppo, amministratore):
    # Account: five from the same browser. Address: five from it, over two accounts.
    _tentativi("mario@example.invalid", "203.0.113.7", 5)
    _tentativi("anna@example.invalid", "198.51.100.2", 3)
    _tentativi("lucia@example.invalid", "198.51.100.2", 2)
    # Not locked: four, or older than the cool-off.
    _tentativi("piero@example.invalid", "192.0.2.1", 4)
    _tentativi("vecchio@example.invalid", "192.0.2.9", 9, fa=timedelta(hours=2))
    blocchi = _blocchi(amministratore).json()
    assert [(b["tipo"], b["valore"], b["tentativi"]) for b in blocchi] == [
        ("account", "mario@example.invalid", 5),
        ("indirizzo", "198.51.100.2", 5),
        ("indirizzo", "203.0.113.7", 5),
    ]
    assert all(b["fino_al"] for b in blocchi)


def test_sbloccare_toglie_solo_quel_blocco(gruppo, amministratore):
    _tentativi("mario@example.invalid", "203.0.113.7", 5)
    _tentativi("anna@example.invalid", "198.51.100.2", 5, user_agent="Safari")
    client = _client(amministratore)

    def sblocca(tipo, valore):
        return client.post(
            f"{URL}/blocchi-accesso/sblocca",
            {"tipo": tipo, "valore": valore},
            content_type="application/json",
        )

    rimasti = sblocca("account", "mario@example.invalid").json()
    assert {b["valore"] for b in rimasti} == {"anna@example.invalid", "198.51.100.2"}
    rimasti = sblocca("indirizzo", "198.51.100.2").json()
    assert rimasti == []
    assert sblocca("nessuno", "x").status_code == 400
    assert sblocca("account", " ").status_code == 400


def test_comando_per_lo_script_di_aggiornamento(db):
    """scripts/aggiorna.sh puts the app in maintenance and back (DEC-292)."""
    from io import StringIO

    from django.core.management import call_command

    def comando(*argomenti):
        uscita = StringIO()
        call_command("manutenzione", *argomenti, stdout=uscita)
        return uscita.getvalue().strip()

    assert comando() == "non attiva"
    comando("attiva", "--messaggio", "Aggiornamento in corso.")
    assert comando() == "attiva"
    assert Impostazioni.carica().avviso_manutenzione() == "Aggiornamento in corso."
    comando("disattiva")
    assert comando() == "non attiva"
    # The message stays for the next time.
    assert Impostazioni.carica().messaggio_manutenzione == "Aggiornamento in corso."
