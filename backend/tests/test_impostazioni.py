"""Settings of the installation: names, titles, footer (DEC-245…DEC-248)."""

from datetime import date

import pytest
from django.test import Client

from apps.accounts.models import User
from apps.impostazioni.models import Impostazioni
from apps.organizzazione.models import Incarico, RuoloIncarico
from apps.permessi import policy
from tests.conftest import crea_capo

URL = "/api/v1/impostazioni"


def _client(utente) -> Client:
    client = Client()
    client.force_login(utente)
    return client


def _put(utente, dati):
    return _client(utente).put(f"{URL}/sito", dati, content_type="application/json")


DATI = {
    "nome_sito": "Quaderno di Caccia",
    "sigla_sito": "QdC",
    "nome_gruppo": "AGESCI Prova 1",
    "sigla_gruppo": "PR1",
    "titolo_completo": "[Nome sito] - [Gruppo]",
    "titolo_breve": "[Pagina corrente] · [Sigla sito] - [Sigla gruppo]",
    "riga_piede": "Anno [Anno]",
}


@pytest.fixture
def amministratore(db) -> User:
    return User.objects.create_user(email="admin@example.invalid", amministratore_tecnico=True)


@pytest.fixture
def tesoriere_gruppo(coca, gruppo):
    persona = crea_capo("Teresa", "Tesoriera", "tg@example.invalid")
    Incarico.objects.create(
        persona=persona,
        ruolo=RuoloIncarico.TESORIERE_GRUPPO,
        gruppo=gruppo,
        data_inizio=date(2025, 10, 1),
    )
    return persona


def test_sito_di_base_anche_senza_accesso(gruppo):
    dati = Client().get("/api/v1/sito").json()
    assert dati["nome_sito"] == "Quaderno di Caccia"
    assert dati["sigla_sito"] == "QdC"
    # The title's group name is not the official one, but starts from it.
    assert dati["gruppo"] == "AGESCI Prova 1"
    assert dati["titolo_completo"] == "[Nome sito] - [Gruppo]"
    assert dati["titolo_breve"] == "[Sigla sito] - [Sigla gruppo]"
    assert "/" in dati["anno"]


def test_policy_impostazioni(
    capo, capogruppo, ragazza, csq, genitore, estraneo, amministratore, tesoriere_gruppo
):
    assert policy.puo_modificare_impostazioni(capogruppo.utente)
    assert policy.puo_modificare_impostazioni(amministratore)
    for chi in (capo, ragazza, csq, genitore, estraneo, tesoriere_gruppo):
        assert not policy.puo_modificare_impostazioni(chi.utente)
    # The treasurer opens the page for the payment link alone.
    assert policy.vede_impostazioni(tesoriere_gruppo.utente)
    for chi in (capo, ragazza, csq, genitore, estraneo):
        assert not policy.vede_impostazioni(chi.utente)


def test_chi_cambia_le_impostazioni(
    gruppo, capo, capogruppo, ragazza, csq, genitore, estraneo, amministratore, tesoriere_gruppo
):
    for chi in (capo, ragazza, csq, genitore, estraneo, tesoriere_gruppo):
        assert _put(chi.utente, DATI).status_code == 403
    for chi in (capo, ragazza, csq, genitore, estraneo):
        assert _client(chi.utente).get(URL).status_code == 403
    letto = _client(tesoriere_gruppo.utente).get(URL).json()
    assert letto["puo_modificare"] is False and letto["puo_modificare_pagamenti"] is True

    risposta = _put(capogruppo.utente, DATI)
    assert risposta.status_code == 200
    assert risposta.json()["puo_modificare_intestazione"] is True
    assert Impostazioni.carica().sigla_gruppo == "PR1"
    assert _put(amministratore, {**DATI, "sigla_gruppo": "AV1"}).status_code == 200
    letto = _client(amministratore).get(URL).json()
    # The technical administrator does not touch the prints (capigruppo only).
    assert letto["puo_modificare_intestazione"] is False
    assert Client().get("/api/v1/sito").json()["sigla_gruppo"] == "AV1"


def test_segnaposto_sconosciuto_non_si_salva(gruppo, capogruppo):
    risposta = _put(capogruppo.utente, {**DATI, "titolo_breve": "[Sigla] - [Gruppo]"})
    assert risposta.status_code == 400
    assert "[Sigla]" in risposta.json()["detail"]
    # Case does not matter.
    assert _put(capogruppo.utente, {**DATI, "titolo_breve": "[sigla sito]"}).status_code == 200


def test_nome_del_gruppo_vuoto_torna_quello_di_base(gruppo, capogruppo):
    assert _put(capogruppo.utente, {**DATI, "nome_gruppo": "  "}).status_code == 200
    assert Client().get("/api/v1/sito").json()["gruppo"] == "AGESCI Prova 1"


def test_denominazione_ufficiale_separata(gruppo, capogruppo):
    url = "/api/v1/gruppo/intestazione"
    client = _client(capogruppo.utente)
    risposta = client.put(url, {"denominazione": "Prova Uno"}, content_type="application/json")
    assert risposta.status_code == 200 and risposta.json()["denominazione"] == "Prova Uno"
    vuota = client.put(url, {"denominazione": " "}, content_type="application/json")
    assert vuota.status_code == 400
    # Without the field (older clients) it stays.
    assert client.put(url, {}, content_type="application/json").json()["denominazione"] == (
        "Prova Uno"
    )
