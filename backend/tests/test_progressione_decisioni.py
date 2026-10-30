"""Choices confirmed by the maintainer after the phase-4 blocks (DEC-186…DEC-190): who
runs the imprese, the date of a conquest, the rover's own reading of the Punto della
Strada, coming back to clan, the length of an L/C season."""

from datetime import date, timedelta

import pytest
from django.test import Client

from apps.anagrafica.models import Appartenenza, RuoloAppartenenza
from apps.organizzazione.models import (
    Composizione,
    Incarico,
    RuoloIncarico,
    Squadriglia,
    TipoUnita,
    Unita,
)
from apps.progressione import servizi
from apps.progressione.models import Impresa, PercorsoCompetenza, PeriodoBranca, Stagione
from tests.conftest import INIZIO_ANNO, crea_capo, crea_persona, nato_anni_fa

pytestmark = pytest.mark.django_db

OGGI = date.today()


def _client(chi) -> Client:
    client = Client()
    client.force_login(chi.utente)
    return client


def _post(chi, url, dati=None):
    return _client(chi).post(url, dati or {}, content_type="application/json")


def _put(chi, url, dati):
    return _client(chi).put(url, dati, content_type="application/json")


# --- Imprese: CSQ and Consiglio d'impresa (DEC-187) ----------------------------------------


@pytest.fixture
def altra_sq(reparto):
    return Squadriglia.objects.create(unita=reparto, nome="Volpi", sesso="F")


def _impresa(chi, reparto, **dati):
    return _post(
        chi,
        f"/api/v1/unita/{reparto.pk}/imprese",
        {"titolo": "Costruire una zattera", "dal": OGGI.isoformat(), **dati},
    )


def test_il_csq_guida_le_imprese_della_sua_squadriglia(
    capo, csq, ragazza, reparto, squadriglia, altra_sq, genitore, estraneo
):
    url = f"/api/v1/unita/{reparto.pk}/imprese"
    for chi in (ragazza, genitore, estraneo):
        assert _client(chi).get(url).status_code == 403
    assert _client(csq).get(url).json()["puo_creare"] is True
    assert _impresa(csq, reparto, livello="REPARTO").status_code == 403
    assert (
        _impresa(csq, reparto, livello="SQUADRIGLIA", squadriglia_id=altra_sq.pk).status_code == 403
    )
    dati = _impresa(csq, reparto, livello="SQUADRIGLIA", squadriglia_id=squadriglia.pk).json()
    impresa = dati["imprese"][0]
    assert impresa["puo_modificare"] and impresa["puo_gestire_posti"]
    # Posti for the patrol only; the link to an impegno is the staff's.
    posti = f"/api/v1/imprese/{impresa['id']}/posti"
    altro = crea_persona("Rita", "Altra", data_nascita=nato_anni_fa(13))
    Appartenenza.objects.create(
        persona=altro, unita=reparto, ruolo=RuoloAppartenenza.RAGAZZO, data_inizio=INIZIO_ANNO
    )
    assert _post(csq, posti, {"persona_id": altro.pk, "ruolo": "Cuoca"}).status_code == 400
    dati = _post(csq, posti, {"persona_id": ragazza.pk, "ruolo": "Cuoca"}).json()
    posto = dati["imprese"][0]["posti"][0]
    risposta = _post(
        csq,
        f"/api/v1/posti-azione/{posto['id']}/verifica",
        {"il": OGGI.isoformat(), "sede": "CONSIGLIO_SQ"},
    )
    assert risposta.status_code == 200
    # The staff's reparto impresa is not shown to the CSQ.
    _impresa(capo, reparto, livello="REPARTO")
    assert len(_client(csq).get(url).json()["imprese"]) == 1
    assert len(_client(capo).get(url).json()["imprese"]) == 2


def test_il_consiglio_d_impresa(capo, csq, ragazza, reparto, squadriglia):
    impresa = _impresa(capo, reparto, livello="REPARTO").json()["imprese"][0]
    url = f"/api/v1/imprese/{impresa['id']}/consiglio"
    assert _put(csq, url, {"persone": [ragazza.pk]}).status_code in (403, 404)
    assert _put(capo, url, {"persone": [ragazza.pk]}).status_code == 200
    me = _client(ragazza).get("/api/v1/io").json()
    assert me["imprese_reparto"] == reparto.pk
    posti = f"/api/v1/imprese/{impresa['id']}/posti"
    dati = _post(ragazza, posti, {"persona_id": csq.pk, "ruolo": "Topografa"}).json()
    voce = dati["imprese"][0]
    assert voce["puo_gestire_posti"] and not voce["puo_modificare"]
    # Not the details of the impresa.
    risposta = _put(
        ragazza,
        f"/api/v1/imprese/{impresa['id']}",
        {"livello": "REPARTO", "titolo": "Altro", "dal": OGGI.isoformat()},
    )
    assert risposta.status_code == 403
    # Once it has ended, the Consiglio stops.
    Impresa.objects.filter(pk=impresa["id"]).update(
        dal=OGGI - timedelta(days=30), al=OGGI - timedelta(days=1)
    )
    assert _post(ragazza, posti, {"persona_id": ragazza.pk, "ruolo": "Cuoca"}).status_code == 403
    assert _client(ragazza).get("/api/v1/io").json()["imprese_reparto"] is None


def test_un_capo_non_dello_staff_legge_ma_non_scrive(capo, coca, reparto, squadriglia, capogruppo):
    altro = crea_capo("Carlo", "Altro", "altro@example.invalid")
    for chi in (altro, capogruppo):
        assert _client(chi).get(f"/api/v1/unita/{reparto.pk}/imprese").status_code == 200
        assert _impresa(chi, reparto, livello="REPARTO").status_code == 403


# --- The date of a conquest (DEC-190) -----------------------------------------------------


def test_la_conquista_ha_la_sua_data(capo, ragazza):
    _post(
        capo,
        f"/api/v1/persone/{ragazza.pk}/progressione/sentiero",
        {"data": (OGGI - timedelta(days=200)).isoformat(), "precisione": "GIORNO"},
    )
    voce = _post(
        capo,
        f"/api/v1/persone/{ragazza.pk}/progressione/competenze",
        {"tipo": "SPECIALITA", "codice": "EGSP001"},
    ).json()["competenze"][0]
    for azione in ("avvia", "proponi_verifica"):
        _post(capo, f"/api/v1/competenze/{voce['id']}/{azione}")
    il = OGGI - timedelta(days=5)
    assert (
        _post(
            capo, f"/api/v1/competenze/{voce['id']}/riconosci", {"il": il.isoformat()}
        ).status_code
        == 200
    )
    assert PercorsoCompetenza.objects.get().riconosciuto_il == il


# --- R/S: the rover's reading, coming back (DEC-188, DEC-189) -------------------------------


@pytest.fixture
def clan(gruppo):
    return Unita.objects.create(
        gruppo=gruppo, nome="Hirpinia", tipo=TipoUnita.CLAN_FUOCO, composizione=Composizione.MISTA
    )


@pytest.fixture
def capo_clan(coca, clan):
    persona = crea_capo("Elena", "Clan", "clan@example.invalid")
    Incarico.objects.create(
        persona=persona, ruolo=RuoloIncarico.CAPO_UNITA, unita=clan, data_inizio=INIZIO_ANNO
    )
    return persona


@pytest.fixture
def scolta(clan):
    persona = crea_persona(
        "Sara", "Scolta", "scolta@example.invalid", data_nascita=nato_anni_fa(19)
    )
    Appartenenza.objects.create(
        persona=persona, unita=clan, ruolo=RuoloAppartenenza.RAGAZZO, data_inizio=INIZIO_ANNO
    )
    return persona


def _strada(capo_clan, scolta, giorni=300):
    return _post(
        capo_clan,
        f"/api/v1/persone/{scolta.pk}/progressione/sentiero",
        {"data": (OGGI - timedelta(days=giorni)).isoformat(), "precisione": "GIORNO"},
    )


def test_la_voce_della_scolta(capo_clan, scolta, capo):
    _strada(capo_clan, scolta)
    periodo = PeriodoBranca.objects.get(persona=scolta)
    punto = _post(
        capo_clan,
        f"/api/v1/progressione/periodi/{periodo.pk}/punti-strada",
        {"data": OGGI.isoformat(), "sintesi": "Bene"},
    ).json()["punti_strada"][0]
    url = f"/api/v1/punti-strada/{punto['id']}/voce"
    assert _put(capo_clan, url, {"testo": "x"}).status_code == 403
    dati = _put(scolta, url, {"testo": "Ho capito che il servizio mi cambia"}).json()
    assert dati["puo_scrivere_voce"] is True
    assert dati["punti_strada"][0]["voce"] == "Ho capito che il servizio mi cambia"
    letto = _client(capo).get(f"/api/v1/persone/{scolta.pk}/progressione").json()
    assert letto["punti_strada"][0]["voce"] == "Ho capito che il servizio mi cambia"
    # The staff saving the Punto keeps it.
    _put(
        capo_clan,
        f"/api/v1/punti-strada/{punto['id']}",
        {"data": OGGI.isoformat(), "sintesi": "Meglio"},
    )
    assert (
        _client(scolta)
        .get(f"/api/v1/persone/{scolta.pk}/progressione")
        .json()["punti_strada"][0]["voce"]
    )


def test_rientro_in_clan(capo_clan, scolta):
    _strada(capo_clan, scolta)
    periodo = PeriodoBranca.objects.get(persona=scolta)
    _post(
        capo_clan,
        f"/api/v1/progressione/periodi/{periodo.pk}/conclusione",
        {
            "data": (OGGI - timedelta(days=100)).isoformat(),
            "precisione": "GIORNO",
            "tipo": "INTERRUZIONE",
        },
    )
    assert _strada(capo_clan, scolta, giorni=120).status_code == 400  # before the end
    assert _strada(capo_clan, scolta, giorni=10).status_code == 201
    nuovo = PeriodoBranca.objects.get(persona=scolta, data_fine__isnull=True)
    _post(
        capo_clan,
        f"/api/v1/progressione/periodi/{nuovo.pk}/conclusione",
        {"data": OGGI.isoformat(), "precisione": "GIORNO", "tipo": "PARTENZA"},
    )
    risposta = _strada(capo_clan, scolta, giorni=0)
    assert risposta.status_code == 400 and "Partenza" in risposta.json()["detail"]


# --- L/C: length of a season (DEC-190) -----------------------------------------------------


def test_avvisi_sulla_durata_della_stagione(gruppo):
    branco = Unita.objects.create(
        gruppo=gruppo, nome="Seeonee", tipo=TipoUnita.BRANCO, composizione=Composizione.MISTA
    )

    def stagione(giorni):
        return Stagione(
            unita=branco,
            nome="S",
            inizio_previsto=OGGI,
            fine_prevista=OGGI + timedelta(days=giorni),
        )

    assert servizi.avvisi_stagione(stagione(100)) == []
    assert "meno di due mesi" in servizi.avvisi_stagione(stagione(40))[0]
    assert "più di cinque mesi" in servizi.avvisi_stagione(stagione(200))[0]
