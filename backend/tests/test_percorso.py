"""The scout path of a member (DEC-287)."""

from datetime import date

import pytest
from django.test import Client

from apps.anagrafica.models import Appartenenza, PeriodoPercorso, RuoloAppartenenza
from apps.core.anno import AnnoAssociativo
from apps.core.models import FonteDato
from apps.permessi import policy
from tests.conftest import INIZIO_ANNO, crea_capo

pytestmark = pytest.mark.django_db


def _client(chi) -> Client:
    client = Client()
    client.force_login(chi.utente)
    return client


def _post(chi, url, dati):
    return _client(chi).post(url, dati, content_type="application/json")


def test_chi_vede_il_percorso(capo, capogruppo, ragazza, csq, genitore, estraneo):
    url = f"/api/v1/persone/{ragazza.pk}/percorso"
    for chi in (capo, capogruppo, ragazza, genitore):
        assert _client(chi).get(url).status_code == 200, chi
    # Another ragazzo or an unrelated person: not even there.
    for chi in (csq, estraneo):
        assert _client(chi).get(url).status_code == 404
        assert not policy.vede_percorso(chi.utente, ragazza)


def test_chi_lo_completa(capo, capogruppo, ragazza, genitore):
    assert policy.puo_modificare_percorso(capogruppo.utente, ragazza)
    assert policy.puo_modificare_percorso(capo.utente, capo)
    # A capo only for themself; ragazzi and parents never.
    assert not policy.puo_modificare_percorso(capo.utente, ragazza)
    assert not policy.puo_modificare_percorso(ragazza.utente, ragazza)
    assert not policy.puo_modificare_percorso(genitore.utente, ragazza)
    dati = {
        "gruppo": "",
        "unita": "Reparto Orsa",
        "ruolo": "RAGAZZO",
        "anno_inizio": 2020,
        "anno_fine": 2021,
    }
    url = f"/api/v1/persone/{ragazza.pk}/percorso"
    assert _post(genitore, url, dati).status_code == 403
    assert _post(capo, url, dati).status_code == 403


def test_periodi_uniti_e_ricostruiti(capo, capogruppo, reparto, coca):
    # Two contiguous memberships of the reparto from the past: one line.
    anna = crea_capo("Anna", "Percorso", "percorso@example.invalid")
    Appartenenza.objects.create(
        persona=anna,
        unita=reparto,
        ruolo=RuoloAppartenenza.RAGAZZO,
        data_inizio=date(2005, 10, 1),
        data_fine=date(2007, 10, 1),
        fonte=FonteDato.BUONASTRADA,
    )
    Appartenenza.objects.create(
        persona=anna,
        unita=reparto,
        ruolo=RuoloAppartenenza.RAGAZZO,
        data_inizio=date(2007, 10, 1),
        data_fine=date(2009, 10, 1),
        fonte=FonteDato.BUONASTRADA,
    )
    PeriodoPercorso.objects.create(
        persona=anna,
        gruppo="AGESCI Montoro 1",
        unita="Clan/Fuoco (T1)",
        ruolo=RuoloAppartenenza.RAGAZZO,
        anno_inizio=2010,
        anno_fine=2012,
        fonte=FonteDato.BUONASTRADA,
    )
    url = f"/api/v1/persone/{anna.pk}/percorso"
    dati = _client(anna).get(url).json()
    assert dati["anno_ingresso"] == "2005/06"
    righe = [(p["gruppo"], p["unita"], p["anni"]) for p in dati["periodi"]]
    corrente = AnnoAssociativo.da_data(INIZIO_ANNO).etichetta
    assert righe == [
        ("AGESCI Prova 1", str(reparto), "2005/06–2008/09"),
        ("AGESCI Montoro 1", "Clan/Fuoco (T1)", "2009/10–2011/12"),
        ("AGESCI Prova 1", str(coca), f"{corrente}–oggi"),
    ]
    assert dati["puo_modificare"]
    # Rebuilt by hand by the capo: a year before BuonaStrada, in this group.
    nuovo = {
        "unita": "Branco Fiore Rosso",
        "ruolo": "RAGAZZO",
        "anno_inizio": 2002,
        "anno_fine": 2004,
    }
    risposta = _post(anna, url, nuovo)
    assert risposta.status_code == 201
    primo = risposta.json()["periodi"][0]
    assert primo["ricostruito"] and primo["rimovibile"] and not primo["altro_gruppo"]
    assert risposta.json()["anno_ingresso"] == "2001/02"
    # Wrong years refused; only rebuilt periods are removed.
    assert _post(anna, url, nuovo | {"anno_inizio": 2005}).status_code == 400
    importato = PeriodoPercorso.objects.get(fonte=FonteDato.BUONASTRADA)
    assert _client(anna).delete(f"/api/v1/percorso/{importato.pk}").status_code == 400
    assert _client(anna).delete(f"/api/v1/percorso/{primo['id']}").status_code == 200
    assert _client(capo).delete(f"/api/v1/percorso/{importato.pk}").status_code == 403


def test_anni_di_servizio_in_altri_gruppi(capo):
    PeriodoPercorso.objects.create(
        persona=capo,
        gruppo="AGESCI Montoro 1",
        unita="Comunità Capi (G1)",
        ruolo=RuoloAppartenenza.CAPO,
        anno_inizio=2018,
        anno_fine=2019,
        fonte=FonteDato.BUONASTRADA,
    )
    dati = _client(capo).get(f"/api/v1/persone/{capo.pk}/fascicolo-capo").json()
    anni = {a["anno"]: a for a in dati["anni"]}
    assert anni[2019]["altri_gruppi"] == ["Comunità Capi (G1), AGESCI Montoro 1"]
    assert anni[2018]["gruppo"] == ""
    assert anni[AnnoAssociativo.da_data(INIZIO_ANNO).anno_fine]["gruppo"] == "AGESCI Prova 1"
    # A rebuilt year in another group says it.
    url = f"/api/v1/persone/{capo.pk}/fascicolo-capo/servizi"
    risposta = _post(
        capo,
        url,
        {
            "anno": 2015,
            "unita_testo": "Reparto Orsa",
            "ruolo": "STAFF",
            "gruppo": "AGESCI Salerno 3",
        },
    )
    anni = {a["anno"]: a for a in risposta.json()["anni"]}
    assert anni[2015]["ricostruiti"][0]["testo"] == "Staff di unità, Reparto Orsa, AGESCI Salerno 3"
    assert dati["anni_di_servizio"] >= 3
