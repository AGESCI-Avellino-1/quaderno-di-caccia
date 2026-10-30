"""R/S: passi, Carta di clan, Punto della Strada, conclusione (DEC-67, DEC-179…DEC-181),
with the cases of the PP specification v1.0 (§6, §17.7, §17.10, §19.4; V12…V15)."""

from datetime import date, timedelta

import pytest
from auditlog.models import LogEntry
from django.test import Client

from apps.anagrafica.models import Appartenenza, RelazioneTutela, RuoloAppartenenza
from apps.organizzazione.models import (
    Composizione,
    Incarico,
    RuoloIncarico,
    TipoUnita,
    Unita,
)
from apps.progressione.models import FirmaCarta, PeriodoBranca, Tappa
from tests.conftest import INIZIO_ANNO, crea_capo, crea_persona, nato_anni_fa

pytestmark = pytest.mark.django_db

OGGI = date.today()


def _client(chi) -> Client:
    client = Client()
    client.force_login(chi.utente)
    return client


def _post(chi, url, dati=None):
    return _client(chi).post(url, dati or {}, content_type="application/json")


def _giorno(giorno=OGGI):
    return {"data": giorno.isoformat(), "precisione": "GIORNO"}


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
def rover(clan):
    persona = crea_persona("Paolo", "Rover", "rover@example.invalid", data_nascita=nato_anni_fa(17))
    Appartenenza.objects.create(
        persona=persona, unita=clan, ruolo=RuoloAppartenenza.RAGAZZO, data_inizio=INIZIO_ANNO
    )
    return persona


@pytest.fixture
def papa(rover):
    persona = crea_persona("Pietro", "Rover", "papa@example.invalid")
    RelazioneTutela.objects.create(tutore=persona, minore=rover, tipo="GENITORE")
    return persona


@pytest.fixture
def strada(capo_clan, rover):
    risposta = _post(
        capo_clan,
        f"/api/v1/persone/{rover.pk}/progressione/sentiero",
        _giorno(OGGI - timedelta(days=300)),
    )
    assert risposta.status_code == 201, risposta.content
    return PeriodoBranca.objects.get(persona=rover)


def test_si_apre_la_strada_in_clan(strada, rover):
    assert strada.branca == "RS"
    assert Tappa.objects.get(periodo=strada).fase == "SCOPERTA"


def test_senza_carta_resta_in_scoperta(capo_clan, strada):
    """A scolta in clan who has not signed the Carta can still be in scoperta (§19.4)."""
    tappa = strada.tappe.get()
    # Neither the Consiglio della Legge nor a placement moves the passi R/S.
    assert (
        _post(capo_clan, f"/api/v1/progressione/tappe/{tappa.pk}/riconosci", _giorno()).status_code
        == 400
    )
    risposta = _post(
        capo_clan,
        f"/api/v1/progressione/tappe/{tappa.pk}/responsabilita",
        _giorno(),
    )
    assert risposta.status_code == 400
    assert strada.tappe.get().fase == "SCOPERTA"


def test_la_firma_della_carta_apre_la_competenza_una_volta(capo_clan, strada):
    """A Carta signature entered twice does not open competenza twice (§19.4)."""
    giorno = OGGI - timedelta(days=100)
    url = f"/api/v1/progressione/periodi/{strada.pk}/carta"
    assert _post(capo_clan, url, _giorno(giorno)).status_code == 200
    dati = _post(capo_clan, url, _giorno(giorno)).json()
    assert [t["fase"] for t in dati["periodi"][0]["tappe"]] == ["SCOPERTA", "COMPETENZA"]
    assert dati["periodi"][0]["firma_carta"]["data"] == giorno.isoformat()
    assert _post(capo_clan, url, _giorno(giorno - timedelta(days=1))).status_code == 400
    # A wrong date is corrected, and the competenza moves with it.
    giusta = giorno - timedelta(days=7)
    risposta = _client(capo_clan).put(
        url, {**_giorno(giusta), "motivo": "Era la route"}, content_type="application/json"
    )
    assert risposta.status_code == 200
    assert strada.tappe.get(fase="COMPETENZA").data_inizio == giusta
    assert FirmaCarta.objects.get().data == giusta


def test_responsabilita_e_conclusione(capo_clan, strada, rover):
    _post(
        capo_clan,
        f"/api/v1/progressione/periodi/{strada.pk}/carta",
        _giorno(OGGI - timedelta(days=50)),
    )
    competenza = strada.tappe.get(fase="COMPETENZA")
    url = f"/api/v1/progressione/tappe/{competenza.pk}/responsabilita"
    assert _post(capo_clan, url, _giorno(OGGI - timedelta(days=10))).status_code == 200
    # Saluto fraterno is distinct from Partenza (§19.4); either closes the period only.
    dati = _post(
        capo_clan,
        f"/api/v1/progressione/periodi/{strada.pk}/conclusione",
        {**_giorno(), "tipo": "SALUTO_FRATERNO", "nota": "Va a studiare fuori"},
    ).json()
    periodo = dati["periodi"][0]
    assert periodo["conclusione"]["tipo_nome"] == "Saluto fraterno"
    assert periodo["motivo_fine"] == "Saluto fraterno" and periodo["attivo"] is False
    assert not Tappa.objects.filter(periodo=strada, data_fine__isnull=True).exists()
    # The clan membership is BuonaStrada's (DEC-181).
    assert Appartenenza.objects.attive().filter(persona=rover).exists()
    # Done once.
    risposta = _post(
        capo_clan,
        f"/api/v1/progressione/periodi/{strada.pk}/conclusione",
        {**_giorno(), "tipo": "PARTENZA"},
    )
    assert risposta.status_code == 400


def test_a_21_anni_nessuna_partenza_automatica(capo_clan, strada, rover):
    """A rover turning 21 does not get an automatic Partenza (§19.4, V14)."""
    rover.data_nascita = nato_anni_fa(22)
    rover.save()
    dati = _client(capo_clan).get(f"/api/v1/persone/{rover.pk}/progressione").json()
    assert dati["periodi"][0]["attivo"] is True and dati["periodi"][0]["conclusione"] is None


def test_il_rover_propone_obiettivi_e_impegni(capo_clan, strada, rover):
    """As in E/G (DEC-179); an obiettivo may cover several dimensions (§19.4): it is free
    text, never four mandatory ones (V13)."""
    url = f"/api/v1/persone/{rover.pk}/progressione/mete"
    risposta = _post(rover, url, {"testo": "Servizio in mensa e lettura del Vangelo"})
    assert risposta.status_code == 201, risposta.content
    meta = risposta.json()["mete"][0]
    assert meta["stato"] == "BOZZA" and meta["proposto_dal_ragazzo"] is True
    impegni = _post(
        rover, f"/api/v1/persone/{rover.pk}/progressione/impegni", {"testo": "Ogni sabato"}
    )
    assert impegni.status_code == 201


def test_punto_della_strada_e_parte_riservata(capo_clan, strada, rover, papa, capo, estraneo):
    """With a private situation the parents see only the summary (§19.4, DEC-180)."""
    obiettivo = _post(
        capo_clan, f"/api/v1/persone/{rover.pk}/progressione/mete", {"testo": "Servizio"}
    ).json()["mete"][0]
    risposta = _post(
        capo_clan,
        f"/api/v1/progressione/periodi/{strada.pk}/punti-strada",
        {
            "data": OGGI.isoformat(),
            "sintesi": "Cammino sereno",
            "servizio": "Mensa Caritas, costante",
            "riservato": "Difficoltà in famiglia",
            "obiettivi": [obiettivo["id"]],
        },
    )
    assert risposta.status_code == 201, risposta.content
    punto = risposta.json()["punti_strada"][0]
    assert punto["riservato"] == "Difficoltà in famiglia"
    assert punto["obiettivi"] == [obiettivo["id"]]
    url = f"/api/v1/persone/{rover.pk}/progressione"
    for chi in (rover, capo):
        assert (
            _client(chi).get(url).json()["punti_strada"][0]["riservato"] == "Difficoltà in famiglia"
        )
    dal_papa = _client(papa).get(url).json()["punti_strada"][0]
    assert dal_papa["sintesi"] == "Cammino sereno" and dal_papa["riservato"] is None
    assert _client(estraneo).get(url).status_code == 404
    # Neither the parent nor the rover writes it; the audit log does not hold it.
    assert (
        _post(
            papa,
            f"/api/v1/progressione/periodi/{strada.pk}/punti-strada",
            {"data": OGGI.isoformat()},
        ).status_code
        == 403
    )
    assert (
        _post(
            rover,
            f"/api/v1/progressione/periodi/{strada.pk}/punti-strada",
            {"data": OGGI.isoformat()},
        ).status_code
        == 403
    )
    assert not LogEntry.objects.filter(changes_text__icontains="famiglia").exists()
    # Repeatable; a change by the staff keeps the private part when it is not sent.
    _client(capo_clan).put(
        f"/api/v1/punti-strada/{punto['id']}",
        {"data": OGGI.isoformat(), "sintesi": "Cammino sereno, più presente"},
        content_type="application/json",
    )
    assert (
        _client(rover).get(url).json()["punti_strada"][0]["riservato"] == "Difficoltà in famiglia"
    )


def test_fascicolo_e_cancellazione(capo_clan, strada, rover, capogruppo):
    from apps.progressione.models import PuntoStrada

    _post(capo_clan, f"/api/v1/progressione/periodi/{strada.pk}/carta", _giorno())
    _post(
        capo_clan,
        f"/api/v1/progressione/periodi/{strada.pk}/punti-strada",
        {"data": OGGI.isoformat(), "sintesi": "Bene", "riservato": "Solo per i capi"},
    )
    dati = _client(capogruppo).get(f"/api/v1/persone/{rover.pk}/fascicolo").json()
    assert dati["progressione_personale"][0]["Firma della Carta di clan"]
    assert dati["punti_della_strada"][0]["Parte riservata"] == "Solo per i capi"
    url = f"/api/v1/persone/{rover.pk}/cancellazione"
    assert _post(capogruppo, url, {"cognome": "Rover"}).status_code == 200
    assert not (PuntoStrada.objects.exists() or FirmaCarta.objects.exists())
    assert not PeriodoBranca.objects.filter(persona=rover).exists()
