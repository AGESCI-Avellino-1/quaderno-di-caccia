"""Progressione Personale E/G (DEC-56…DEC-74, DEC-171…DEC-173). The test cases of the
domain specification v1.0 (§13, §19.3) that concern E/G become tests here (DEC-73).
Dates are relative to today: history cannot be in the future."""

import uuid
from datetime import date, timedelta

import pytest
from auditlog.models import LogEntry
from django.test import Client

from apps.permessi import policy
from apps.progressione.models import Fase, Impegno, Obiettivo, PeriodoBranca, Stato, Tappa
from tests.conftest import crea_capo

pytestmark = pytest.mark.django_db

OGGI = date.today()
FA_UN_ANNO = OGGI - timedelta(days=365)


def _client(chi) -> Client:
    client = Client()
    client.force_login(chi.utente)
    return client


def _post(chi, url, dati=None, **extra):
    return _client(chi).post(url, dati or {}, content_type="application/json", **extra)


def _put(chi, url, dati):
    return _client(chi).put(url, dati, content_type="application/json")


def _apri(capo, ragazza, quando=FA_UN_ANNO, precisione="GIORNO"):
    risposta = _post(
        capo,
        f"/api/v1/persone/{ragazza.pk}/progressione/sentiero",
        {"data": quando.isoformat(), "precisione": precisione},
    )
    assert risposta.status_code == 201, risposta.content
    return risposta.json()


def _tappa_in_corso(scheda) -> dict:
    (periodo,) = [p for p in scheda["periodi"] if p["attivo"]]
    return next(t for t in periodo["tappe"] if t["in_corso"])


def _giorno(giorni_fa: int) -> dict:
    return {"data": (OGGI - timedelta(days=giorni_fa)).isoformat(), "precisione": "GIORNO"}


@pytest.fixture
def altro_capo(coca):
    return crea_capo("Carlo", "Altro", "altro@example.invalid")


# --- Who sees and who writes ---------------------------------------------------------------


def test_chi_vede_e_chi_scrive(capo, altro_capo, capogruppo, ragazza, genitore, csq, estraneo):
    vede = policy.puo_vedere_progressione
    for chi in (capo, altro_capo, capogruppo, ragazza, genitore, csq):
        assert vede(chi.utente, ragazza)  # csq: same patrol (DEC-13)
    assert not vede(estraneo.utente, ragazza)
    # Only the staff of the unit writes (DEC-09); the ragazzo proposes drafts (DEC-61).
    assert policy.puo_gestire_progressione(capo.utente, ragazza)
    for chi in (altro_capo, capogruppo, ragazza, genitore, csq):
        assert not policy.puo_gestire_progressione(chi.utente, ragazza)
    assert policy.puo_proporre_percorsi(ragazza.utente, ragazza)
    assert not policy.puo_proporre_percorsi(csq.utente, ragazza)
    assert policy.puo_proporre_verifica(csq.utente, ragazza)
    # A private meta: never the CSQ (DEC-173).
    assert not policy.vede_mete_riservate(csq.utente, ragazza)
    assert policy.vede_mete_riservate(genitore.utente, ragazza)


def test_lo_apre_lo_staff_non_altri(capo, altro_capo, ragazza, estraneo):
    url = f"/api/v1/persone/{ragazza.pk}/progressione/sentiero"
    dati = {"data": OGGI.isoformat(), "precisione": "GIORNO"}
    assert _post(altro_capo, url, dati).status_code == 403
    assert _post(ragazza, url, dati).status_code == 403
    assert _post(estraneo, url, dati).status_code == 404
    scheda = _apri(capo, ragazza, OGGI)
    assert _tappa_in_corso(scheda)["fase"] == "SCOPERTA"
    assert _post(capo, url, dati).status_code == 400  # one open sentiero


# --- Tappe, Promessa, badges (§13, §19.3) -------------------------------------------------


def test_il_distintivo_non_completa_la_tappa(capo, ragazza):
    """§13: the Competenza badge is handed over → the tappa starts, not completed."""
    scheda = _apri(capo, ragazza)
    scoperta = _tappa_in_corso(scheda)
    scheda = _post(
        capo, f"/api/v1/progressione/tappe/{scoperta['id']}/riconosci", _giorno(100)
    ).json()
    competenza = _tappa_in_corso(scheda)
    assert competenza["fase"] == "COMPETENZA" and competenza["inizio"]["data"]
    scheda = _post(
        capo, f"/api/v1/progressione/tappe/{competenza['id']}/distintivo", _giorno(90)
    ).json()
    competenza = _tappa_in_corso(scheda)
    assert competenza["distintivo"] and competenza["completata"] is None


def test_due_invii_dello_stesso_riconoscimento(capo, ragazza):
    """§19.3: one effect only."""
    scoperta = _tappa_in_corso(_apri(capo, ragazza))
    url = f"/api/v1/progressione/tappe/{scoperta['id']}/riconosci"
    assert _post(capo, url, _giorno(10)).status_code == 200
    assert _post(capo, url, _giorno(10)).status_code == 200
    assert Tappa.objects.filter(fase=Fase.COMPETENZA).count() == 1


def test_le_date_di_una_tappa_si_correggono_con_il_motivo(capo, altro_capo, ragazza):
    """A recording mistake is corrected with its reason, by the staff only (DEC-70)."""
    scoperta = _tappa_in_corso(_apri(capo, ragazza))
    _post(capo, f"/api/v1/progressione/tappe/{scoperta['id']}/riconosci", _giorno(100))
    url = f"/api/v1/progressione/tappe/{scoperta['id']}"
    giusta = {**_giorno(101), "campo": "completata", "motivo": "Il Consiglio era il giorno prima"}
    assert _put(altro_capo, url, giusta).status_code == 403
    assert _put(capo, url, {**giusta, "motivo": ""}).status_code == 400
    assert _put(capo, url, giusta).status_code == 200
    tappa = Tappa.objects.get(pk=scoperta["id"])
    assert tappa.completata_il == OGGI - timedelta(days=101)
    assert tappa.nota_rettifica == "Il Consiglio era il giorno prima"


def test_dopo_la_responsabilita_il_sentiero_continua(capo, ragazza):
    """§13 and §19.3: responsabilità concluded in February, passaggio in October: the
    sentiero stays open, new impegni are still possible (V16)."""
    tappa = _tappa_in_corso(_apri(capo, ragazza, OGGI - timedelta(days=900)))
    for giorni in (600, 300, 30):
        scheda = _post(
            capo, f"/api/v1/progressione/tappe/{tappa['id']}/riconosci", _giorno(giorni)
        ).json()
        tappa = next(
            t for t in [p for p in scheda["periodi"] if p["attivo"]][0]["tappe"] if t["in_corso"]
        )
    assert tappa["fase"] == "RESPONSABILITA" and tappa["completata"]
    assert PeriodoBranca.objects.get().data_fine is None
    risposta = _post(
        capo,
        f"/api/v1/persone/{ragazza.pk}/progressione/impegni",
        {"testo": "Insegnare i nodi ai nuovi", "termine": (OGGI + timedelta(days=60)).isoformat()},
    )
    assert risposta.status_code == 201


def test_ingresso_in_eta_superiore(capo, ragazza):
    """§13: after Scoperta and Promessa, placed in the right tappa, no invented history."""
    scheda = _apri(capo, ragazza, OGGI - timedelta(days=120))
    scoperta = _tappa_in_corso(scheda)
    periodo_id = scheda["periodi"][0]["id"]
    url = f"/api/v1/progressione/tappe/{scoperta['id']}/colloca"
    dati = {**_giorno(10), "fase": "RESPONSABILITA", "motivazione": "Entrata a 15 anni"}
    risposta = _post(capo, url, dati)
    assert "Promessa" in risposta.json()["detail"]
    _post(capo, f"/api/v1/progressione/periodi/{periodo_id}/promessa", _giorno(60))
    scheda = _post(capo, url, dati).json()
    tappe = scheda["periodi"][0]["tappe"]
    assert [t["fase"] for t in tappe] == ["SCOPERTA", "RESPONSABILITA"]
    assert tappe[1]["collocamento"] and tappe[0]["completata"] is None


def test_tappa_importata_con_il_solo_anno(capo, ragazza):
    """§19.3: precision declared, no fake exact date (DEC-70)."""
    anno = OGGI.year - 2
    scheda = _apri(capo, ragazza, date(anno, 1, 1), precisione="ANNO")
    inizio = scheda["periodi"][0]["inizio"]
    assert inizio == {"data": f"{anno}-01-01", "precisione": "ANNO"}
    # A date sent with a day under "year" precision is stored as the year only.
    periodo_id = scheda["periodi"][0]["id"]
    scheda = _post(
        capo,
        f"/api/v1/progressione/periodi/{periodo_id}/promessa",
        {"data": f"{anno}-11-15", "precisione": "ANNO"},
    ).json()
    assert scheda["periodi"][0]["promessa"] == {"data": f"{anno}-01-01", "precisione": "ANNO"}


def test_rettifica_tracciata_e_niente_revoca(capo, ragazza):
    """§19.3: the correction of a date updates the history and keeps the audit; the
    Promessa is never withdrawn (V20)."""
    scheda = _apri(capo, ragazza)
    periodo_id = scheda["periodi"][0]["id"]
    url = f"/api/v1/progressione/periodi/{periodo_id}/promessa"
    _post(capo, url, _giorno(200))
    assert _put(capo, url, {**_giorno(201)}).status_code == 422  # reason required
    risposta = _put(capo, url, {**_giorno(201), "motivo": "Errore di trascrizione"})
    assert (
        risposta.json()["periodi"][0]["promessa"]["data"]
        == (OGGI - timedelta(days=201)).isoformat()
    )
    assert LogEntry.objects.filter(content_type__model="promessa").count() == 2
    assert _client(capo).delete(url).status_code == 405


def test_niente_transizioni_da_sole(capo, ragazza):
    """§19.3, V08: a birthday or a new scout year moves nobody."""
    _apri(capo, ragazza, OGGI - timedelta(days=1000))
    scheda = _client(capo).get(f"/api/v1/persone/{ragazza.pk}/progressione").json()
    assert _tappa_in_corso(scheda)["fase"] == "SCOPERTA"


# --- Impegni and mete ----------------------------------------------------------------------


def test_impegni_senza_meta_e_ciclo_completo(capo, ragazza, csq):
    """§13: impegni without a meta; the six states (DEC-59); the CSQ proposes, the staff
    validates with date and place (DEC-60, DEC-172)."""
    _apri(capo, ragazza)
    scheda = _post(
        ragazza,
        f"/api/v1/persone/{ragazza.pk}/progressione/impegni",
        {"testo": "Imparare il nodo savoia"},
    ).json()
    (impegno,) = scheda["impegni"]
    assert impegno["stato"] == "BOZZA" and impegno["proposto_dal_ragazzo"]
    url = f"/api/v1/progressione/impegni/{impegno['id']}"
    # The ragazzo cannot agree it; an agreed impegno needs a deadline.
    assert _post(ragazza, f"{url}/concorda").status_code == 403
    assert "entro quando" in _post(capo, f"{url}/concorda").json()["detail"]
    _put(
        ragazza,
        url,
        {
            "testo": "Imparare il nodo savoia e il parlato",
            "termine": (OGGI + timedelta(days=30)).isoformat(),
        },
    )
    assert _post(capo, f"{url}/concorda").status_code == 200
    # After the agreement only the staff rewords it.
    assert _put(ragazza, url, {"testo": "Altro"}).status_code == 403
    _post(capo, f"{url}/avvia")
    assert _post(csq, f"{url}/proponi_verifica").status_code == 200
    risposta = _post(capo, f"{url}/convalida", {"sede": "ALTRO"})
    assert "Scrivi dove" in risposta.json()["detail"]
    scheda = _post(capo, f"{url}/convalida", {"sede": "CONSIGLIO_SQ"}).json()
    (impegno,) = scheda["impegni"]
    assert impegno["stato"] == "CONCLUSO" and impegno["sede_nome"] == "Consiglio di squadriglia"
    assert impegno["revisioni"][0]["testo"] == "Imparare il nodo savoia"
    assert Impegno.objects.get().verificato_da == capo.utente
    # A step already applied (a replay from the offline queue) is answered as done.
    assert _post(capo, f"{url}/convalida", {"sede": "CONSIGLIO_SQ"}).status_code == 200
    # A concluded impegno is not reopened.
    assert _post(capo, f"{url}/prosegui").status_code == 400


def test_un_impegno_inviato_due_volte_offline(capo, ragazza):
    """§19.3, DEC-96: the same Idempotency-Key creates it once."""
    _apri(capo, ragazza)
    chiave = str(uuid.uuid4())
    for _ in range(2):
        risposta = _post(
            capo,
            f"/api/v1/persone/{ragazza.pk}/progressione/impegni",
            {"testo": "Fare la cucina al campo"},
            headers={"Idempotency-Key": chiave},
        )
        assert risposta.status_code == 201
    assert Impegno.objects.count() == 1


def test_meta_riservata(capo, ragazza, genitore, csq):
    """DEC-173: the CSQ does not see a private meta, nor its link from an impegno."""
    _apri(capo, ragazza)
    scheda = _post(
        capo,
        f"/api/v1/persone/{ragazza.pk}/progressione/mete",
        {"testo": "Parlare di più con il papà", "riservata": True},
    ).json()
    meta_id = scheda["mete"][0]["id"]
    _post(
        capo,
        f"/api/v1/persone/{ragazza.pk}/progressione/impegni",
        {"testo": "Cena insieme ogni settimana", "mete": [meta_id]},
    )
    per_il_csq = _client(csq).get(f"/api/v1/persone/{ragazza.pk}/progressione").json()
    assert per_il_csq["mete"] == [] and per_il_csq["impegni"][0]["mete"] == []
    assert _post(csq, f"/api/v1/progressione/mete/{meta_id}/proponi_verifica").status_code == 404
    per_il_genitore = _client(genitore).get(f"/api/v1/persone/{ragazza.pk}/progressione").json()
    assert per_il_genitore["mete"][0]["riservata"]
    assert Obiettivo.objects.get().stato == Stato.BOZZA


def test_interrompere_richiede_il_motivo(capo, ragazza):
    _apri(capo, ragazza)
    scheda = _post(
        capo, f"/api/v1/persone/{ragazza.pk}/progressione/impegni", {"testo": "Fare il diario"}
    ).json()
    url = f"/api/v1/progressione/impegni/{scheda['impegni'][0]['id']}/interrompi"
    assert _post(capo, url).status_code == 400
    assert (
        _post(capo, url, {"motivo": "Cambiato interesse"}).json()["impegni"][0]["stato"]
        == "INTERROTTO"
    )


# --- The reparto at a glance ---------------------------------------------------------------


def test_vista_del_reparto(capo, altro_capo, ragazza, csq, reparto):
    _apri(capo, ragazza)
    scheda = _post(
        capo, f"/api/v1/persone/{ragazza.pk}/progressione/impegni", {"testo": "Fare il diario"}
    ).json()
    assert scheda["impegni"]
    dati = _client(altro_capo).get(f"/api/v1/unita/{reparto.pk}/progressione").json()
    righe = {r["persona_id"]: r for r in dati["ragazzi"]}
    assert righe[ragazza.pk]["tappa"] == "Scoperta" and righe[ragazza.pk]["bozze"] == 1
    assert righe[csq.pk]["sentiero_aperto"] is False
    assert dati["puo_gestire"] is False  # another capo sees, the staff writes
    assert _client(csq).get(f"/api/v1/unita/{reparto.pk}/progressione").status_code == 403
