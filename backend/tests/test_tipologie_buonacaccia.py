"""Types of BuonaCaccia events and the constraints on who registers (DEC-398, DEC-399)."""

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest
from django.test import Client

from apps.anagrafica.models import Appartenenza, RuoloAppartenenza
from apps.buonacaccia import servizi
from apps.buonacaccia.models import (
    EventoBuonaCaccia,
    StatoIscrizione,
    TipologiaBuonaCaccia,
    tipologia_altro,
)
from apps.eventi.models import Evento, TipoEvento
from apps.organizzazione.models import TipoUnita, Unita
from tests.conftest import INIZIO_ANNO, crea_capo, crea_persona, nato_anni_fa

ROMA = ZoneInfo("Europe/Rome")
OGGI = date.today()
URL = "/api/v1/buonacaccia/tipologie"


def _client(chi) -> Client:
    client = Client()
    client.force_login(chi.utente)
    return client


def _json(chi, metodo, url, dati=None):
    return getattr(_client(chi), metodo)(url, dati or {}, content_type="application/json")


def _tipologia(codice: str) -> TipologiaBuonaCaccia:
    return TipologiaBuonaCaccia.objects.get(codice=codice)


def _evento(capo, giorno: date | None = None, **vincoli) -> Evento:
    giorno = giorno or OGGI + timedelta(days=30)
    evento = Evento(
        titolo="Capi Squadriglia di Zona",
        tipo=TipoEvento.CAMPO,
        inizio=datetime.combine(giorno, time(9), ROMA),
        fine=datetime.combine(giorno + timedelta(days=2), time(17), ROMA),
    )
    dettagli = EventoBuonaCaccia(tipologia=_tipologia("2010102"), **vincoli)
    return servizi.salva_evento(evento, dettagli, capo.utente)


def _iscrivi(capo, evento, persona):
    return servizi.iscrivi(
        evento,
        persona,
        capo.utente,
        iscritto_il=OGGI - timedelta(days=1),
        stato=StatoIscrizione.AMMESSO,
    )


def test_catalogo_di_buonacaccia_e_altro(db):
    assert TipologiaBuonaCaccia.objects.exclude(codice="").count() == 64
    altro = tipologia_altro()
    assert altro.senza_vincoli() and altro.attiva
    assert _tipologia("1010101").nome == "Piccole Orme"
    assert _tipologia("2010102").branche == ["EG"]


def test_solo_le_branche_del_gruppo(capo, reparto):
    nomi = {t["nome"] for t in _client(capo).get(URL).json()}
    # The group has a reparto and no branco or clan.
    assert "Capi Squadriglia" in nomi and "Altro" in nomi and "CFT" in nomi
    assert "Piccole Orme" not in nomi and "EPPPI" not in nomi
    Unita.objects.create(gruppo=reparto.gruppo, nome="Seeonee", tipo=TipoUnita.BRANCO_CERCHIO)
    assert "Piccole Orme" in {t["nome"] for t in _client(capo).get(URL).json()}
    # Who manages them sees them all.
    assert len(_client(capo).get(f"{URL}?tutte=true").json()) == 66


def test_chi_gestisce_le_tipologie(capo, capogruppo, csq, ragazza, genitore, estraneo):
    nuova = {"nome": "Uscita di Zona", "categoria": "SPECIALE", "eta_minima": 12}
    for chi in (csq, ragazza, genitore, estraneo):
        assert _json(chi, "post", URL, nuova).status_code == 403
        assert _client(chi).get(f"{URL}?tutte=true").status_code == 403
    # Every capo, whatever their role.
    semplice = crea_capo("Carlo", "Semplice", "semplice@example.invalid")
    for chi in (capo, capogruppo, semplice):
        assert _client(chi).get(f"{URL}?tutte=true").status_code == 200
    risposta = _json(semplice, "post", URL, nuova)
    assert risposta.status_code == 201
    tipologia = risposta.json()
    cambiata = {**nuova, "eta_minima": 14, "eta_massima": 11}
    assert _json(capo, "put", f"{URL}/{tipologia['id']}", cambiata).status_code == 400
    assert _client(capogruppo).delete(f"{URL}/{tipologia['id']}").status_code == 204


def test_altro_senza_vincoli_e_che_resta(capo):
    altro = tipologia_altro()
    dati = {"nome": "Altro", "categoria": "ALTRO"}
    assert _json(capo, "put", f"{URL}/{altro.pk}", {**dati, "eta_minima": 8}).status_code == 400
    assert _json(capo, "put", f"{URL}/{altro.pk}", {**dati, "attiva": False}).status_code == 400
    assert _client(capo).delete(f"{URL}/{altro.pk}").status_code == 400
    # Only one «Altro».
    assert _json(capo, "post", URL, {"nome": "Altro bis", "categoria": "ALTRO"}).status_code == 400


def test_usata_si_disattiva_non_si_toglie(capo):
    _evento(capo)
    capi_sq = _tipologia("2010102")
    assert _client(capo).delete(f"{URL}/{capi_sq.pk}").status_code == 400
    dati = {"nome": capi_sq.nome, "categoria": "EG", "attiva": False, "branche": ["EG"]}
    assert _json(capo, "put", f"{URL}/{capi_sq.pk}", dati).status_code == 200
    assert capi_sq.nome not in {t["nome"] for t in _client(capo).get(URL).json()}


def test_branca_ed_eta_alla_partenza(capo, ragazza, reparto):
    # The ragazza is 12 today; the event starts in a month.
    evento = _evento(capo, branche=["EG"], eta_minima=13)
    url = f"/api/v1/buonacaccia/eventi/{evento.pk}/iscrivibili"
    assert _client(capo).get(url).json() == []
    risposta = _json(
        capo,
        "post",
        f"/api/v1/buonacaccia/eventi/{evento.pk}/iscrizioni",
        {"persona_id": ragazza.pk, "iscritto_il": OGGI.isoformat()},
    )
    assert risposta.status_code == 400
    assert "alla partenza ha 12 anni, il minimo è 13" in risposta.json()["detail"]

    # Turning 13 the day before the start is enough; the day after is not.
    partenza = OGGI + timedelta(days=30)
    # The 13th birthday falls on the first day (on 1 March for a start on 29 February).
    tredici = partenza.replace(year=partenza.year - 13, day=28) + timedelta(days=partenza.day - 28)
    ragazza.data_nascita = tredici - timedelta(days=1)
    ragazza.save()
    assert [p["id"] for p in _client(capo).get(url).json()] == [ragazza.pk]
    ragazza.data_nascita = tredici + timedelta(days=1)
    ragazza.save()
    assert _client(capo).get(url).json() == []

    solo_rs = _evento(capo, branche=["RS"])
    risposta = _json(
        capo,
        "post",
        f"/api/v1/buonacaccia/eventi/{solo_rs.pk}/iscrizioni",
        {"persona_id": ragazza.pk, "iscritto_il": OGGI.isoformat()},
    )
    assert "l'evento è per Rover e Scolte" in risposta.json()["detail"]


def test_livello_di_formazione_dei_capi(capo, coca):
    evento = _evento(capo, branche=["COCA"], livello_minimo=2)
    url = f"/api/v1/buonacaccia/eventi/{evento.pk}/partecipanti"
    capo.livello_formazione = 1
    capo.save()
    risposta = _json(capo, "put", url, {"persona_id": capo.pk})
    assert risposta.status_code == 400
    assert "livello di formazione 1, il minimo è 2" in risposta.json()["detail"]
    dettaglio = _client(capo).get(f"/api/v1/buonacaccia/eventi/{evento.pk}").json()
    assert dettaglio["non_puoi_partecipare"] == "ha il livello di formazione 1, il minimo è 2."

    # Unknown in BuonaStrada: may take part, with a warning.
    capo.livello_formazione = None
    capo.save()
    risposta = _json(capo, "put", url, {"persona_id": capo.pk})
    assert risposta.status_code == 200
    (adulto,) = risposta.json()["adulti"]
    assert "non è in BuonaStrada" in adulto["avvisi"][0]

    # A provisional code is level 1 (DEC-399).
    nuovo = crea_capo("Nuovo", "Entrato", "nuovo@example.invalid")
    nuovo.codice_socio = "9000000031"
    nuovo.save()
    assert "minimo è 2" in servizi.motivo_esclusione(evento, nuovo)


def test_massimi_solo_un_avviso(capo, ragazza, csq, reparto, gruppo):
    evento = _evento(capo, massimo_per_unita=1, massimo_per_gruppo=2)
    _iscrivi(capo, evento, ragazza)
    _iscrivi(capo, evento, csq)  # past the unit's maximum: still registered
    # A ragazzo of a linked unit counts in his own.
    gemello = Unita.objects.create(gruppo=gruppo, tipo=TipoUnita.REPARTO, nome="Gemello")
    altro = crea_persona("Piero", "Gemello", "piero@example.invalid", data_nascita=nato_anni_fa(13))
    Appartenenza.objects.create(
        persona=altro, unita=gemello, ruolo=RuoloAppartenenza.RAGAZZO, data_inizio=INIZIO_ANNO
    )
    servizi.salva_evento(evento, evento.buonacaccia, capo.utente)
    assert servizi.avvisi_massimi(evento) == [
        f"Iscritti di {reparto}: 2, il massimo per unità è 1."
    ]
    dettaglio = _client(capo).get(f"/api/v1/buonacaccia/eventi/{evento.pk}").json()
    assert dettaglio["avvisi"] == servizi.avvisi_massimi(evento)


def test_il_tipo_scelto_decide_piccole_orme_e_formazione(capo):
    evento = _evento(capo)
    dettagli = evento.buonacaccia
    servizi.applica_tipologia(dettagli, _tipologia("1010101"))
    assert dettagli.piccole_orme and not dettagli.formazione_capi
    servizi.applica_tipologia(dettagli, _tipologia("4000101"))
    assert dettagli.formazione_capi and dettagli.tipo_campo == "CFT"
    # The same type again leaves the flags alone: an event converted from the old ones keeps
    # its kind of camp.
    dettagli.save()
    dettagli.tipo_campo = "CFM"
    servizi.applica_tipologia(dettagli, _tipologia("4000101"))
    assert dettagli.tipo_campo == "CFM"


@pytest.mark.parametrize("codice", ["2010102", "1010101"])
def test_evento_dal_modulo_con_i_vincoli(capo, codice):
    tipologia = _tipologia(codice)
    risposta = _json(
        capo,
        "post",
        "/api/v1/buonacaccia/eventi",
        {
            "titolo": "Evento",
            "inizio": datetime.combine(OGGI, time(9), ROMA).isoformat(),
            "fine": datetime.combine(OGGI, time(18), ROMA).isoformat(),
            "tipologia_id": tipologia.pk,
            "branche": tipologia.branche,
            "eta_minima": 12,
            "massimo_per_unita": 4,
        },
    )
    assert risposta.status_code == 201
    dettaglio = _client(capo).get(f"/api/v1/buonacaccia/eventi/{risposta.json()['id']}").json()
    assert dettaglio["tipologia"] == tipologia.nome
    assert (dettaglio["eta_minima"], dettaglio["massimo_per_unita"]) == (12, 4)
    assert dettaglio["piccole_orme"] == (codice == "1010101")


def test_eventi_gia_inseriti_prendono_il_tipo(capo):
    # Converted at the update: certain types from the old flags, «Altro» for the rest; the
    # flags themselves stay (DEC-398).
    from importlib import import_module

    from django.apps import apps

    eventi = [_evento(capo) for _ in range(4)]
    vecchi = [
        {"piccole_orme": True},
        {"formazione_capi": True, "tipo_campo": "CFT"},
        {"formazione_capi": True, "tipo_campo": "CFM"},
        {},
    ]
    for evento, flag in zip(eventi, vecchi, strict=True):
        EventoBuonaCaccia.objects.filter(evento=evento).update(
            tipologia=tipologia_altro(), branche=[], **flag
        )
    import_module("apps.buonacaccia.migrations.0006_carica_tipologie").carica(apps, None)
    tipi = [EventoBuonaCaccia.objects.get(evento=e) for e in eventi]
    assert [str(d.tipologia) for d in tipi] == [
        "Piccole Orme",
        "CFT",
        "Altro formazione capi",
        "Altro",
    ]
    assert tipi[2].tipo_campo == "CFM" and tipi[2].formazione_capi
    assert tipi[0].branche == ["LC"] and tipi[3].branche == []
    assert TipologiaBuonaCaccia.objects.filter(categoria="ALTRO").count() == 1
