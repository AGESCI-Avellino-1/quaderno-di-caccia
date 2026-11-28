"""Whose an entry of the book of ceremonies is (DEC-438): the group, the Co.Ca., one or more
units, the Alta Squadriglia or the Consiglio capi of a reparto, one or more patrols, the
Consiglio degli Anziani. It decides who writes it; the conditions decide who reads it."""

# The fixtures imported from test_cerimonie are named again as parameters.
# ruff: noqa: F811

import pytest

from apps.cerimonie.models import AmbitoVoce, VoceLibro
from apps.organizzazione.models import (
    Composizione,
    Incarico,
    RuoloIncarico,
    Squadriglia,
    TipoUnita,
    Unita,
)
from tests.conftest import INIZIO_ANNO, crea_capo
from tests.test_cerimonie import (  # noqa: F401 (fixtures)
    URL,
    _accendi,
    _client,
    _dati,
    _titoli,
    _voce,
    branco,
    lupetto,
)

pytestmark = pytest.mark.django_db


def _con(ambito: str, unita=(), squadriglie=(), **campi) -> dict:
    return _dati(
        ambito=ambito,
        unita_ids=[u.pk for u in unita],
        squadriglie_ids=[s.pk for s in squadriglie],
        **campi,
    )


@pytest.fixture
def staff_branco(branco, coca):
    capo = crea_capo("Akela", "Branco", "akela@example.invalid")
    Incarico.objects.create(
        persona=capo, ruolo=RuoloIncarico.CAPO_UNITA, unita=branco, data_inizio=INIZIO_ANNO
    )
    return capo


def test_voce_di_piu_unita(capo, staff_branco, capogruppo, reparto, branco):
    _accendi()
    # The reparto staff adds only its own units.
    risposta = _client(capo).post(URL, _con("UNITA", [reparto, branco]), "application/json")
    assert risposta.status_code == 403
    risposta = _client(capogruppo).post(
        URL, _con("UNITA", [reparto, branco], titolo="Fuoco"), "application/json"
    )
    assert risposta.status_code == 201
    voce = risposta.json()
    assert voce["ambito"] == "UNITA" and sorted(voce["unita_ids"]) == sorted(
        [reparto.pk, branco.pk]
    )
    assert voce["unita"] == f"{branco} e {reparto}"
    # The staff of either unit changes it, keeping the other unit.
    for chi in (capo, staff_branco):
        risposta = _client(chi).put(
            f"{URL}/{voce['id']}", _con("UNITA", [reparto, branco]), "application/json"
        )
        assert risposta.status_code == 200
    # Taking away one's own units would leave it to the others: refused.
    risposta = _client(capo).put(f"{URL}/{voce['id']}", _con("UNITA", [branco]), "application/json")
    assert risposta.status_code == 403
    assert VoceLibro.objects.get(pk=voce["id"]).unita.count() == 2


def test_comunita_capi_solo_capigruppo(capo, capogruppo):
    _accendi()
    assert _client(capo).post(URL, _con("COCA"), "application/json").status_code == 403
    risposta = _client(capogruppo).post(URL, _con("COCA"), "application/json")
    assert risposta.status_code == 201 and risposta.json()["unita"] == "Comunità capi"


def test_strutture_di_un_reparto(capo, capogruppo, reparto, branco, gruppo):
    from apps.eventi.servizi import crea_alta

    _accendi()
    client = _client(capo)
    alta = crea_alta(reparto, "Aquile Randagie")
    risposta = client.post(URL, _dati(ambito="ALTA_SQ", alta_id=alta.pk), "application/json")
    assert risposta.status_code == 201
    assert risposta.json()["unita"] == "Alta Squadriglia «Aquile Randagie»"
    assert risposta.json()["alta_id"] == alta.pk
    assert client.post(URL, _dati(ambito="ALTA_SQ"), "application/json").status_code == 400
    risposta = client.post(URL, _con("CONSIGLIO_CAPI", [reparto]), "application/json")
    assert risposta.json()["unita"] == f"Consiglio capi · {reparto}"
    # One reparto, nothing else.
    altro = Unita.objects.create(
        gruppo=gruppo, nome="Altro", tipo=TipoUnita.REPARTO, composizione=Composizione.MISTA
    )
    doppio = _client(capogruppo).post(
        URL, _con("CONSIGLIO_CAPI", [reparto, altro]), "application/json"
    )
    assert doppio.status_code == 400
    # Another reparto's Alta Squadriglia is not the capo's.
    estranea = crea_alta(altro, "Altra")
    risposta = client.post(URL, _dati(ambito="ALTA_SQ", alta_id=estranea.pk), "application/json")
    assert risposta.status_code == 403


def test_consiglio_degli_anziani(staff_branco, capogruppo, reparto, branco):
    _accendi()
    client = _client(staff_branco)
    risposta = client.post(URL, _con("CONSIGLIO_ANZIANI", [branco]), "application/json")
    assert risposta.status_code == 201
    assert risposta.json()["unita"] == f"Consiglio degli Anziani · {branco}"
    sbagliata = _client(capogruppo).post(
        URL, _con("CONSIGLIO_ANZIANI", [reparto]), "application/json"
    )
    assert sbagliata.status_code == 400


def test_voce_di_squadriglie(capo, staff_branco, reparto, squadriglia, ragazza, csq):
    _accendi()
    pantere = Squadriglia.objects.create(unita=reparto, nome="Pantere", sesso="M")
    client = _client(capo)
    risposta = client.post(
        URL,
        _con(
            "SQUADRIGLIE",
            squadriglie=[squadriglia, pantere],
            titolo="Fuoco di squadriglia",
            condizioni=[[{"tipo": "squadriglia", "squadriglia": squadriglia.pk}]],
        ),
        "application/json",
    )
    assert risposta.status_code == 201
    voce = risposta.json()
    assert voce["unita"] == "Sq. Aquile e Sq. Pantere"
    # The staff of another unit does not write it.
    risposta = _client(staff_branco).put(
        f"{URL}/{voce['id']}", _con("SQUADRIGLIE", squadriglie=[pantere]), "application/json"
    )
    assert risposta.status_code == 403
    assert (
        _client(staff_branco)
        .post(URL, _con("SQUADRIGLIE", squadriglie=[pantere]), "application/json")
        .status_code
        == 403
    )
    assert client.post(URL, _con("SQUADRIGLIE"), "application/json").status_code == 400
    # The members of the patrol read it.
    assert "Fuoco di squadriglia" in _titoli(ragazza)
    assert "Fuoco di squadriglia" in _titoli(csq)
    libro = client.get(URL).json()
    assert {s["id"] for s in libro["squadriglie"]} == {squadriglia.pk, pantere.pk}


def test_condizioni_di_un_reparto(capo, reparto, gruppo, csq, ragazza):
    """Consiglio capi and Alta Squadriglia of a reparto, the linked one counting too."""
    from apps.eventi.models import MembroAltaSquadriglia

    _accendi()
    altro = Unita.objects.create(
        gruppo=gruppo, nome="Altro", tipo=TipoUnita.REPARTO, composizione=Composizione.MISTA
    )
    cc_altro = _voce("Consiglio dell'altro", altro)
    cc_altro.condizioni = [[{"tipo": "consiglio_capi", "unita": altro.pk}]]
    cc_altro.save()
    from apps.eventi.servizi import crea_alta

    di_reparto = crea_alta(reparto, "Aquile Randagie")
    alta = VoceLibro.objects.create(
        titolo="Alta del reparto",
        ambito=AmbitoVoce.ALTA_SQUADRIGLIA,
        alta=di_reparto,
        condizioni=[[{"tipo": "alta_squadriglia", "alta": di_reparto.pk}]],
    )
    MembroAltaSquadriglia.objects.create(
        alta=di_reparto, reparto=reparto, persona=ragazza, data_inizio=INIZIO_ANNO
    )
    assert _titoli(csq) == set()
    assert _titoli(ragazza) == {"Alta del reparto"}
    # Linked: one Consiglio capi for every permission.
    reparto.collegata_a, altro.collegata_a = altro, reparto
    reparto.save()
    altro.save()
    assert _titoli(csq) == {"Consiglio dell'altro"}
    # An Alta Squadriglia that does not exist is refused.
    risposta = _client(capo).put(
        f"{URL}/{alta.pk}",
        _dati(
            ambito="ALTA_SQ",
            alta_id=di_reparto.pk,
            condizioni=[[{"tipo": "alta_squadriglia", "alta": 99999}]],
        ),
        "application/json",
    )
    assert risposta.status_code == 400


@pytest.mark.django_db(transaction=True)
def test_migrazione_da_una_unita(reparto):
    """An entry of a unit becomes an entry of that one unit; the others of the group."""
    from django.db import connection
    from django.db.migrations.executor import MigrationExecutor

    prima = [("cerimonie", "0005_allegati")]
    dopo = [("cerimonie", "0006_ambito")]
    executor = MigrationExecutor(connection)
    executor.migrate(prima)
    vecchie = executor.loader.project_state(prima).apps
    Vecchia = vecchie.get_model("cerimonie", "VoceLibro")
    Vecchia.objects.create(titolo="Del reparto", unita_id=reparto.pk, condizioni=[])
    Vecchia.objects.create(titolo="Del gruppo", condizioni=[])
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate(dopo)
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate(executor.loader.graph.leaf_nodes())
    del_reparto = VoceLibro.objects.get(titolo="Del reparto")
    assert del_reparto.ambito == AmbitoVoce.UNITA
    assert list(del_reparto.unita.all()) == [reparto]
    assert VoceLibro.objects.get(titolo="Del gruppo").ambito == AmbitoVoce.GRUPPO
