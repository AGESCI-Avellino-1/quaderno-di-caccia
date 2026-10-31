"""Proposing a codice fiscale from the personal data."""

from datetime import date

import pytest
from django.test import Client

from apps.core.codice_fiscale import calcola, carattere_di_controllo, cerca_comuni


@pytest.fixture(autouse=True)
def _senza_limiti():
    from django.core.cache import cache

    cache.clear()


def test_calcolo_con_le_regole_standard():
    assert calcola("Mario", "Rossi", "M", date(1980, 1, 1), "H501") == "RSSMRA80A01H501U"
    # Women: day + 40; four consonants in the name: first, third, fourth.
    assert calcola("Francesca", "Gallo", "F", date(1988, 10, 5), "A509")[:11] == "GLLFNC88R45"
    assert carattere_di_controllo("RSSMRA80A01H501") == "U"


def test_comuni_dal_catalogo_istat():
    assert [c["codice"] for c in cerca_comuni("avellino")] == ["A509"]
    assert cerca_comuni("Sant'Angelo dei Lombardi")[0]["codice"] == "I281"
    assert len(cerca_comuni("Castro")) == 2
    assert [c["provincia"] for c in cerca_comuni("Castro (LE)")] == ["LE"]


def test_api_pubblica(db):
    url = "/api/v1/codice-fiscale"
    dati = {
        "nome": "Mario",
        "cognome": "Rossi",
        "sesso": "M",
        "data_nascita": "1980-01-01",
        "luogo_nascita": "Roma",
    }
    risposta = Client().post(url, dati, content_type="application/json").json()
    assert risposta == {"codice_fiscale": "RSSMRA80A01H501U", "comune": "Roma (RM)"}
    ambiguo = Client().post(
        url, {**dati, "luogo_nascita": "Castro"}, content_type="application/json"
    )
    assert ambiguo.status_code == 400 and "Castro (LE)" in ambiguo.json()["detail"]
    estero = Client().post(
        url, {**dati, "luogo_nascita": "Parigi"}, content_type="application/json"
    )
    assert "a mano" in estero.json()["detail"]
    assert "Avellino (AV)" in Client().get("/api/v1/comuni?cerca=avel").json()
