"""Addresses proposed while a place is written: who may ask, what comes back from the service
(answers shaped as the real ones), and that a failure only means no proposals."""

import pytest
import requests
from django.core.cache import cache
from django.test import Client, override_settings

from apps.eventi import indirizzi

pytestmark = pytest.mark.django_db

VIA = {"type": "street", "name": "Piazza della Libertà", "city": "Avellino", "postcode": "83100"}
CIVICO = {"type": "house", "housenumber": "1", "street": "Via Roma", "city": "Teora"}
SCUOLA = {"name": "Scuola Dante", "street": "Via Verdi", "postcode": "83100", "city": "Avellino"}


class _Risposta:
    def __init__(self, dati, stato=200):
        self.dati, self.stato = dati, stato

    def raise_for_status(self):
        if self.stato >= 400:
            raise requests.HTTPError(str(self.stato))

    def json(self):
        return self.dati


@pytest.fixture(autouse=True)
def senza_cache():
    cache.clear()


@pytest.fixture
def servizio(monkeypatch):
    chiamate = []

    def imposta(*proprieta, stato=200):
        def falso_get(url, **opzioni):
            chiamate.append((url, opzioni))
            elementi = [{"properties": p} for p in proprieta]
            return _Risposta({"features": elementi}, stato)

        monkeypatch.setattr(indirizzi.requests, "get", falso_get)
        return chiamate

    return imposta


def _cerca(chi, testo="via roma"):
    client = Client()
    client.force_login(chi.utente)
    return client.get("/api/v1/localita/cerca", {"testo": testo})


def test_chi_cerca(servizio, capo, capogruppo, csq, ragazza, genitore, estraneo):
    servizio(VIA)
    assert _cerca(capo).status_code == 200
    assert _cerca(capogruppo).status_code == 200
    assert _cerca(csq).status_code == 200
    for persona in (ragazza, genitore, estraneo):
        assert _cerca(persona).status_code == 403
    assert Client().get("/api/v1/localita/cerca", {"testo": "via roma"}).status_code == 401


def test_le_proposte(servizio, capo):
    chiamate = servizio(VIA, CIVICO, SCUOLA, {"name": "Solo un nome", "street": ""}, {})
    assert _cerca(capo, "  via   roma ").json() == [
        {"nome": "", "indirizzo": "Piazza della Libertà, 83100 Avellino"},
        {"nome": "", "indirizzo": "Via Roma 1, Teora"},
        {"nome": "Scuola Dante", "indirizzo": "Via Verdi, 83100 Avellino"},
        {"nome": "", "indirizzo": "Solo un nome"},
    ]
    url, opzioni = chiamate[0]
    assert url == "https://photon.komoot.io/api/"
    assert opzioni["params"]["q"] == "via roma"
    # The service refuses any language but its own few, Italian included.
    assert "lang" not in opzioni["params"]
    assert opzioni["timeout"] == indirizzi.ATTESA_SECONDI


def test_una_via_a_pezzi_torna_una_volta(servizio, capo):
    servizio(VIA, VIA)
    assert len(_cerca(capo).json()) == 1


def test_stessa_ricerca_una_sola_chiamata(servizio, capo):
    chiamate = servizio(VIA)
    _cerca(capo, "via roma")
    _cerca(capo, "VIA  ROMA")
    assert len(chiamate) == 1


def test_troppo_corto_non_chiede(servizio, capo):
    chiamate = servizio(VIA)
    assert _cerca(capo, "vi").json() == []
    assert not chiamate


@pytest.mark.parametrize("stato", [400, 429, 500])
def test_il_servizio_rifiuta_nessuna_proposta(servizio, capo, stato):
    servizio(VIA, stato=stato)
    risposta = _cerca(capo)
    assert risposta.status_code == 200 and risposta.json() == []


def test_il_servizio_non_risponde_e_non_si_scrive_cosa_si_cercava(monkeypatch, capo, caplog):
    chiamate = []

    def falso_get(*_, **__):
        chiamate.append(1)
        raise requests.Timeout("via segreta 12")

    monkeypatch.setattr(indirizzi.requests, "get", falso_get)
    risposta = _cerca(capo, "via segreta 12")
    assert risposta.status_code == 200 and risposta.json() == []
    assert "segreta" not in caplog.text
    # Not remembered: the next one tries again.
    _cerca(capo, "via segreta 12")
    assert len(chiamate) == 2


def test_risposta_non_valida_nessuna_proposta(monkeypatch, capo):
    monkeypatch.setattr(indirizzi.requests, "get", lambda *_, **__: _Risposta(["strano"]))
    assert _cerca(capo).json() == []


@override_settings(QDC_PHOTON_URL="")
def test_senza_servizio_non_chiede(servizio, capo):
    chiamate = servizio(VIA)
    assert _cerca(capo).json() == []
    assert not chiamate


@override_settings(QDC_PHOTON_URL="https://photon.esempio.invalid/")
def test_il_servizio_si_puo_cambiare(servizio, capo):
    chiamate = servizio(VIA)
    _cerca(capo)
    assert chiamate[0][0] == "https://photon.esempio.invalid/api/"
