import uuid

import pytest
from django.test import Client

from apps.dispositivi.middleware import CODICE_REVOCATO, INTESTAZIONE_SCADENZA
from apps.dispositivi.models import Dispositivo

pytestmark = pytest.mark.django_db


def _client(persona) -> Client:
    client = Client()
    client.force_login(persona.utente)
    return client


def _registra(client: Client, **dati):
    return client.post(
        "/api/v1/dispositivi", {"nome": "Telefono", **dati}, content_type="application/json"
    )


def test_registrazione_lega_il_dispositivo_alla_sessione(capo):
    client = _client(capo)
    risposta = _registra(client)
    assert risposta.status_code == 201
    assert risposta.json()["corrente"] is True
    # Every later response renews the offline window (DEC-97).
    assert INTESTAZIONE_SCADENZA in client.get("/api/v1/io")


def test_senza_dispositivo_nessuna_scadenza(capo):
    assert INTESTAZIONE_SCADENZA not in _client(capo).get("/api/v1/io")


def test_revoca_dal_proprietario_scollega_la_sessione(capo):
    client = _client(capo)
    id_dispositivo = _registra(client).json()["id"]
    assert client.post(f"/api/v1/dispositivi/{id_dispositivo}/revoca").status_code == 200
    # The session was deleted at revocation: the next call is anonymous.
    assert client.get("/api/v1/io").status_code == 401


def test_revoca_da_capogruppo_e_codice_per_il_client(capo, capogruppo):
    telefono = _client(capo)
    id_dispositivo = _registra(telefono).json()["id"]
    # Simulate a session the revocation could not delete (e.g. key rotated meanwhile).
    Dispositivo.objects.filter(pk=id_dispositivo).update(chiave_sessione="")

    cg = _client(capogruppo)
    assert any(d["id"] == id_dispositivo for d in cg.get("/api/v1/dispositivi?tutti=true").json())
    assert cg.post(f"/api/v1/dispositivi/{id_dispositivo}/revoca").status_code == 200

    risposta = telefono.get("/api/v1/io")
    assert risposta.status_code == 401
    assert risposta.json()["codice"] == CODICE_REVOCATO
    assert telefono.get("/api/v1/io").status_code == 401  # logged out for good


def test_altri_non_vedono_ne_revocano(capo, estraneo):
    id_dispositivo = _registra(_client(capo)).json()["id"]
    altro = _client(estraneo)
    assert altro.get("/api/v1/dispositivi?tutti=true").status_code == 403
    assert altro.get("/api/v1/dispositivi").json() == []
    assert altro.post(f"/api/v1/dispositivi/{id_dispositivo}/revoca").status_code == 404


def test_dispositivo_revocato_non_si_riattiva(capo):
    client = _client(capo)
    id_dispositivo = _registra(client).json()["id"]
    Dispositivo.objects.filter(pk=id_dispositivo).update(revocato_il="2026-10-01T00:00Z")
    nuovo = _client(capo)
    assert _registra(nuovo, id=id_dispositivo).status_code == 403
    # A fresh registration after a new login is allowed: it is a new device.
    assert _registra(nuovo).status_code == 201


def test_stesso_dispositivo_dopo_nuovo_accesso(capo):
    id_dispositivo = _registra(_client(capo)).json()["id"]
    di_nuovo = _registra(_client(capo), id=id_dispositivo)
    assert di_nuovo.json()["id"] == id_dispositivo
    assert Dispositivo.objects.count() == 1


def test_id_di_un_altro_utente_ignorato(capo, genitore):
    id_altrui = _registra(_client(capo)).json()["id"]
    mio = _registra(_client(genitore), id=id_altrui).json()["id"]
    assert mio != id_altrui
    assert uuid.UUID(mio)


def test_stato_senza_accesso_dopo_la_revoca(capo):
    """The lost phone has no session any more: it asks with its id alone."""
    client = _client(capo)
    id_dispositivo = _registra(client).json()["id"]
    anonimo = Client()
    assert anonimo.get(f"/api/v1/dispositivi/{id_dispositivo}/stato").json() == {"revocato": False}
    client.post(f"/api/v1/dispositivi/{id_dispositivo}/revoca")
    assert anonimo.get(f"/api/v1/dispositivi/{id_dispositivo}/stato").json() == {"revocato": True}
    assert anonimo.get(f"/api/v1/dispositivi/{uuid.uuid4()}/stato").json() == {"revocato": True}
