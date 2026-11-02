"""The group's medical form (DEC-289) and what goes offline at camp (DEC-291)."""

from datetime import date, timedelta

import pytest
from django.test import Client

from apps.sanitaria.api import _essenziali
from apps.sanitaria.models import Allergia, InformazioniSanitarie, TipoAllergia

pytestmark = pytest.mark.django_db


def _client(chi) -> Client:
    client = Client()
    client.force_login(chi.utente)
    return client


def _put(chi, url, dati):
    return _client(chi).put(url, dati, content_type="application/json")


def _url(persona) -> str:
    return f"/api/v1/persone/{persona.pk}/sanitarie"


SCHEDA = {
    "patologie": True,
    "patologie_dettaglio": "Asma da sforzo",
    "interventi": False,
    "disturbi_sonno": False,
    "occhiali": True,
    "occhiali_dettaglio": "Occhiali da vista",
    "allergie_farmaci": False,
    "allergie_alimentari": True,
    "intolleranze_alimentari": False,
    "allergie_insetti": True,
    "allergie_ambientali": False,
    "allergie": [
        {"tipo": "ALIMENTARE", "sostanza": "Arachidi", "gravita": "GRAVE"},
        {"tipo": "INSETTI", "sostanza": "Vespa", "gravita": "MODERATA"},
    ],
    "farmaco_salvavita": True,
    "farmaci_da_banco": False,
    "antitetanica_data": "2022-05-10",
    "medico_curante": "Dott.ssa Bianchi",
    "medico_telefono": "0825 000000",
}


def test_scheda_del_gruppo(genitore, ragazza):
    risposta = _put(genitore, _url(ragazza), SCHEDA)
    assert risposta.status_code == 200, risposta.content
    dati = risposta.json()
    assert dati["patologie"] and dati["patologie_dettaglio"] == "Asma da sforzo"
    assert dati["antitetanica"] is True and dati["antitetanica_data"] == "2022-05-10"
    assert not dati["nessuna_allergia"]
    assert {a["tipo"] for a in dati["allergie"]} == {"ALIMENTARE", "INSETTI"}
    # What the capi take offline at camp (DEC-291).
    info = InformazioniSanitarie.objects.get(persona=ragazza)
    essenziali = _essenziali(info)
    assert essenziali["farmaco_salvavita"] is True and essenziali["farmaci_da_banco"] is False
    assert "patologie" not in essenziali and "medico_telefono" not in essenziali


def test_risposte_coerenti(genitore, ragazza):
    url = _url(ragazza)
    # "No" to a kind with items of it.
    assert _put(genitore, url, SCHEDA | {"allergie_insetti": False}).status_code == 400
    # "Yes" without saying what.
    assert _put(genitore, url, SCHEDA | {"interventi": True}).status_code == 400
    domani = (date.today() + timedelta(days=1)).isoformat()
    assert _put(genitore, url, SCHEDA | {"antitetanica_data": domani}).status_code == 400
    # All five "no": no allergy at all.
    tutti_no = {c: False for c in ("allergie_alimentari", "allergie_insetti")}
    risposta = _put(genitore, url, SCHEDA | tutti_no | {"allergie": []})
    assert risposta.json()["nessuna_allergia"] is True


def test_richiesta_di_una_app_vecchia(genitore, ragazza):
    """Queued offline before the group's form: "ALLERGIA" and "nessuna allergia" only."""
    vecchia = {
        "nessuna_allergia": False,
        "allergie": [{"tipo": "ALLERGIA", "sostanza": "Polline", "gravita": "LIEVE"}],
    }
    assert _put(genitore, _url(ragazza), vecchia).status_code == 200
    assert Allergia.objects.get().tipo == TipoAllergia.ALIMENTARE
    risposta = _put(genitore, _url(ragazza), {"nessuna_allergia": True})
    info = InformazioniSanitarie.objects.get(persona=ragazza)
    assert risposta.json()["nessuna_allergia"] and info.allergie_insetti is False


def test_telefono_fisso_dei_genitori(genitore, ragazza, capo, estraneo):
    dati = _client(capo).get(_url(ragazza)).json()
    assert [g["id"] for g in dati["genitori"]] == [genitore.pk]
    url = f"/api/v1/persone/{genitore.pk}/telefono-fisso"
    risposta = _put(genitore, url, {"telefono": "0825 111111"})
    assert risposta.status_code == 200
    genitore.refresh_from_db()
    assert genitore.telefono_fisso == "0825 111111"
    # Who writes the child's form (the capo of the unit) too; nobody else.
    assert _put(capo, url, {"telefono": "0825 222222"}).status_code == 200
    assert _put(estraneo, url, {"telefono": "1"}).status_code == 404
    assert _client(capo).get(_url(ragazza)).json()["genitori"][0]["telefono_fisso"] == (
        "0825 222222"
    )
