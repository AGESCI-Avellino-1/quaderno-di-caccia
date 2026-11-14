"""Two linked reparti on one page: patrols of both, managed by their one staff (DEC-405)."""

import pytest
from django.test import Client

from apps.anagrafica.models import Appartenenza, RuoloAppartenenza
from apps.organizzazione import servizi
from apps.organizzazione.models import Composizione, Squadriglia, TipoUnita, Unita
from tests.conftest import INIZIO_ANNO, crea_persona, nato_anni_fa

pytestmark = pytest.mark.django_db


def _client(chi) -> Client:
    client = Client()
    client.force_login(chi.utente)
    return client


@pytest.fixture
def parallelo(gruppo, reparto) -> Unita:
    altro = Unita.objects.create(
        gruppo=gruppo, nome="Parallelo", tipo=TipoUnita.REPARTO, composizione=Composizione.MISTA
    )
    servizi.collega(reparto, altro, "Reparto parallelo")
    return altro


@pytest.fixture
def lupi(parallelo) -> Squadriglia:
    return Squadriglia.objects.create(unita=parallelo, nome="Lupi", sesso="M")


@pytest.fixture
def marco(parallelo):
    persona = crea_persona("Marco", "Parallelo", data_nascita=nato_anni_fa(12))
    Appartenenza.objects.create(
        persona=persona, unita=parallelo, ruolo=RuoloAppartenenza.RAGAZZO, data_inizio=INIZIO_ANNO
    )
    return persona


def test_le_squadriglie_di_tutti_e_due(capo, reparto, parallelo, squadriglia, lupi, marco):
    for unita in (reparto, parallelo):
        dettaglio = _client(capo).get(f"/api/v1/unita/{unita.pk}").json()
        nomi = {(s["nome"], s["unita_id"]) for s in dettaglio["squadriglie"]}
        assert nomi == {("Aquile", reparto.pk), ("Lupi", parallelo.pk)}
        assert {s["unita_nome"] for s in dettaglio["squadriglie"]} == {
            str(reparto),
            str(parallelo),
        }
        assert [r["id"] for r in dettaglio["reparti"]] == [unita.pk, unita.collegata_a_id]
        senza = {(p["id"], p["reparto_id"]) for p in dettaglio["senza_squadriglia"]}
        assert (marco.pk, parallelo.pk) in senza
        assert dettaglio["puo_gestire_squadriglie"] is True


def test_lo_staff_comune_compone_anche_l_altro(capo, parallelo, lupi, marco):
    # The capo serves the first reparto only: the linked one shares its staff.
    risposta = _client(capo).post(
        f"/api/v1/squadriglie/{lupi.pk}/membri",
        {"persona_id": marco.pk},
        content_type="application/json",
    )
    assert risposta.status_code == 201, risposta.content


def test_un_ragazzo_resta_nelle_squadriglie_del_suo_reparto(capo, squadriglia, marco):
    risposta = _client(capo).post(
        f"/api/v1/squadriglie/{squadriglia.pk}/membri",
        {"persona_id": marco.pk},
        content_type="application/json",
    )
    assert risposta.status_code == 400


def test_un_reparto_solo_non_cambia(capo, reparto, squadriglia):
    dettaglio = _client(capo).get(f"/api/v1/unita/{reparto.pk}").json()
    assert dettaglio["reparti"] == []
    assert [s["unita_nome"] for s in dettaglio["squadriglie"]] == [""]


def test_un_branco_collegato_non_porta_squadriglie(capo, gruppo, reparto, squadriglia):
    branco = Unita.objects.create(
        gruppo=gruppo, nome="Branco", tipo=TipoUnita.BRANCO, composizione=Composizione.MISTA
    )
    servizi.collega(reparto, branco, "")
    dettaglio = _client(capo).get(f"/api/v1/unita/{reparto.pk}").json()
    assert [s["nome"] for s in dettaglio["squadriglie"]] == ["Aquile"]
    assert _client(capo).get(f"/api/v1/unita/{branco.pk}").json()["squadriglie"] == []


@pytest.mark.parametrize("ruolo", ["csq", "ragazza", "genitore", "estraneo"])
def test_gli_altri_non_compongono(request, ruolo, lupi, marco):
    risposta = _client(request.getfixturevalue(ruolo)).post(
        f"/api/v1/squadriglie/{lupi.pk}/membri",
        {"persona_id": marco.pk},
        content_type="application/json",
    )
    assert risposta.status_code == 403


def test_stesso_nome_distinti_dal_codice(capo, gruppo, reparto):
    # Parallel reparti may share a name: the code tells them apart (DEC-408).
    reparto.nome, reparto.codice_unita, reparto.progressivo = "Millenium", "M", 1
    reparto.save()
    gemello = Unita.objects.create(
        gruppo=gruppo,
        nome="Millenium",
        tipo=TipoUnita.REPARTO,
        composizione=Composizione.MISTA,
        codice_unita="N",
        progressivo=1,
    )
    servizi.collega(reparto, gemello, "")
    dettaglio = _client(capo).get(f"/api/v1/unita/{reparto.pk}").json()
    assert [r["nome"] for r in dettaglio["reparti"]] == [
        "Reparto Millenium (M1)",
        "Reparto Millenium (N1)",
    ]
