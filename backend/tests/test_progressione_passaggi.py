"""Passaggi tra branche (DEC-69, DEC-174…DEC-177), with the cases of the PP specification
v1.0 (§7, §17.9, §19.3; DEC-73)."""

from datetime import date, timedelta

import pytest
from django.test import Client

from apps.anagrafica.models import Appartenenza, AppartenenzaSquadriglia
from apps.core.models import FonteDato
from apps.organizzazione.models import Composizione, TipoUnita, Unita
from apps.progressione import servizi
from apps.progressione.models import (
    PercorsoCompetenza,
    PeriodoBranca,
    StatoPassaggio,
    Tappa,
)
from tests.conftest import crea_capo

pytestmark = pytest.mark.django_db

OGGI = date.today()


def _client(chi) -> Client:
    client = Client()
    client.force_login(chi.utente)
    return client


def _post(chi, url, dati=None):
    return _client(chi).post(url, dati or {}, content_type="application/json")


@pytest.fixture
def clan(gruppo):
    return Unita.objects.create(
        gruppo=gruppo, nome="Hirpinia", tipo=TipoUnita.CLAN_FUOCO, composizione=Composizione.MISTA
    )


@pytest.fixture
def sentiero(capo, ragazza):
    _post(
        capo,
        f"/api/v1/persone/{ragazza.pk}/progressione/sentiero",
        {"data": (OGGI - timedelta(days=700)).isoformat(), "precisione": "GIORNO"},
    )
    _post(
        capo,
        f"/api/v1/persone/{ragazza.pk}/progressione/competenze",
        {"tipo": "SPECIALITA", "codice": "EGSP001"},
    )
    return ragazza


def _prepara(chi, reparto, destinazione, ragazza, giorno=OGGI, **altro):
    return _post(
        chi,
        f"/api/v1/unita/{reparto.pk}/passaggi",
        {
            "unita_destinazione_id": destinazione.pk,
            "data": giorno.isoformat(),
            "persone": [{"persona_id": ragazza.pk, "sintesi": "Brava a cucinare, timida"}],
            **altro,
        },
    )


def test_chi_prepara_e_dove_si_va(capo, capogruppo, reparto, clan, sentiero, coca):
    altro = crea_capo("Carlo", "Altro", "altro@example.invalid")
    assert _prepara(altro, reparto, clan, sentiero).status_code == 403
    assert _client(sentiero).get(f"/api/v1/unita/{reparto.pk}/passaggi").status_code == 403
    # Only to the next branch.
    risposta = _prepara(capo, reparto, reparto, sentiero)
    assert "branca successiva" in risposta.json()["detail"]
    assert _prepara(capogruppo, reparto, clan, sentiero).status_code == 201
    dati = _client(capo).get(f"/api/v1/unita/{reparto.pk}/passaggi").json()
    assert [d["id"] for d in dati["destinazioni"]] == [clan.pk]
    assert dati["in_uscita"][0]["persone"][0]["sintesi"] == "Brava a cucinare, timida"


def test_eseguito_chiude_e_apre_senza_convertire(capo, reparto, clan, sentiero, squadriglia):
    """DEC-69, DEC-175, DEC-176: periods and unit change together; the specialità stays
    in the E/G period, nothing is converted."""
    passaggio = _prepara(capo, reparto, clan, sentiero).json()["in_uscita"][0]
    url = f"/api/v1/passaggi/{passaggio['id']}"
    assert _post(capo, f"{url}/esegui").json()["in_uscita"][0]["stato"] == "ESEGUITO"
    vecchio, nuovo = PeriodoBranca.objects.order_by("data_inizio")
    assert (vecchio.branca, vecchio.data_fine) == ("EG", OGGI)
    assert not Tappa.objects.filter(periodo=vecchio, data_fine__isnull=True).exists()
    assert (nuovo.branca, nuovo.data_fine) == ("RS", None)
    assert Tappa.objects.get(periodo=nuovo).fase == "SCOPERTA"
    assert PercorsoCompetenza.objects.get().periodo == vecchio
    # Unit assigned in the app; patrol membership closed.
    attiva = Appartenenza.objects.attive().get(persona=sentiero)
    assert (attiva.unita, attiva.fonte) == (clan, FonteDato.APP)
    assert not AppartenenzaSquadriglia.objects.attive().filter(persona=sentiero).exists()
    # The new capi read the summary in the new period.
    scheda = _client(capo).get(f"/api/v1/persone/{sentiero.pk}/progressione").json()
    attivo = next(p for p in scheda["periodi"] if p["attivo"])
    assert attivo["passaggio"]["sintesi"] == "Brava a cucinare, timida"
    # Twice: one effect; no longer cancellable or editable.
    assert _post(capo, f"{url}/esegui").status_code == 200
    assert PeriodoBranca.objects.count() == 2
    assert _post(capo, f"{url}/annulla", {"motivo": "Errore"}).status_code == 400


def test_non_prima_della_data_e_annullamento(capo, reparto, clan, sentiero):
    passaggio = _prepara(capo, reparto, clan, sentiero, OGGI + timedelta(days=10)).json()
    url = f"/api/v1/passaggi/{passaggio['in_uscita'][0]['id']}"
    assert "Si esegue dal" in _post(capo, f"{url}/esegui").json()["detail"]
    assert _post(capo, f"{url}/annulla", {"motivo": ""}).status_code == 400
    dati = _post(capo, f"{url}/annulla", {"motivo": "Rimandato all'anno prossimo"}).json()
    assert dati["in_uscita"][0]["stato"] == "ANNULLATO"
    assert PeriodoBranca.objects.get().data_fine is None
    assert Appartenenza.objects.attive().get(persona=sentiero).unita == reparto


def test_interrotto_a_meta_non_lascia_nulla_a_metà(capo, reparto, clan, sentiero, csq, monkeypatch):
    """§19.3: never an origin closed without its destination."""
    _post(
        capo,
        f"/api/v1/persone/{csq.pk}/progressione/sentiero",
        {"data": OGGI.isoformat(), "precisione": "GIORNO"},
    )
    risposta = _post(
        capo,
        f"/api/v1/unita/{reparto.pk}/passaggi",
        {
            "unita_destinazione_id": clan.pk,
            "data": OGGI.isoformat(),
            "persone": [{"persona_id": sentiero.pk}, {"persona_id": csq.pk}],
        },
    )
    passaggio_id = risposta.json()["in_uscita"][0]["id"]
    originale = servizi._apri_periodo
    chiamate = []

    def guasto(*args, **kwargs):
        chiamate.append(1)
        if len(chiamate) == 2:
            raise RuntimeError("caduta della connessione")
        return originale(*args, **kwargs)

    monkeypatch.setattr(servizi, "_apri_periodo", guasto)
    with pytest.raises(RuntimeError):
        _post(capo, f"/api/v1/passaggi/{passaggio_id}/esegui")
    assert PeriodoBranca.objects.filter(data_fine__isnull=True).count() == 2
    assert not PeriodoBranca.objects.filter(branca="RS").exists()
    from apps.progressione.models import Passaggio

    assert Passaggio.objects.get().stato == StatoPassaggio.PREPARATO


def test_da_lupetti_a_reparto(capo, capogruppo, reparto, gruppo):
    """L/C → E/G: the sentiero opens with the Scoperta, even without a L/C history."""
    from apps.anagrafica.models import RuoloAppartenenza
    from tests.conftest import INIZIO_ANNO, crea_persona, nato_anni_fa

    branco = Unita.objects.create(
        gruppo=gruppo, nome="Seeonee", tipo=TipoUnita.BRANCO, composizione=Composizione.MISTA
    )
    lupetto = crea_persona("Luca", "Lupetto", data_nascita=nato_anni_fa(11))
    Appartenenza.objects.create(
        persona=lupetto, unita=branco, ruolo=RuoloAppartenenza.RAGAZZO, data_inizio=INIZIO_ANNO
    )
    passaggio = _prepara(capogruppo, branco, reparto, lupetto).json()["in_uscita"][0]
    _post(capogruppo, f"/api/v1/passaggi/{passaggio['id']}/esegui")
    periodo = PeriodoBranca.objects.get(persona=lupetto)
    assert periodo.branca == "EG" and periodo.tappe.get().fase == "SCOPERTA"


# --- Correcting an executed passage (spec §17.9, §18.4; DEC-178) ----------------------------


def _eseguito(capo, reparto, clan, ragazza, giorno=OGGI):
    passaggio = _prepara(capo, reparto, clan, ragazza, giorno).json()["in_uscita"][0]
    _post(capo, f"/api/v1/passaggi/{passaggio['id']}/esegui")
    return passaggio["id"]


def test_annullare_l_esecuzione_rimette_tutto_com_era(capo, reparto, clan, sentiero, squadriglia):
    from auditlog.models import LogEntry

    prima_sq = AppartenenzaSquadriglia.objects.attive().get(persona=sentiero)
    passaggio_id = _eseguito(capo, reparto, clan, sentiero)
    url = f"/api/v1/passaggi/{passaggio_id}/annulla-esecuzione"
    assert _post(capo, url, {"motivo": ""}).status_code == 400
    dati = _post(capo, url, {"motivo": "Era la sorella"}).json()
    passaggio = dati["in_uscita"][0]
    assert passaggio["stato"] == "RETTIFICATO"
    assert passaggio["persone"][0]["motivo_rettifica"] == "Era la sorella"
    periodo = PeriodoBranca.objects.get()
    assert (periodo.branca, periodo.data_fine) == ("EG", None)
    assert Tappa.objects.filter(periodo=periodo, data_fine__isnull=True).count() == 1
    assert Appartenenza.objects.attive().get(persona=sentiero).unita == reparto
    assert AppartenenzaSquadriglia.objects.attive().get(persona=sentiero) == prima_sq
    # Traced: the removed R/S period is in the audit log.
    assert LogEntry.objects.filter(content_type__model="periodobranca", action=2).exists()
    # Done once only.
    assert _post(capo, url, {"motivo": "Ancora"}).status_code == 400


def test_annullare_per_uno_solo(capo, reparto, clan, sentiero, csq):
    _post(
        capo,
        f"/api/v1/persone/{csq.pk}/progressione/sentiero",
        {"data": OGGI.isoformat(), "precisione": "GIORNO"},
    )
    risposta = _post(
        capo,
        f"/api/v1/unita/{reparto.pk}/passaggi",
        {
            "unita_destinazione_id": clan.pk,
            "data": OGGI.isoformat(),
            "persone": [{"persona_id": sentiero.pk}, {"persona_id": csq.pk}],
        },
    )
    passaggio_id = risposta.json()["in_uscita"][0]["id"]
    _post(capo, f"/api/v1/passaggi/{passaggio_id}/esegui")
    dati = _post(
        capo,
        f"/api/v1/passaggi/{passaggio_id}/annulla-esecuzione",
        {"motivo": "Resta un altro anno", "persone": [csq.pk]},
    ).json()
    assert dati["in_uscita"][0]["stato"] == "ESEGUITO"
    assert Appartenenza.objects.attive().get(persona=csq).unita == reparto
    assert Appartenenza.objects.attive().get(persona=sentiero).unita == clan


def test_niente_rettifica_se_il_nuovo_staff_ha_scritto(capo, capogruppo, reparto, clan, sentiero):
    passaggio_id = _eseguito(capo, reparto, clan, sentiero)
    nuovo = PeriodoBranca.objects.get(data_fine__isnull=True)
    servizi.registra_promessa(nuovo, servizi.DataParziale.giorno(OGGI), capogruppo.utente)
    risposta = _post(
        capo, f"/api/v1/passaggi/{passaggio_id}/annulla-esecuzione", {"motivo": "Errore"}
    )
    assert risposta.status_code == 400 and "Promess" in risposta.json()["detail"]
    assert PeriodoBranca.objects.filter(data_fine__isnull=True).get() == nuovo


def test_niente_rettifica_dopo_un_importazione(capo, reparto, clan, sentiero):
    from django.utils import timezone

    from apps.importazione.models import ImportazioneBuonaStrada

    passaggio_id = _eseguito(capo, reparto, clan, sentiero)
    ImportazioneBuonaStrada.objects.create(
        nome_file="export.csv", sha256="x" * 64, applicata_il=timezone.now() + timedelta(seconds=1)
    )
    risposta = _post(
        capo, f"/api/v1/passaggi/{passaggio_id}/annulla-esecuzione", {"motivo": "Errore"}
    )
    assert "BuonaStrada" in risposta.json()["detail"]


def test_correggere_la_data(capo, reparto, clan, sentiero):
    passaggio_id = _eseguito(capo, reparto, clan, sentiero)
    giusta = OGGI - timedelta(days=3)
    url = f"/api/v1/passaggi/{passaggio_id}/correggi-data"
    assert _post(capo, url, {"data": giusta.isoformat(), "motivo": ""}).status_code == 400
    dati = _post(capo, url, {"data": giusta.isoformat(), "motivo": "Era sabato"}).json()
    assert dati["in_uscita"][0]["data"] == giusta.isoformat()
    vecchio, nuovo = PeriodoBranca.objects.order_by("data_inizio")
    assert vecchio.data_fine == giusta and nuovo.data_inizio == giusta
    assert Appartenenza.objects.get(persona=sentiero, unita=clan).data_inizio == giusta
    assert Appartenenza.objects.get(persona=sentiero, unita=reparto).data_fine == giusta
