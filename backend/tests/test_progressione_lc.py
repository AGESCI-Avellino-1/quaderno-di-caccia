"""L/C: pista and sentiero, stagione di caccia o di volo, prede and voli, momenti,
specialità L/C, Consiglio degli Anziani, Piccole Orme (DEC-66, DEC-68, DEC-182…DEC-185),
with the cases of the PP specification v1.0 (§4, §13, §17.5; V03…V05, V11)."""

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest
from django.test import Client

from apps.anagrafica.models import Appartenenza, RelazioneTutela, RuoloAppartenenza
from apps.buonacaccia import servizi as bc
from apps.buonacaccia.models import EventoBuonaCaccia, StatoIscrizione
from apps.eventi.models import Evento, TipoEvento
from apps.organizzazione.models import (
    Composizione,
    Incarico,
    RuoloIncarico,
    TipoUnita,
    Unita,
)
from apps.progressione import servizi
from apps.progressione.models import PeriodoBranca, Stagione, Tappa
from tests.conftest import INIZIO_ANNO, crea_capo, crea_persona, nato_anni_fa

pytestmark = pytest.mark.django_db

OGGI = date.today()


def _client(chi) -> Client:
    client = Client()
    client.force_login(chi.utente)
    return client


def _post(chi, url, dati=None):
    return _client(chi).post(url, dati or {}, content_type="application/json")


def _giorno(giorno=OGGI, **altro):
    return {"data": giorno.isoformat(), "precisione": "GIORNO", **altro}


@pytest.fixture
def branco(gruppo):
    return Unita.objects.create(
        gruppo=gruppo, nome="Seeonee", tipo=TipoUnita.BRANCO, composizione=Composizione.MISTA
    )


@pytest.fixture
def akela(coca, branco):
    persona = crea_capo("Akela", "Branco", "akela@example.invalid")
    Incarico.objects.create(
        persona=persona, ruolo=RuoloIncarico.CAPO_UNITA, unita=branco, data_inizio=INIZIO_ANNO
    )
    return persona


def _bambino(unita, nome, sesso, login=None):
    persona = crea_persona(nome, "Bambino", login, data_nascita=nato_anni_fa(9), sesso=sesso)
    Appartenenza.objects.create(
        persona=persona, unita=unita, ruolo=RuoloAppartenenza.RAGAZZO, data_inizio=INIZIO_ANNO
    )
    return persona


@pytest.fixture
def lupetto(branco):
    return _bambino(branco, "Mowgli", "M")


@pytest.fixture
def mamma(lupetto):
    persona = crea_persona("Messua", "Bambino", "mamma@example.invalid")
    RelazioneTutela.objects.create(tutore=persona, minore=lupetto, tipo="GENITORE")
    return persona


@pytest.fixture
def pista(akela, lupetto):
    risposta = _post(
        akela,
        f"/api/v1/persone/{lupetto.pk}/progressione/sentiero",
        _giorno(OGGI - timedelta(days=200)),
    )
    assert risposta.status_code == 201, risposta.content
    return PeriodoBranca.objects.get(persona=lupetto)


@pytest.fixture
def stagione(akela, branco):
    dati = _post(
        akela,
        f"/api/v1/unita/{branco.pk}/stagioni",
        {
            "nome": "Stagione di caccia",
            "inizio_previsto": (OGGI - timedelta(days=60)).isoformat(),
            "fine_prevista": (OGGI + timedelta(days=40)).isoformat(),
        },
    ).json()
    stagione = Stagione.objects.get(pk=dati["stagioni"][0]["id"])
    _post(
        akela,
        f"/api/v1/stagioni/{stagione.pk}/lancia",
        {"il": (OGGI - timedelta(days=50)).isoformat()},
    )
    stagione.refresh_from_db()
    return stagione


def _preda(akela, lupetto, stagione, testo="Imparare il nodo piano"):
    dati = _post(
        akela,
        f"/api/v1/persone/{lupetto.pk}/progressione/impegni",
        {"testo": testo, "stagione_id": stagione.pk},
    ).json()
    return next(i for i in dati["impegni"] if i["testo"] == testo)


def _conquista(akela, preda):
    for azione in ("concorda", "avvia", "proponi_verifica"):
        assert (
            _post(akela, f"/api/v1/progressione/impegni/{preda['id']}/{azione}").status_code == 200
        )
    risposta = _post(
        akela,
        f"/api/v1/progressione/impegni/{preda['id']}/convalida",
        {"il": OGGI.isoformat(), "sede": "ANZIANI"},
    )
    assert risposta.status_code == 200, risposta.content


def test_la_pista_si_apre_e_l_ambiente_e_la_giungla(akela, lupetto, pista):
    assert pista.branca == "LC"
    dati = _client(akela).get(f"/api/v1/persone/{lupetto.pk}/progressione").json()
    assert dati["ambiente"] == "GIUNGLA"


def test_l_ambiente_e_dell_unita_mai_del_bambino(gruppo):
    """Giungla or bosco by the unit's setting, for boys and girls alike (DEC-185,
    DEC-225); generic names while the setting is not known."""
    from apps.organizzazione.models import Ambiente
    from apps.progressione.api import ambiente

    misto = Unita.objects.create(
        gruppo=gruppo, nome="Misto", tipo=TipoUnita.BRANCO_CERCHIO, composizione=Composizione.MISTA
    )
    lia, teo = _bambino(misto, "Lia", "F"), _bambino(misto, "Teo", "M")
    assert ambiente(lia) is None and ambiente(teo) is None
    misto.ambiente = Ambiente.GIUNGLA
    misto.save()
    assert ambiente(lia) == "GIUNGLA" and ambiente(teo) == "GIUNGLA"
    femminile = Unita.objects.create(
        gruppo=gruppo,
        nome="Femminile",
        tipo=TipoUnita.BRANCO_CERCHIO,
        composizione=Composizione.FEMMINILE,
        ambiente=Ambiente.GIUNGLA,
    )
    assert ambiente(_bambino(femminile, "Ada", "F")) == "GIUNGLA"


def test_un_impegno_prima_della_promessa(akela, lupetto, pista, stagione):
    """A coccinella takes an impegno before the Promessa: the progression has begun."""
    preda = _preda(akela, lupetto, stagione)
    assert preda["stagione"] == "Stagione di caccia"
    # Agreed with the season as time reference, no deadline needed (spec §16.4).
    assert _post(akela, f"/api/v1/progressione/impegni/{preda['id']}/concorda").status_code == 200
    # No mete in L/C.
    risposta = _post(akela, f"/api/v1/persone/{lupetto.pk}/progressione/mete", {"testo": "x"})
    assert risposta.status_code == 400


def test_due_prede_o_una(akela, branco, lupetto, pista, stagione):
    """One child agrees two prede, another one: both are valid (V03)."""
    altro = _bambino(branco, "Fratellino", "M")
    _post(akela, f"/api/v1/persone/{altro.pk}/progressione/sentiero", _giorno())
    _preda(akela, lupetto, stagione, "Uno")
    _preda(akela, lupetto, stagione, "Due")
    _preda(akela, altro, stagione, "Una")
    dati = _client(akela).get(f"/api/v1/unita/{branco.pk}/stagioni").json()
    assert dati["stagioni"][0]["prede"] == 3


def test_la_fine_della_stagione_non_conquista_nulla(akela, branco, lupetto, pista, stagione):
    """A preda to reformulate at the end of the season: kept, never conquered (V04)."""
    preda = _preda(akela, lupetto, stagione)
    dati = _post(akela, f"/api/v1/stagioni/{stagione.pk}/chiudi").json()
    chiusa = dati["stagioni"][0]
    assert chiusa["stato"] == "CHIUSA" and chiusa["conquistate"] == 0
    assert chiusa["da_rileggere"] == ["Bambino Mowgli: Imparare il nodo piano"]
    dati = _client(akela).get(f"/api/v1/persone/{lupetto.pk}/progressione").json()
    assert dati["impegni"][0]["stato"] == "BOZZA"
    # A closed season takes no new prede.
    risposta = _post(
        akela,
        f"/api/v1/persone/{lupetto.pk}/progressione/impegni",
        {"testo": "Nuova", "stagione_id": stagione.pk},
    )
    assert risposta.status_code == 400
    assert preda["id"]


def test_stagioni_una_aperta_e_annullamento(akela, branco, stagione):
    url = f"/api/v1/unita/{branco.pk}/stagioni"
    dati = {
        "nome": "Stagione di primavera",
        "inizio_previsto": OGGI.isoformat(),
        "fine_prevista": (OGGI + timedelta(days=100)).isoformat(),
    }
    nuova = _post(akela, url, dati).json()["stagioni"]
    seconda = next(s for s in nuova if s["nome"] == "Stagione di primavera")
    assert _post(akela, f"/api/v1/stagioni/{seconda['id']}/lancia").status_code == 400
    assert _post(akela, f"/api/v1/stagioni/{stagione.pk}/annulla").status_code == 400
    assert _post(akela, f"/api/v1/stagioni/{seconda['id']}/annulla").status_code == 200
    assert _post(akela, url, {**dati, "fine_prevista": OGGI.isoformat()}).status_code == 400


def test_chi_vede_e_chi_gestisce_le_stagioni(
    akela, branco, capo, capogruppo, csq, ragazza, genitore, estraneo, lupetto, mamma
):
    url = f"/api/v1/unita/{branco.pk}/stagioni"
    dati = {
        "nome": "Stagione",
        "inizio_previsto": OGGI.isoformat(),
        "fine_prevista": (OGGI + timedelta(days=100)).isoformat(),
    }
    for chi in (capo, capogruppo):
        assert _client(chi).get(url).status_code == 200
        assert _post(chi, url, dati).status_code == 403
    for chi in (csq, ragazza, genitore, estraneo, mamma):
        assert _client(chi).get(url).status_code == 403
    assert _post(akela, url, dati).status_code == 201


def test_il_momento_si_riconosce_dopo_una_conquista(akela, lupetto, pista, stagione):
    tappa = pista.tappe.get()
    url = f"/api/v1/progressione/tappe/{tappa.pk}/riconosci"
    risposta = _post(akela, url, _giorno())
    assert risposta.status_code == 400 and "preda" in risposta.json()["detail"]
    # The badge only after the recognition (V05).
    assert (
        _post(akela, f"/api/v1/progressione/tappe/{tappa.pk}/distintivo", _giorno()).status_code
        == 400
    )
    _conquista(akela, _preda(akela, lupetto, stagione))
    assert _post(akela, url, _giorno()).status_code == 200
    tappa.refresh_from_db()
    assert tappa.completata_il == OGGI and tappa.sede_completamento == ""
    assert (
        _post(akela, f"/api/v1/progressione/tappe/{tappa.pk}/distintivo", _giorno()).status_code
        == 200
    )


def test_storia_di_chi_c_era_gia(akela, lupetto, pista):
    """Imported history may lack the conquests, when said so (V05)."""
    tappa = pista.tappe.get()
    risposta = _post(
        akela,
        f"/api/v1/progressione/tappe/{tappa.pk}/riconosci",
        _giorno(OGGI - timedelta(days=100), storico=True),
    )
    assert risposta.status_code == 200
    assert pista.tappe.count() == 2


def test_il_quarto_anno_continua_la_responsabilita(akela, lupetto, pista):
    """Four-year unit: Responsabilità goes on with other tools, no fourth phase (§13)."""
    for giorni in (150, 100, 50):
        tappa = Tappa.objects.get(periodo=pista, data_fine__isnull=True)
        _post(
            akela,
            f"/api/v1/progressione/tappe/{tappa.pk}/riconosci",
            _giorno(OGGI - timedelta(days=giorni), storico=True),
        )
    fasi = list(pista.tappe.order_by("data_inizio").values_list("fase", flat=True))
    assert fasi == ["SCOPERTA", "COMPETENZA", "RESPONSABILITA"]
    pista.refresh_from_db()
    assert pista.data_fine is None


def test_specialita_lc(akela, lupetto, pista):
    url = f"/api/v1/persone/{lupetto.pk}/progressione/competenze"
    assert _post(akela, url, {"tipo": "SPECIALITA", "codice": "EGSP001"}).status_code == 400
    dati = _post(akela, url, {"tipo": "SPECIALITA_LC", "codice": "LCSP001"}).json()
    voce = dati["competenze"][0]
    assert voce["nome"] == "Amico degli animali"
    for azione in ("avvia", "proponi_verifica"):
        _post(akela, f"/api/v1/competenze/{voce['id']}/{azione}")
    dati = _post(
        akela, f"/api/v1/competenze/{voce['id']}/riconosci", {"il": OGGI.isoformat()}
    ).json()
    assert dati["competenze"][0]["stato"] == "RICONOSCIUTO"
    from apps.progressione.models import PercorsoCompetenza

    assert PercorsoCompetenza.objects.get().sede == ""


def test_consiglio_degli_anziani(akela, branco, lupetto, capo, reparto, ragazza):
    url = "/api/v1/incarichi"
    dati = {"persona_id": lupetto.pk, "ruolo": "CONSIGLIO_ANZIANI", "unita_id": branco.pk}
    assert _post(capo, url, dati).status_code == 403
    assert _post(akela, url, {**dati, "persona_id": akela.pk}).status_code == 400
    assert _post(akela, url, dati).status_code == 201
    nomina = _client(akela).get(f"/api/v1/unita/{branco.pk}").json()["nomina"]
    assert "CONSIGLIO_ANZIANI" in [n["valore"] for n in nomina]
    # Not in a reparto.
    risposta = _post(capo, url, {**dati, "persona_id": ragazza.pk, "unita_id": reparto.pk})
    assert risposta.status_code in (400, 403)
    # Leaving the branco ends it.
    from apps.organizzazione.servizi import esci_dal_reparto

    esci_dal_reparto(lupetto, branco, OGGI + timedelta(days=1))
    assert Incarico.objects.get(ruolo="CONSIGLIO_ANZIANI").data_fine == OGGI + timedelta(days=1)


def _evento_po(akela, giorni=3):
    roma = ZoneInfo("Europe/Rome")
    inizio = OGGI + timedelta(days=30)
    evento = Evento(
        titolo="Piccole Orme di cucina",
        tipo=TipoEvento.CAMPO,
        inizio=datetime.combine(inizio, time(9), roma),
        fine=datetime.combine(inizio + timedelta(days=giorni - 1), time(17), roma),
    )
    return bc.salva_evento(evento, EventoBuonaCaccia(piccole_orme=True), akela.utente)


def test_piccole_orme(akela, lupetto, pista):
    """Once only, in Responsabilità, at least three days: warnings, never a block (V11)."""
    prima = _evento_po(akela)
    iscrizione = bc.iscrivi(
        prima, lupetto, akela.utente, iscritto_il=OGGI, stato=StatoIscrizione.AMMESSO
    )
    avvisi = bc.avvisi_piccole_orme(iscrizione)
    assert len(avvisi) == 1 and "Responsabilità" in avvisi[0]
    seconda = _evento_po(akela, giorni=2)
    altra = bc.iscrivi(
        seconda, lupetto, akela.utente, iscritto_il=OGGI, stato=StatoIscrizione.AMMESSO
    )
    avvisi = bc.avvisi_piccole_orme(altra)
    assert any("una sola volta" in a for a in avvisi)
    assert any("tre giorni" in a for a in avvisi)
    dati = _client(akela).get(f"/api/v1/persone/{lupetto.pk}/progressione").json()
    assert len(dati["piccole_orme"]) == 2
    assert servizi.periodo_attivo(lupetto) == pista
