"""The patrol roles (DEC-321): who assigns them, who sees them, when they end."""

import pytest
from django.test import Client

from apps.anagrafica.models import AppartenenzaSquadriglia
from apps.organizzazione import servizi
from apps.organizzazione.models import Incarico, RuoloIncarico, Squadriglia
from apps.permessi import policy
from tests.conftest import INIZIO_ANNO, crea_capo

R = RuoloIncarico


def _client(chi) -> Client:
    client = Client()
    client.force_login(chi.utente)
    return client


def _nomina(chi, persona, ruolo, squadriglia):
    return _client(chi).post(
        "/api/v1/incarichi",
        {"persona_id": persona.pk, "ruolo": ruolo, "squadriglia_id": squadriglia.pk},
        content_type="application/json",
    )


def _attivi(persona) -> set[str]:
    return set(Incarico.objects.attivi().filter(persona=persona).values_list("ruolo", flat=True))


@pytest.fixture
def staff(reparto, coca):
    persona = crea_capo("Elena", "Staff", "staff-sq@example.invalid")
    Incarico.objects.create(persona=persona, ruolo=R.STAFF, unita=reparto, data_inizio=INIZIO_ANNO)
    return persona


@pytest.fixture
def altra_squadriglia(reparto) -> Squadriglia:
    return Squadriglia.objects.create(unita=reparto, nome="Volpi", sesso="F")


def test_chi_assegna(staff, capo, capogruppo, csq, ragazza, genitore, estraneo, squadriglia):
    for chi in (staff, capo, csq):
        assert policy.puo_nominare(chi.utente, R.CRONISTA, squadriglia=squadriglia)
    # A capogruppo only as part of the reparto's staff.
    for chi in (capogruppo, ragazza, genitore, estraneo):
        assert not policy.puo_nominare(chi.utente, R.CRONISTA, squadriglia=squadriglia)
    Incarico.objects.create(
        persona=capogruppo, ruolo=R.STAFF, unita=squadriglia.unita, data_inizio=INIZIO_ANNO
    )
    assert policy.puo_nominare(capogruppo.utente, R.CRONISTA, squadriglia=squadriglia)
    # The CSQ does not appoint the guides.
    assert not policy.puo_nominare(csq.utente, R.VCSQ, squadriglia=squadriglia)


def test_il_vice_non_assegna(staff, ragazza, squadriglia):
    Incarico.objects.create(
        persona=ragazza, ruolo=R.VCSQ, squadriglia=squadriglia, data_inizio=INIZIO_ANNO
    )
    assert not policy.puo_nominare(ragazza.utente, R.CRONISTA, squadriglia=squadriglia)


def test_csq_di_altra_squadriglia_non_assegna(csq, altra_squadriglia):
    assert not policy.puo_nominare(csq.utente, R.CRONISTA, squadriglia=altra_squadriglia)


def test_chi_vede(
    capo, capogruppo, csq, ragazza, genitore, estraneo, squadriglia, altra_squadriglia
):
    for chi in (capo, capogruppo, csq, ragazza, genitore):
        assert policy.puo_vedere_incarichi_squadriglia(chi.utente, squadriglia)
    assert not policy.puo_vedere_incarichi_squadriglia(estraneo.utente, squadriglia)
    # Not the other patrols of the reparto.
    for chi in (csq, ragazza, genitore):
        assert not policy.puo_vedere_incarichi_squadriglia(chi.utente, altra_squadriglia)


def test_csq_assegna_piu_incarichi_e_piu_persone(csq, ragazza, squadriglia):
    assert _nomina(csq, ragazza, "CRONISTA", squadriglia).status_code == 201
    assert _nomina(csq, ragazza, "MAGAZZINIERE", squadriglia).status_code == 201
    # A role has no limit of holders, and the CSQ may hold one too.
    assert _nomina(csq, csq, "CRONISTA", squadriglia).status_code == 201
    assert _attivi(ragazza) == {"CRONISTA", "MAGAZZINIERE"}
    # Twice the same: refused.
    assert _nomina(csq, ragazza, "CRONISTA", squadriglia).status_code == 400


def test_solo_ai_membri_della_squadriglia(csq, altra_squadriglia, squadriglia, reparto):
    from tests.conftest import crea_persona, nato_anni_fa

    fuori = crea_persona("Pino", "Fuori", data_nascita=nato_anni_fa(14))
    assert _nomina(csq, fuori, "CRONISTA", squadriglia).status_code == 400


def test_chiude_chi_lo_ha_assegnato(csq, ragazza, squadriglia, estraneo):
    assert _nomina(csq, ragazza, "CICALA", squadriglia).status_code == 201
    incarico = Incarico.objects.get(persona=ragazza, ruolo=R.CICALA)
    url = f"/api/v1/incarichi/{incarico.pk}/termina"
    assert _client(ragazza).post(url, {}, content_type="application/json").status_code == 403
    assert _client(csq).post(url, {}, content_type="application/json").status_code == 200
    assert "CICALA" not in _attivi(ragazza)


def test_api_lettura(csq, ragazza, genitore, estraneo, squadriglia):
    assert _nomina(csq, ragazza, "INFERMIERE", squadriglia).status_code == 201
    url = f"/api/v1/squadriglie/{squadriglia.pk}/incarichi"
    del_capo = _client(csq).get(url).json()
    # The guides first, whatever the alphabet says.
    assert [i["ruolo_nome"] for i in del_capo["incarichi"]] == ["Capo squadriglia", "Infermiere"]
    assert "CRONISTA" in {n["valore"] for n in del_capo["nomina"]}
    assert "CSQ" not in {n["valore"] for n in del_capo["nomina"]}
    # Read only for a member and for the parents.
    assert _client(ragazza).get(url).json()["nomina"] == []
    assert _client(genitore).get(url).json()["nomina"] == []
    dal_figlio = _client(genitore).get(f"/api/v1/persone/{ragazza.pk}/incarichi-squadriglia")
    assert dal_figlio.status_code == 200
    assert dal_figlio.json()["nome"] == squadriglia.nome
    assert _client(estraneo).get(url).status_code == 404
    assert (
        _client(estraneo).get(f"/api/v1/persone/{ragazza.pk}/incarichi-squadriglia").status_code
        == 404
    )


def test_nessun_permesso_dato_dall_incarico(csq, ragazza, squadriglia):
    """DEC-321: the infermiere sees no health data of the others."""
    assert _nomina(csq, ragazza, "INFERMIERE", squadriglia).status_code == 201
    risposta = _client(ragazza).get(f"/api/v1/persone/{csq.pk}/sanitarie")
    assert risposta.status_code in (403, 404)
    assert not policy.squadriglie_guidate(ragazza.utente).exists()


def test_cambiare_squadriglia_chiude_gli_incarichi(
    staff, csq, ragazza, squadriglia, altra_squadriglia
):
    assert _nomina(staff, ragazza, "CRONISTA", squadriglia).status_code == 201
    url = f"/api/v1/squadriglie/{altra_squadriglia.pk}/membri"
    risposta = _client(staff).post(url, {"persona_id": ragazza.pk}, content_type="application/json")
    assert risposta.status_code == 201, risposta.content
    assert _attivi(ragazza) == set()
    # The guides still close their role by hand first.
    url = f"/api/v1/squadriglie/{altra_squadriglia.pk}/membri"
    bloccata = _client(staff).post(url, {"persona_id": csq.pk}, content_type="application/json")
    assert bloccata.status_code == 400


def test_togliere_dalla_squadriglia_chiude_gli_incarichi(staff, ragazza, squadriglia):
    assert _nomina(staff, ragazza, "MERCURIO", squadriglia).status_code == 201
    membro = AppartenenzaSquadriglia.objects.attive().get(persona=ragazza)
    url = f"/api/v1/membri-squadriglia/{membro.pk}/termina"
    assert _client(staff).post(url).status_code == 200
    assert _attivi(ragazza) == set()


def test_uscire_dal_reparto_chiude_gli_incarichi(staff, ragazza, squadriglia, reparto):
    from django.utils import timezone

    assert _nomina(staff, ragazza, "LITURGISTA", squadriglia).status_code == 201
    chiusi = servizi.esci_dal_reparto(ragazza, reparto, timezone.localdate())
    assert any("Liturgista" in c for c in chiusi)
    assert _attivi(ragazza) == set()
