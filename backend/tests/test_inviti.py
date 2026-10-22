import pytest
from django.core import mail
from django.core.management import CommandError, call_command
from django.test import Client

from apps.accounts.models import Invito
from apps.organizzazione.models import Incarico, RuoloIncarico
from apps.permessi import policy

pytestmark = pytest.mark.django_db


def test_invito_dall_app_parte_per_email(capo, genitore):
    client = Client()
    client.force_login(capo.utente)
    risposta = client.post(
        "/api/v1/inviti",
        {"persona_id": genitore.pk, "email": "mamma@example.invalid"},
        content_type="application/json",
    )
    assert risposta.status_code == 201
    [messaggio] = mail.outbox
    assert messaggio.to == ["mamma@example.invalid"]
    assert f"/invito/{risposta.json()['token']}" in messaggio.body
    assert genitore.nome in messaggio.body


def test_bootstrap_primo_capogruppo(capo):
    """Fresh install: a capo from the import becomes capogruppo and gets an invite."""
    capo.codice_socio = "1234567"
    capo.save()
    utente = capo.utente
    assert not policy.e_capogruppo(utente)

    call_command("crea_invito", "1234567", "cg@example.invalid", "--capogruppo")

    assert Incarico.objects.attivi().filter(persona=capo, ruolo=RuoloIncarico.CAPOGRUPPO).exists()
    assert policy.e_capogruppo(utente)
    assert Invito.objects.get(email="cg@example.invalid").persona == capo
    assert len(mail.outbox) == 1


def test_bootstrap_codice_sconosciuto(db):
    with pytest.raises(CommandError, match="importa prima"):
        call_command("crea_invito", "0000000", "x@example.invalid")
