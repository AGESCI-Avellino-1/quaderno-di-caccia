"""The capi's file (DEC-47, DEC-134, DEC-206…DEC-208), for every role."""

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest
from django.test import Client

from apps.anagrafica.models import Appartenenza, RuoloAppartenenza
from apps.core.anno import AnnoAssociativo
from apps.fascicolo.models import Formazione, ServizioPassato
from tests.conftest import crea_capo

pytestmark = pytest.mark.django_db

OGGI = date.today()


def _client(chi) -> Client:
    client = Client()
    client.force_login(chi.utente)
    return client


def _post(chi, url, dati):
    return _client(chi).post(url, dati, content_type="application/json")


def test_chi_vede_e_chi_scrive(capo, capogruppo, csq, ragazza, genitore, estraneo):
    url = f"/api/v1/persone/{capo.pk}/fascicolo-capo"
    altro = crea_capo("Carlo", "Altro", "altro@example.invalid")
    for chi in (capo, capogruppo, altro):
        assert _client(chi).get(url).status_code == 200
    for chi in (csq, ragazza, genitore, estraneo):
        assert _client(chi).get(url).status_code == 404
    # Not for a ragazzo.
    assert (
        _client(capogruppo).get(f"/api/v1/persone/{ragazza.pk}/fascicolo-capo").status_code == 404
    )
    formazione = {"tipo": "CFM", "data": "2019-07-01", "luogo": "Bracigliano"}
    assert _post(altro, f"{url}/formazione", formazione).status_code == 403
    assert _post(capo, f"{url}/formazione", formazione).status_code == 201
    assert (
        _post(capogruppo, f"{url}/formazione", {**formazione, "tipo": "MODULO"}).status_code == 400
    )
    dati = _post(
        capogruppo,
        f"{url}/formazione",
        {**formazione, "tipo": "MODULO", "specifica": "Comunicazione"},
    ).json()
    assert [f["tipo"] for f in dati["formazione"]] == ["CFM", "MODULO"] or len(
        dati["formazione"]
    ) == 2
    assert _client(capo).get(f"/api/v1/persone/{capo.pk}").json()["fascicolo_capo"] is True


def test_anni_di_servizio_dall_app_e_ricostruiti(capo, capogruppo, reparto):
    corrente = AnnoAssociativo.corrente()
    dati = _client(capo).get(f"/api/v1/persone/{capo.pk}/fascicolo-capo").json()
    anno = next(a for a in dati["anni"] if a["anno"] == corrente.anno_fine)
    assert any("Capo unità" in r for r in anno["ruoli"]) and anno["in_coca"]
    url = f"/api/v1/persone/{capo.pk}/fascicolo-capo/servizi"
    assert _post(capo, url, {"anno": 2015, "ruolo": "STAFF"}).status_code == 400  # which unit?
    assert (
        _post(capo, url, {"anno": 2015, "ruolo": "ALTRO", "unita_testo": "Reparto"}).status_code
        == 400
    )
    dati = _post(capo, url, {"anno": 2015, "ruolo": "STAFF", "unita_testo": "Reparto Orsa"}).json()
    vecchio = next(a for a in dati["anni"] if a["anno"] == 2015)
    assert vecchio["ricostruiti"][0]["testo"] == "Staff di unità, Reparto Orsa"
    assert dati["anni_di_servizio"] >= 2
    servizio = vecchio["ricostruiti"][0]["id"]
    assert _client(capogruppo).delete(f"/api/v1/servizi-passati/{servizio}").status_code == 200
    assert not ServizioPassato.objects.exists()


def test_i_campi_buonacaccia_compaiono_da_soli(capo, capogruppo):
    from apps.buonacaccia import servizi as bc
    from apps.buonacaccia.models import EventoBuonaCaccia
    from apps.eventi.models import Evento, Partecipazione, TipoEvento

    roma = ZoneInfo("Europe/Rome")
    evento = Evento(
        titolo="CFA Campania",
        tipo=TipoEvento.CAMPO,
        inizio=datetime.combine(OGGI - timedelta(days=60), time(9), roma),
        fine=datetime.combine(OGGI - timedelta(days=55), time(17), roma),
        luogo="Salerno",
    )
    bc.salva_evento(
        evento, EventoBuonaCaccia(formazione_capi=True, tipo_campo="CFA"), capogruppo.utente
    )
    Partecipazione.objects.update_or_create(evento=evento, persona=capo)
    voci = _client(capo).get(f"/api/v1/persone/{capo.pk}/fascicolo-capo").json()["formazione"]
    assert voci[0]["da_buonacaccia"] is True and voci[0]["tipo"] == "CFA"


def test_cancellazione(capo, capogruppo):
    Appartenenza.objects.filter(persona=capo, ruolo=RuoloAppartenenza.CAPO).update(
        data_fine=OGGI - timedelta(days=1)
    )
    Formazione.objects.create(persona=capo, tipo="CFT", data=date(2018, 5, 1))
    ServizioPassato.objects.create(persona=capo, anno=2016, ruolo="STAFF", unita_testo="Branco")
    dati = _client(capogruppo).get(f"/api/v1/persone/{capo.pk}/fascicolo").json()
    assert dati["formazione_capi"] and dati["servizio_ricostruito"]
    risposta = _client(capogruppo).post(
        f"/api/v1/persone/{capo.pk}/cancellazione", {"cognome": capo.cognome}, "application/json"
    )
    assert risposta.status_code == 200, risposta.content
    assert not (Formazione.objects.exists() or ServizioPassato.objects.exists())
