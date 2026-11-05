"""Meetings, apart from the events (DEC-310)."""

from datetime import date, datetime, timedelta

import pytest
from django.core import mail
from django.test import Client
from django.utils import timezone

from apps.anagrafica.models import Appartenenza, RuoloAppartenenza
from apps.eventi.models import Evento, Localita, RiunioneRicorrente
from apps.impostazioni.models import Impostazioni
from apps.organizzazione.models import Composizione, Incarico, RuoloIncarico, TipoUnita, Unita
from tests.conftest import INIZIO_ANNO, crea_persona, nato_anni_fa

pytestmark = pytest.mark.django_db


def _client(chi) -> Client:
    client = Client()
    client.force_login(chi.utente)
    return client


def _post(chi, url, dati=None):
    return _client(chi).post(url, dati or {}, content_type="application/json")


def _put(chi, url, dati):
    return _client(chi).put(url, dati, content_type="application/json")


def _sabato(settimane: int = 1) -> date:
    oggi = timezone.localdate()
    return oggi + timedelta(days=(5 - oggi.weekday()) % 7 + 7 * settimane)


def _serie(unita, **altro):
    return {
        "unita": [unita.pk],
        "giorno_settimana": 5,
        "ora_inizio": "16:30",
        "ora_fine": "18:30",
        "dal": _sabato(1).isoformat(),
        "al": _sabato(4).isoformat(),
        **altro,
    }


@pytest.fixture(autouse=True)
def email_accese():
    imp = Impostazioni.carica()
    imp.email_capi = imp.email_genitori = imp.email_ragazzi = True
    imp.save()


def test_serie_dello_staff_con_localita_nuova(capo, csq, reparto, ragazza):
    url = "/api/v1/riunioni"
    corpo = _serie(reparto, nuova_localita={"nome": "Sede", "indirizzo": "Via dei Pini 1"})
    assert _post(csq, url, corpo).status_code == 403
    risposta = _post(capo, url, corpo)
    assert risposta.status_code == 201, risposta.content
    riunioni = risposta.json()
    assert len(riunioni) == 4
    assert {r["luogo"] for r in riunioni} == {"Sede"} and all(r["uniforme"] for r in riunioni)
    assert all(r["serie_id"] for r in riunioni)
    # The place entered the group's list; the same name again is the same place.
    assert list(Localita.objects.values_list("nome", flat=True)) == ["Sede"]
    _post(capo, url, _serie(reparto, nuova_localita={"nome": "sede"}))
    assert Localita.objects.count() == 1
    assert mail.outbox == []  # a series is not announced


def test_le_riunioni_non_sono_eventi(capo, reparto, ragazza, genitore):
    prima, *_ = _post(capo, "/api/v1/riunioni", _serie(reparto)).json()
    assert _client(genitore).get("/api/v1/eventi").json() == []
    assert [r["id"] for r in _client(genitore).get("/api/v1/eventi?riunioni=true").json()][0] == (
        prima["id"]
    )
    quota = {"rate": [{"descrizione": "", "importo": "5", "scadenza": "2026-12-01"}]}
    assert _put(capo, f"/api/v1/eventi/{prima['id']}/quota", quota).status_code == 400
    evento = {
        "titolo": "Riunione",
        "tipo": "RIUNIONE",
        "livello": "UNITA",
        "unita": [reparto.pk],
        "inizio": "2026-12-05T16:00:00",
        "fine": "2026-12-05T18:00:00",
    }
    assert _post(capo, "/api/v1/eventi", evento).status_code == 400


def test_una_riunione_cambia_e_lo_dice(
    capo, reparto, ragazza, genitore, django_capture_on_commit_callbacks
):
    prima, seconda, *_ = _post(capo, "/api/v1/riunioni", _serie(reparto)).json()
    url = f"/api/v1/riunioni/{prima['id']}"
    corpo = {"inizio": prima["inizio"], "fine": prima["fine"], "uniforme": False}
    note = "<p>Porta la <strong>borraccia</strong></p><script>x()</script>"
    assert _put(genitore, url, {**corpo, "informazioni": note}).status_code == 403
    with django_capture_on_commit_callbacks(execute=True):
        cambiata = _put(capo, url, {**corpo, "informazioni": note}).json()
    assert cambiata["uniforme"] is False
    assert "<script>" not in cambiata["informazioni"] and "borraccia" in cambiata["informazioni"]
    assert mail.outbox == []  # notes and uniform: no email
    # Moved: the family is told.
    fine = datetime.fromisoformat(seconda["fine"]) + timedelta(minutes=30)
    spostata = {**corpo, "inizio": seconda["inizio"], "fine": fine.isoformat()}
    with django_capture_on_commit_callbacks(execute=True):
        _put(capo, f"/api/v1/riunioni/{seconda['id']}", spostata)
    assert [m.subject for m in mail.outbox] == [f"Spostata: {seconda['titolo']}"]
    assert mail.outbox[0].to == ["genitore@example.invalid"]
    mail.outbox.clear()
    with django_capture_on_commit_callbacks(execute=True):
        _post(capo, f"/api/v1/eventi/{prima['id']}/annulla", {"motivo": "Pioggia"})
    assert mail.outbox[0].subject == f"Annullata: {prima['titolo']}"
    # The family sees the notes.
    dettaglio = _client(genitore).get(f"/api/v1/eventi/{prima['id']}").json()
    assert "borraccia" in dettaglio["informazioni"]


def test_la_serie_cambia_uniforme_e_luogo(capo, reparto):
    riunioni = _post(capo, "/api/v1/riunioni", _serie(reparto)).json()
    serie = RiunioneRicorrente.objects.get()
    propria = Evento.objects.get(pk=riunioni[0]["id"])
    propria.uniforme = True
    propria.save()
    risposta = _put(
        capo,
        f"/api/v1/riunioni/serie/{serie.pk}",
        {"uniforme": False, "nuova_localita": {"nome": "Base Monte"}},
    )
    assert risposta.status_code == 200, risposta.content
    tutte = {r["id"]: r for r in _client(capo).get("/api/v1/eventi?riunioni=true").json()}
    assert tutte[propria.pk]["uniforme"] is True  # its own choice stays
    assert {r["uniforme"] for i, r in tutte.items() if i != propria.pk} == {False}
    assert {r["luogo"] for r in tutte.values()} == {"Base Monte"}
    # Taken away: the meetings to come are cancelled.
    assert _client(capo).delete(f"/api/v1/riunioni/serie/{serie.pk}").json()["riunioni"] == 0


def test_riunioni_di_squadriglia_del_csq_e_del_delegato(csq, ragazza, squadriglia, capo, estraneo):
    corpo = {**_serie(squadriglia.unita), "unita": [], "squadriglia_id": squadriglia.pk}
    risposta = _post(csq, "/api/v1/riunioni", corpo)
    assert risposta.status_code == 201, risposta.content
    assert {r["squadriglia"] for r in risposta.json()} == {squadriglia.nome}
    assert _post(estraneo, "/api/v1/riunioni", corpo).status_code == 403
    _put(csq, f"/api/v1/squadriglie/{squadriglia.pk}/delega", {"persona_id": ragazza.pk})
    singola = {**corpo, "giorno": _sabato(6).isoformat()}
    assert _post(ragazza, "/api/v1/riunioni", singola).status_code == 201
    assert [s["squadriglia"] for s in _client(csq).get("/api/v1/riunioni/serie").json()] == [
        squadriglia.nome
    ]


def test_consiglio_degli_anziani(gruppo, coca, capogruppo):
    branco = Unita.objects.create(
        gruppo=gruppo, nome="Branco", tipo=TipoUnita.BRANCO, composizione=Composizione.MISTA
    )
    lupo = crea_persona("Lino", "Lupo", data_nascita=nato_anni_fa(10))
    Appartenenza.objects.create(
        persona=lupo, unita=branco, ruolo=RuoloAppartenenza.RAGAZZO, data_inizio=INIZIO_ANNO
    )
    cucciolo = crea_persona("Cico", "Lupo", data_nascita=nato_anni_fa(8))
    Appartenenza.objects.create(
        persona=cucciolo, unita=branco, ruolo=RuoloAppartenenza.RAGAZZO, data_inizio=INIZIO_ANNO
    )
    Incarico.objects.create(
        persona=lupo, ruolo=RuoloIncarico.CONSIGLIO_ANZIANI, unita=branco, data_inizio=INIZIO_ANNO
    )
    singola = {**_serie(branco), "cerchia": "CDA", "giorno": _sabato(2).isoformat()}
    (cda,) = _post(capogruppo, "/api/v1/riunioni", singola).json()
    assert cda["titolo"] == "Consiglio degli Anziani"
    evento = Evento.objects.get(pk=cda["id"])
    assert list(evento.partecipazioni.values_list("persona_id", flat=True)) == [lupo.pk]
    reparto = Unita.objects.create(gruppo=gruppo, nome="R", tipo=TipoUnita.REPARTO)
    sbagliata = {**singola, "unita": [reparto.pk]}
    assert (
        "branco o di un cerchio"
        in _post(capogruppo, "/api/v1/riunioni", sbagliata).json()["detail"]
    )


def test_insieme_solo_con_l_unita_collegata(gruppo, capogruppo, reparto):
    altro = Unita.objects.create(gruppo=gruppo, nome="Altro", tipo=TipoUnita.REPARTO)
    corpo = {**_serie(reparto), "unita": [reparto.pk, altro.pk], "cerchia": "CONCA"}
    assert _post(capogruppo, "/api/v1/riunioni", corpo).status_code == 400
    reparto.collegata_a = altro
    reparto.save()
    altro.collegata_a = reparto
    altro.save()
    riunioni = _post(capogruppo, "/api/v1/riunioni", corpo).json()
    assert len(riunioni[0]["unita"]) == 2


def test_localita_indirizzo_completo():
    assert Localita(indirizzo="Via Roma, 83100 Avellino", civico="1").indirizzo_completo == (
        "Via Roma 1, 83100 Avellino"
    )
    assert Localita(indirizzo="Via Roma", civico="1").indirizzo_completo == "Via Roma 1"
    assert Localita(indirizzo="Via Roma 1, Teora").indirizzo_completo == "Via Roma 1, Teora"
    assert Localita(indirizzo="", civico="1").indirizzo_completo == ""


def test_localita_con_nome_completo_e_civico(capogruppo, capo, reparto):
    risposta = _post(
        capo,
        "/api/v1/riunioni",
        _serie(
            reparto,
            nuova_localita={
                "nome": "Sede",
                "denominazione": "Parrocchia di San Rocco",
                "indirizzo": "Via Roma, 83100 Avellino",
                "civico": "1",
            },
        ),
    )
    assert risposta.status_code == 201, risposta.content
    # Who is invited reads its own name: the page, the emails and the calendar use this copy.
    assert risposta.json()[0]["luogo"] == "Parrocchia di San Rocco"
    localita = risposta.json()[0]["localita"]
    assert localita["nome"] == "Sede"
    assert localita["indirizzo_completo"] == "Via Roma 1, 83100 Avellino"
    # The list goes on calling it by its short name.
    assert [(s["nome"]) for s in _client(capo).get("/api/v1/localita").json()] == ["Sede"]
    url = f"/api/v1/localita/{localita['id']}"
    corpo = {"nome": "Sede", "denominazione": "Oratorio", "indirizzo": "Via Roma", "civico": "2"}
    assert _put(capogruppo, url, corpo).json()["indirizzo_completo"] == "Via Roma 2"
    prossima = Evento.objects.filter(localita_id=localita["id"]).first()
    assert prossima.luogo == "Oratorio"
    corpo["denominazione"] = ""
    _put(capogruppo, url, corpo)
    prossima.refresh_from_db()
    assert prossima.luogo == "Sede"


def test_nome_completo_nel_presso_dell_assemblea(capogruppo):
    from apps.verbali import modelli, servizi

    giorno = timezone.localdate() + timedelta(days=10)
    risposta = _post(
        capogruppo,
        "/api/v1/riunioni",
        {
            "cerchia": "SOCI",
            "giorno": giorno.isoformat(),
            "ora_inizio": "18:00",
            "ora_fine": "20:00",
            "nuova_localita": {"nome": "Sede", "denominazione": "Parrocchia di San Rocco"},
        },
    )
    assert risposta.status_code == 201, risposta.content
    evento = Evento.objects.get(pk=risposta.json()[0]["id"])
    dati = modelli.dati_convocazione(servizi.verbale_di(evento))
    assert dati["luogo"]["presso"] == "Parrocchia di San Rocco"


def test_localita_del_gruppo(capogruppo, capo, ragazza):
    assert _post(ragazza, "/api/v1/localita", {"nome": "Sede"}).status_code == 403
    sede = _post(capo, "/api/v1/localita", {"nome": "Sede"}).json()
    url = f"/api/v1/localita/{sede['id']}"
    assert _put(capo, url, {"nome": "Sede vecchia"}).status_code == 403
    assert _put(capogruppo, url, {"nome": "Sede di via Roma"}).json()["nome"] == "Sede di via Roma"
    assert _client(capogruppo).delete(url).status_code == 204
    assert _client(capo).get("/api/v1/localita").json() == []
