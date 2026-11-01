"""Error pages outside the API in the app's look, with nothing technical (DEC-270)."""

from django.test import Client, RequestFactory
from django.views.defaults import bad_request, permission_denied, server_error

DETTAGLI = ("Traceback", "Django", "DEBUG", "urls.py", "Exception")


def _pulita(html: str) -> None:
    assert "Quaderno di Caccia" in html and "Torna all'app" in html
    for parola in DETTAGLI:
        assert parola not in html


def test_pagina_non_trovata(db):
    risposta = Client().get("/accounts/non-esiste/")
    assert risposta.status_code == 404
    html = risposta.content.decode()
    assert "Pagina non trovata" in html
    # The address asked is not echoed back.
    assert "non-esiste" not in html
    _pulita(html)


def test_pagina_scaduta_per_il_csrf(db):
    risposta = Client(enforce_csrf_checks=True).post("/admin/login/", {"username": "x"})
    assert risposta.status_code == 403
    html = risposta.content.decode()
    assert "La pagina è scaduta" in html
    assert "CSRF" not in html
    _pulita(html)


def test_errore_del_server_senza_dettagli():
    richiesta = RequestFactory().get("/admin/")
    risposta = server_error(richiesta)
    assert risposta.status_code == 500
    html = risposta.content.decode()
    assert "Qualcosa non ha funzionato" in html
    _pulita(html)


def test_richiesta_non_valida_e_accesso_negato():
    richiesta = RequestFactory().get("/admin/")
    assert "Richiesta non valida" in bad_request(richiesta, Exception("x")).content.decode()
    negato = permission_denied(richiesta, Exception("motivo interno")).content.decode()
    assert "Accesso non consentito" in negato and "motivo interno" not in negato
    _pulita(negato)
