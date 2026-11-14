"""Turns of the group round the units (DEC-406)."""

from datetime import date, datetime, time

import pytest
from django.test import Client
from django.utils import timezone

from apps.eventi import servizi, turni_gruppo
from apps.eventi.models import (
    Evento,
    Livello,
    PeriodoCambiato,
    PeriodoTurno,
    TipoEvento,
    TurnoGruppo,
)
from apps.organizzazione.models import Composizione, TipoUnita, Unita
from tests.conftest import crea_capo

pytestmark = pytest.mark.django_db
ROMA = timezone.get_default_timezone()


def _client(chi) -> Client:
    client = Client()
    client.force_login(chi.utente)
    return client


def _json(chi, metodo, url, dati=None):
    return getattr(_client(chi), metodo)(url, dati or {}, content_type="application/json")


@pytest.fixture
def branco(gruppo) -> Unita:
    return Unita.objects.create(
        gruppo=gruppo, nome="Branco Prova", tipo=TipoUnita.BRANCO, composizione=Composizione.MISTA
    )


def _turno(*unita, periodo=PeriodoTurno.MESE, dal=date(2027, 1, 15)) -> TurnoGruppo:
    return TurnoGruppo.objects.create(
        nome="Pulizia della sede", unita=[u.pk for u in unita], periodo=periodo, dal=dal
    )


def _riunione(unita, giorno: date, utente):
    return servizi.crea(
        Evento(
            titolo="Riunione",
            tipo=TipoEvento.RIUNIONE,
            livello=Livello.UNITA,
            inizio=datetime.combine(giorno, time(16), ROMA),
            fine=datetime.combine(giorno, time(18), ROMA),
        ),
        [unita],
        utente,
    )


# --- Periods -----------------------------------------------------------------------------------


def test_mesi_dal_primo_giorno_del_mese(reparto, branco):
    turno = _turno(reparto, branco)
    assert turni_gruppo.indice(turno, date(2027, 1, 14)) is None
    assert turni_gruppo.indice(turno, date(2027, 1, 31)) == 0
    assert turni_gruppo.indice(turno, date(2027, 2, 1)) == 1
    assert turni_gruppo.limiti(turno, 0) == (date(2027, 1, 15), date(2027, 1, 31))
    assert turni_gruppo.limiti(turno, 1) == (date(2027, 2, 1), date(2027, 2, 28))


def test_trimestri_e_settimane(reparto, branco):
    trimestre = _turno(reparto, branco, periodo=PeriodoTurno.TRIMESTRE, dal=date(2026, 11, 3))
    assert turni_gruppo.indice(trimestre, date(2027, 1, 31)) == 0
    assert turni_gruppo.indice(trimestre, date(2027, 2, 1)) == 1
    assert turni_gruppo.limiti(trimestre, 1) == (date(2027, 2, 1), date(2027, 4, 30))
    settimana = _turno(reparto, branco, periodo=PeriodoTurno.SETTIMANA, dal=date(2027, 1, 4))
    assert turni_gruppo.indice(settimana, date(2027, 1, 10)) == 0
    assert turni_gruppo.indice(settimana, date(2027, 1, 11)) == 1
    assert turni_gruppo.limiti(settimana, 1) == (date(2027, 1, 11), date(2027, 1, 17))


def test_la_rotazione_e_il_cambio_di_un_periodo(reparto, branco):
    turno = _turno(reparto, branco)
    PeriodoCambiato.objects.create(turno=turno, indice=2, unita=reparto)
    giorni = [date(2027, 1, 20), date(2027, 2, 10), date(2027, 3, 10), date(2027, 4, 10)]
    prossimi = turni_gruppo.prossimi(turno, 4, oggi=giorni[0])
    assert [p["unita_id"] for p in prossimi] == [reparto.pk, branco.pk, reparto.pk, branco.pk]
    assert [p["cambiato"] for p in prossimi] == [False, False, True, False]


# --- On the meetings -----------------------------------------------------------------------


def test_sulle_riunioni_dell_unita_di_turno(capo, reparto, branco, ragazza, genitore):
    _turno(reparto, branco)
    gennaio = _riunione(reparto, date(2027, 1, 23), capo.utente)
    febbraio = _riunione(reparto, date(2027, 2, 6), capo.utente)
    # Everyone who sees the meeting sees the turn: capi, ragazzi and parents.
    for chi in (capo, ragazza, genitore):
        visto = _client(chi).get(f"/api/v1/eventi/{gennaio.pk}").json()
        assert visto["turni_gruppo"] == [{"turno": "Pulizia della sede", "unita": str(reparto)}]
        # February is the branco's.
        assert _client(chi).get(f"/api/v1/eventi/{febbraio.pk}").json()["turni_gruppo"] == []


def test_non_su_una_riunione_annullata(capo, reparto, branco):
    _turno(reparto, branco)
    riunione = _riunione(reparto, date(2027, 1, 23), capo.utente)
    servizi.annulla(riunione, "Pioggia")
    assert _client(capo).get(f"/api/v1/eventi/{riunione.pk}").json()["turni_gruppo"] == []


# --- Who sets them --------------------------------------------------------------------------


def _nuovo(chi, *unita, **altro):
    dati = {"nome": "Pulizia", "unita": [u.pk for u in unita], "periodo": "MESE"}
    return _json(chi, "post", "/api/v1/turni-gruppo", {"dal": "2027-01-01", **dati, **altro})


def test_li_stabilisce_ogni_capo_della_coca(capogruppo, reparto, branco):
    semplice = crea_capo("Carlo", "Semplice", "semplice@example.invalid")
    for chi in (capogruppo, semplice):
        risposta = _nuovo(chi, reparto, branco)
        assert risposta.status_code == 201, risposta.content
    elenco = _client(semplice).get("/api/v1/turni-gruppo").json()
    assert elenco["puo_gestire"] is True
    assert len(elenco["turni"]) == 2
    assert {u["id"] for u in elenco["unita"]} >= {reparto.pk, branco.pk}


@pytest.mark.parametrize("ruolo", ["csq", "ragazza", "genitore", "estraneo"])
def test_gli_altri_no(request, ruolo, reparto, branco):
    chi = request.getfixturevalue(ruolo)
    assert _nuovo(chi, reparto, branco).status_code == 403
    assert _client(chi).get("/api/v1/turni-gruppo").status_code == 403


def test_almeno_due_unita_attive(capo, coca, reparto, branco):
    assert _nuovo(capo, reparto).status_code == 400
    assert _nuovo(capo, reparto, coca).status_code == 400  # the Co.Ca. is not one of them


def test_cambio_di_un_periodo_e_ritorno(capo, reparto, branco):
    turno = _turno(reparto, branco)
    url = f"/api/v1/turni-gruppo/{turno.pk}/periodi/3"
    assert _json(capo, "put", url, {"unita_id": reparto.pk}).status_code == 200
    assert PeriodoCambiato.objects.get(turno=turno, indice=3).unita == reparto
    altro = Unita.objects.create(
        gruppo=reparto.gruppo, nome="Clan", tipo=TipoUnita.CLAN_FUOCO, composizione="X"
    )
    assert _json(capo, "put", url, {"unita_id": altro.pk}).status_code == 400
    assert _json(capo, "put", url, {"unita_id": None}).status_code == 200
    assert not PeriodoCambiato.objects.filter(turno=turno).exists()


def test_cambiare_l_ordine_toglie_i_cambi(capo, reparto, branco):
    turno = _turno(reparto, branco)
    PeriodoCambiato.objects.create(turno=turno, indice=1, unita=reparto)
    dati = {
        "nome": "Pulizia",
        "unita": [branco.pk, reparto.pk],
        "periodo": "MESE",
        "dal": "2027-01-15",
    }
    assert _json(capo, "put", f"/api/v1/turni-gruppo/{turno.pk}", dati).status_code == 200
    assert not PeriodoCambiato.objects.filter(turno=turno).exists()
    # Only the name: the changes stay.
    PeriodoCambiato.objects.create(turno=turno, indice=1, unita=reparto)
    _json(capo, "put", f"/api/v1/turni-gruppo/{turno.pk}", {**dati, "nome": "Pulizie"})
    assert PeriodoCambiato.objects.filter(turno=turno).exists()


def test_eliminare(capo, reparto, branco):
    turno = _turno(reparto, branco)
    assert _json(capo, "delete", f"/api/v1/turni-gruppo/{turno.pk}").status_code == 200
    assert not TurnoGruppo.objects.exists()
