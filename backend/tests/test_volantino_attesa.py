"""«Invita nel gruppo» (DEC-304): the waiting list flyer and its text."""

import pytest
from django.test import Client

from apps.attesa import volantino
from apps.impostazioni.models import Impostazioni
from apps.permessi import policy

pytestmark = pytest.mark.django_db

URL = "/api/v1/volantino-lista-attesa.pdf"
TESTO = "/api/v1/impostazioni/volantino-attesa"


def _client(chi) -> Client:
    client = Client()
    client.force_login(chi.utente)
    return client


def _put(chi, dati):
    return _client(chi).put(TESTO, dati, content_type="application/json")


def test_chi_scarica_il_volantino(capo, capogruppo, csq, ragazza, genitore, estraneo):
    for chi in (capo, capogruppo, csq, ragazza, genitore, estraneo):
        assert policy.puo_condividere_lista_attesa(chi.utente)
        risposta = _client(chi).get(URL)
        assert risposta.status_code == 200
        assert risposta["Content-Type"] == "application/pdf"
        assert risposta["Cache-Control"] == "no-store"
        assert risposta.content.startswith(b"%PDF")
    assert Client().get(URL).status_code == 401


def test_chi_cambia_il_testo(capo, capogruppo, csq, ragazza, genitore, estraneo):
    assert policy.puo_modificare_volantino_attesa(capogruppo.utente)
    for chi in (capo, csq, ragazza, genitore, estraneo):
        assert not policy.puo_modificare_volantino_attesa(chi.utente)
    assert _put(capo, {"testo": "Altro"}).status_code == 403
    assert Client().put(TESTO, {"testo": "x"}, content_type="application/json").status_code in (
        401,
        403,
    )


def test_testo_del_volantino(capogruppo):
    risposta = _put(
        capogruppo, {"testo": "  Vieni  con noi  in [Gruppo]! \r\n\r\nCiao [sigla gruppo]"}
    )
    assert risposta.status_code == 200
    dati = risposta.json()
    assert dati["volantino_attesa"] == "Vieni con noi in [Gruppo]!\n\nCiao [sigla gruppo]"
    assert dati["volantino_attesa_base"] == volantino.TESTO_BASE
    assert dati["puo_modificare_volantino"]
    imp = Impostazioni.carica()
    imp.sigla_gruppo = "AV1"
    imp.save()
    compilato = volantino.compila(volantino.testo(imp), imp)
    assert compilato == f"Vieni con noi in {imp.nome_del_gruppo()}!\n\nCiao AV1"
    # Unknown placeholders and long texts are refused.
    errore = _put(capogruppo, {"testo": "Da [Nome] in poi"})
    assert errore.status_code == 400 and "[Nome]" in errore.json()["detail"]
    assert _put(capogruppo, {"testo": "x" * 1001}).status_code == 400
    # The base text, or nothing: back to the base, which follows future versions.
    _put(capogruppo, {"testo": volantino.TESTO_BASE})
    assert Impostazioni.carica().volantino_attesa == ""
    _put(capogruppo, {"testo": ""})
    assert volantino.testo(Impostazioni.carica()) == volantino.TESTO_BASE


def test_volantino_col_link_della_lista(settings, capo):
    settings.FRONTEND_URL = "https://qdc.example.org"
    assert volantino.indirizzo() == "https://qdc.example.org/lista-attesa"
    assert _client(capo).get(URL).content.startswith(b"%PDF")
