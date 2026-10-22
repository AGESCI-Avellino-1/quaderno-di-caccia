import uuid

import pytest
from django.test import Client

from apps.accounts.models import Invito

pytestmark = pytest.mark.django_db


def _invita(client: Client, persona_id: int, chiave: str):
    return client.post(
        "/api/v1/inviti",
        {"persona_id": persona_id, "email": "x@example.invalid"},
        content_type="application/json",
        headers={"Idempotency-Key": chiave},
    )


def test_stessa_chiave_non_ripete_la_scrittura(capo, genitore):
    client = Client()
    client.force_login(capo.utente)
    chiave = str(uuid.uuid4())
    prima = _invita(client, genitore.pk, chiave)
    seconda = _invita(client, genitore.pk, chiave)
    assert prima.status_code == seconda.status_code == 201
    assert seconda["Idempotent-Replayed"] == "true"
    assert seconda.json() == prima.json()
    assert Invito.objects.count() == 1


def test_chiavi_diverse_scrivono_due_volte(capo, genitore):
    client = Client()
    client.force_login(capo.utente)
    _invita(client, genitore.pk, str(uuid.uuid4()))
    _invita(client, genitore.pk, str(uuid.uuid4()))
    assert Invito.objects.count() == 2


def test_chiave_non_uuid_rifiutata(capo, genitore):
    client = Client()
    client.force_login(capo.utente)
    assert _invita(client, genitore.pk, "non-un-uuid").status_code == 400


def test_chiave_riusata_su_altro_percorso(capo, genitore):
    client = Client()
    client.force_login(capo.utente)
    chiave = str(uuid.uuid4())
    _invita(client, genitore.pk, chiave)
    altra = client.post(
        "/api/v1/inviti/accetta",
        {"token": "x"},
        content_type="application/json",
        headers={"Idempotency-Key": chiave},
    )
    assert altra.status_code == 422


def test_errori_non_memorizzati(capo, estraneo):
    """A failed write (403 here) can be retried with the same key."""
    client = Client()
    client.force_login(capo.utente)
    chiave = str(uuid.uuid4())
    assert _invita(client, estraneo.pk, chiave).status_code == 403
    assert "Idempotent-Replayed" not in _invita(client, estraneo.pk, chiave)


def test_invito_non_valido_risponde_400(capo, ragazza):
    """Under-14 invitation without parental consent: a clear 400, not a 500."""
    client = Client()
    client.force_login(capo.utente)
    risposta = _invita(client, ragazza.pk, str(uuid.uuid4()))
    assert risposta.status_code == 400
    assert "consenso" in risposta.json()["detail"]
