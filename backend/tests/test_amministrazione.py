"""The Django admin for the technical administrators appointed in the app (DEC-166)."""

import pytest
from django.test import Client
from django.utils import timezone

from apps.organizzazione.models import Incarico, RuoloIncarico
from tests.conftest import INIZIO_ANNO, crea_persona

pytestmark = pytest.mark.django_db


def _client(chi) -> Client:
    client = Client()
    client.force_login(chi.utente)
    return client


@pytest.fixture
def amministratore(capo, gruppo):
    """capo (capo unità of the reparto), also appointed technical administrator."""
    Incarico.objects.create(
        persona=capo, ruolo=RuoloIncarico.AMMINISTRATORE, gruppo=gruppo, data_inizio=INIZIO_ANNO
    )
    return capo


def test_l_amministratore_nominato_entra_nell_amministrazione(amministratore):
    assert not amministratore.utente.is_staff  # nothing copied onto the account
    client = _client(amministratore)
    assert client.get("/admin/").status_code == 200
    assert client.get("/admin/organizzazione/unita/").status_code == 200
    assert client.get("/admin/accounts/user/").status_code == 200


def test_chi_non_e_amministratore_resta_fuori(capo, capogruppo, estraneo):
    for chi in (capo, capogruppo, estraneo):
        risposta = _client(chi).get("/admin/")
        assert risposta.status_code == 302 and "/admin/login/" in risposta["Location"]


def test_chiuso_l_incarico_l_accesso_finisce(amministratore):
    Incarico.objects.filter(ruolo=RuoloIncarico.AMMINISTRATORE).update(
        data_fine=timezone.localdate()
    )
    assert _client(amministratore).get("/admin/").status_code == 302


def test_accesso_con_password(amministratore):
    amministratore.utente.set_password("Prova-amministrazione-1")
    amministratore.utente.save()
    risposta = Client().post(
        "/admin/login/?next=/admin/",
        {"username": amministratore.utente.email, "password": "Prova-amministrazione-1"},
    )
    assert risposta.status_code == 302 and risposta["Location"] == "/admin/"


def test_il_primo_amministratore_da_riga_di_comando(db):
    persona = crea_persona("Tecnico", "Primo", "tecnico@example.invalid")
    persona.utente.amministratore_tecnico = True
    persona.utente.save()
    assert _client(persona).get("/admin/").status_code == 200


def test_mai_mentre_si_usa_l_app_al_posto_di_un_altro(amministratore, genitore):
    client = _client(amministratore)
    client.post(
        "/api/v1/impersonazione",
        {"persona_id": genitore.pk, "motivo": "Prova"},
        content_type="application/json",
    )
    assert client.get("/admin/").status_code == 403
