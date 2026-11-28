"""The Alta Squadriglia with its antechamber (DEC-439): periods kept for the history, one for two
linked reparti, the entry ceremony of the book, the antechamber invited by choice."""

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import Client

from apps.anagrafica.models import Appartenenza, Persona, RuoloAppartenenza
from apps.cerimonie.models import AmbitoVoce, VoceLibro
from apps.eventi import servizi
from apps.eventi.models import Cerchia, Evento, Livello, MembroAltaSquadriglia, TipoEvento
from apps.impostazioni import funzioni
from apps.organizzazione.models import Composizione, TipoUnita, Unita
from apps.organizzazione.servizi import esci_dal_reparto
from tests.conftest import INIZIO_ANNO, crea_persona, nato_anni_fa

pytestmark = pytest.mark.django_db

ROMA = ZoneInfo("Europe/Rome")
OGGI = date.today()


def _client(chi) -> Client:
    client = Client()
    client.force_login(chi.utente)
    return client


def _url(reparto, dopo: str = "") -> str:
    return f"/api/v1/unita/{reparto.pk}/alta-squadriglia{dopo}"


@pytest.fixture
def luca(reparto) -> Persona:
    persona = crea_persona(
        "Luca", "Esploratore", "luca@example.invalid", data_nascita=nato_anni_fa(14)
    )
    Appartenenza.objects.create(
        persona=persona, unita=reparto, ruolo=RuoloAppartenenza.RAGAZZO, data_inizio=INIZIO_ANNO
    )
    return persona


@pytest.fixture
def altro(gruppo, reparto) -> Unita:
    """A reparto linked to `reparto`: one Alta Squadriglia for the two."""
    altro = Unita.objects.create(
        gruppo=gruppo, nome="Altro", tipo=TipoUnita.REPARTO, composizione=Composizione.MASCHILE
    )
    reparto.collegata_a, altro.collegata_a = altro, reparto
    reparto.save()
    altro.save()
    return altro


def _alta(chi, reparto) -> dict:
    return _client(chi).get(_url(reparto)).json()


def test_anticamera_ingresso_e_storia(capo, ragazza, luca, csq, reparto):
    client = _client(capo)
    risposta = client.post(
        _url(reparto, "/anticamera"), {"persone": [ragazza.pk, luca.pk]}, "application/json"
    )
    # By surname: Esploratore before Esploratrice.
    assert [m["persona_id"] for m in risposta.json()["anticamera"]] == [luca.pk, ragazza.pk]
    # Directly, with a day of past years: the Alta Squadriglia was there before the app.
    passato = date(OGGI.year - 3, 5, 4)
    client.post(
        _url(reparto, "/ingresso"),
        {"persone": [csq.pk], "data": passato.isoformat()},
        "application/json",
    )
    # From the antechamber, today.
    alta = client.post(
        _url(reparto, "/ingresso"), {"persone": [ragazza.pk]}, "application/json"
    ).json()
    assert {(m["persona_id"], m["dal"]) for m in alta["entrati"]} == {
        (csq.pk, passato.isoformat()),
        (ragazza.pk, OGGI.isoformat()),
    }
    assert [m["persona_id"] for m in alta["anticamera"]] == [luca.pk]
    assert alta["candidati"] == []
    # No day in the future.
    futuro = (OGGI + timedelta(days=1)).isoformat()
    risposta = client.post(
        _url(reparto, "/ingresso"), {"persone": [luca.pk], "data": futuro}, "application/json"
    )
    assert risposta.status_code == 400
    # Taken off: the period closes and stays; one that began today never took effect.
    csq_membro = next(m for m in alta["entrati"] if m["persona_id"] == csq.pk)
    alta = client.delete(_url(reparto, f"/{csq_membro['id']}")).json()
    assert [(m["persona_id"], m["al"]) for m in alta["usciti"]] == [(csq.pk, OGGI.isoformat())]
    ragazza_membro = next(m for m in alta["entrati"] if m["persona_id"] == ragazza.pk)
    alta = client.post(_url(reparto, f"/{ragazza_membro['id']}/anticamera")).json()
    assert {m["persona_id"] for m in alta["anticamera"]} == {ragazza.pk, luca.pk}
    luca_membro = next(m for m in alta["anticamera"] if m["persona_id"] == luca.pk)
    alta = client.delete(_url(reparto, f"/{luca_membro['id']}")).json()
    assert not MembroAltaSquadriglia.objects.filter(persona=luca).exists()
    # Only capi read it; only the staff changes it.
    assert _client(ragazza).get(_url(reparto)).status_code == 403
    assert (
        _client(csq)
        .post(_url(reparto, "/anticamera"), {"persone": [luca.pk]}, "application/json")
        .status_code
        == 403
    )


def test_reparti_collegati_una_sola_alta(capo, ragazza, reparto, altro, gruppo):
    tommaso = crea_persona("Tommaso", "Altro", data_nascita=nato_anni_fa(14))
    Appartenenza.objects.create(
        persona=tommaso, unita=altro, ruolo=RuoloAppartenenza.RAGAZZO, data_inizio=INIZIO_ANNO
    )
    _client(capo).post(
        _url(reparto, "/ingresso"), {"persone": [ragazza.pk, tommaso.pk]}, "application/json"
    )
    # Recorded in each one's own reparto, shown on both pages.
    assert MembroAltaSquadriglia.objects.get(persona=tommaso).reparto == altro
    assert {m["persona_id"] for m in _alta(capo, altro)["entrati"]} == {ragazza.pk, tommaso.pk}
    assert _alta(capo, altro)["insieme_a"] == str(reparto)
    # In the book's form, each reparto says which one it is linked to.
    funzioni.imposta(funzioni.CERIMONIE, True)
    unita = _client(capo).get("/api/v1/cerimonie").json()["unita"]
    assert {(u["id"], u["collegata_id"]) for u in unita} == {
        (reparto.pk, altro.pk),
        (altro.pk, reparto.pk),
    }
    # Another reparto, not linked: a different one, and nobody in two.
    terzo = Unita.objects.create(
        gruppo=gruppo, nome="Terzo", tipo=TipoUnita.REPARTO, composizione=Composizione.MISTA
    )
    assert _alta(capo, terzo)["entrati"] == []


def test_uscire_dal_reparto_chiude_il_periodo(ragazza, luca, reparto):
    servizi.fai_entrare(reparto, [ragazza], date(OGGI.year - 1, 3, 1))
    servizi.metti_in_anticamera(reparto, [luca])
    esci_dal_reparto(ragazza, reparto, OGGI)
    esci_dal_reparto(luca, reparto, OGGI)
    membro = MembroAltaSquadriglia.objects.get(persona=ragazza)
    assert membro.data_fine == OGGI
    assert not MembroAltaSquadriglia.objects.filter(persona=luca).exists()


def _riunione(reparto, capo, giorno: date, anticamera: bool = False) -> Evento:
    return servizi.crea(
        Evento(
            titolo="Alta",
            tipo=TipoEvento.RIUNIONE,
            livello=Livello.UNITA,
            cerchia=Cerchia.ALTA_SQUADRIGLIA,
            anticamera=anticamera,
            inizio=datetime.combine(giorno, time(18), ROMA),
            fine=datetime.combine(giorno, time(20), ROMA),
        ),
        [reparto],
        capo.utente,
    )


def _invitati(evento: Evento) -> set[int]:
    return set(evento.partecipazioni.values_list("persona_id", flat=True))


def test_invitati_alle_riunioni(capo, ragazza, luca, csq, reparto, altro):
    servizi.fai_entrare(reparto, [ragazza], date(OGGI.year - 1, 3, 1))
    servizi.metti_in_anticamera(reparto, [luca])
    domani = OGGI + timedelta(days=1)
    assert _invitati(_riunione(reparto, capo, domani)) == {ragazza.pk}
    assert _invitati(_riunione(reparto, capo, domani, anticamera=True)) == {ragazza.pk, luca.pk}
    # A meeting of the linked reparto is of the same Alta Squadriglia.
    assert _invitati(_riunione(altro, capo, domani)) == {ragazza.pk}
    # Who entered after the day was not in.
    servizi.fai_entrare(reparto, [csq], OGGI)
    passata = date(OGGI.year - 1, 6, 1)
    assert _invitati(_riunione(reparto, capo, passata)) == {ragazza.pk}


def test_anticamera_dalle_riunioni_ricorrenti(
    capo, ragazza, luca, reparto, django_capture_on_commit_callbacks
):
    servizi.fai_entrare(reparto, [ragazza], date(OGGI.year - 1, 3, 1))
    servizi.metti_in_anticamera(reparto, [luca])
    inizio = OGGI + timedelta(days=1)
    risposta = _client(capo).post(
        "/api/v1/riunioni",
        {
            "cerchia": "ALTA_SQ",
            "unita": [reparto.pk],
            "ora_inizio": "18:00",
            "ora_fine": "20:00",
            "giorno_settimana": inizio.weekday(),
            "dal": inizio.isoformat(),
            "al": (inizio + timedelta(days=14)).isoformat(),
            "anticamera": True,
        },
        "application/json",
    )
    assert risposta.status_code == 201
    eventi = Evento.objects.filter(cerchia=Cerchia.ALTA_SQUADRIGLIA)
    assert all(e.anticamera and luca.pk in _invitati(e) for e in eventi)
    serie = eventi.first().riunione
    with django_capture_on_commit_callbacks(execute=True):
        risposta = _client(capo).put(
            f"/api/v1/riunioni/serie/{serie.pk}",
            {"uniforme": True, "anticamera": False},
            "application/json",
        )
    assert risposta.status_code == 200 and not risposta.json()["anticamera"]
    assert all(_invitati(e) == {ragazza.pk} for e in Evento.objects.filter(riunione=serie))
    # One meeting changes on its own.
    evento = Evento.objects.filter(riunione=serie).first()
    risposta = _client(capo).put(
        f"/api/v1/riunioni/{evento.pk}",
        {
            "inizio": evento.inizio.isoformat(),
            "fine": evento.fine.isoformat(),
            "anticamera": True,
        },
        "application/json",
    )
    assert risposta.status_code == 200 and risposta.json()["anticamera"]
    assert luca.pk in _invitati(evento)


# --- The book (DEC-439) ----------------------------------------------------------------------


@pytest.fixture
def libro(reparto):
    funzioni.imposta(funzioni.CERIMONIE, True)
    ingresso = VoceLibro.objects.create(
        titolo="Ingresso in Alta",
        ambito=AmbitoVoce.ALTA_SQUADRIGLIA,
        cerimonia_ingresso_alta=True,
        condizioni=[[{"tipo": "alta_squadriglia", "unita": reparto.pk}]],
    )
    ingresso.unita.set([reparto])
    notte = VoceLibro.objects.create(
        titolo="Notte dell'Alta",
        ambito=AmbitoVoce.ALTA_SQUADRIGLIA,
        condizioni=[[{"tipo": "alta_squadriglia", "unita": reparto.pk}]],
    )
    notte.unita.set([reparto])
    return {"ingresso": ingresso, "notte": notte}


def _titoli(chi) -> set[str]:
    return {v["titolo"] for v in _client(chi).get("/api/v1/cerimonie").json()["voci"]}


def test_anticamera_non_legge_le_voci_dell_alta(capo, luca, reparto, libro):
    servizi.metti_in_anticamera(reparto, [luca])
    # Not even when added by hand.
    libro["notte"].aggiunti.add(luca)
    assert _titoli(luca) == set()
    assert _client(luca).get(f"/api/v1/cerimonie/{libro['notte'].pk}").status_code == 404
    risposta = _client(capo).post(
        "/api/v1/cerimonie/anteprima",
        {"aggiunti": [luca.pk], "ambito": "ALTA_SQ", "unita_ids": [reparto.pk]},
        "application/json",
    )
    assert risposta.json() == []
    # In: the entries open.
    servizi.fai_entrare(reparto, [luca], OGGI)
    assert _titoli(luca) == {"Ingresso in Alta", "Notte dell'Alta"}


def test_cerimonia_d_ingresso_fa_entrare(capo, ragazza, luca, csq, reparto, libro):
    ingresso = libro["ingresso"]
    servizi.metti_in_anticamera(reparto, [luca])
    giorno = date(OGGI.year - 1, 4, 12)
    risposta = _client(capo).post(
        f"/api/v1/cerimonie/{ingresso.pk}/partecipanti",
        {"persone": [luca.pk], "data": giorno.isoformat()},
        "application/json",
    )
    assert risposta.status_code == 200
    assert MembroAltaSquadriglia.objects.get(persona=luca).data_inizio == giorno
    # Who entered by hand is in the register by themselves, with the day of entry.
    servizi.fai_entrare(reparto, [ragazza], OGGI)
    registro = _client(capo).get(f"/api/v1/cerimonie/{ingresso.pk}").json()["partecipanti"]
    assert [(p["id"], p["data"], p["automatica"]) for p in registro] == [
        (luca.pk, giorno.isoformat(), False),
        (ragazza.pk, OGGI.isoformat(), True),
    ]
    voce = _client(ragazza).get(f"/api/v1/cerimonie/{ingresso.pk}").json()
    assert voce["vede_registro"]
    # Out of the reparto, still in the register, and reading the ceremony while a member.
    esci_dal_reparto(ragazza, reparto, OGGI + timedelta(days=1))
    registro = _client(capo).get(f"/api/v1/cerimonie/{ingresso.pk}").json()["partecipanti"]
    assert ragazza.pk in [p["id"] for p in registro]
    assert _alta(capo, reparto)["cerimonia"] == ingresso.pk


def test_una_sola_cerimonia_d_ingresso(capo, reparto, altro, libro):
    risposta = _client(capo).post(
        "/api/v1/cerimonie",
        {
            "titolo": "Nuovo ingresso",
            "tipo": "CERIMONIA",
            "ambito": "ALTA_SQ",
            "unita_ids": [altro.pk],
            "cerimonia_ingresso_alta": True,
        },
        "application/json",
    )
    assert risposta.status_code == 201
    libro["ingresso"].refresh_from_db()
    assert not libro["ingresso"].cerimonia_ingresso_alta
    risposta = _client(capo).post(
        "/api/v1/cerimonie",
        {
            "titolo": "Sbagliata",
            "tipo": "CERIMONIA",
            "ambito": "UNITA",
            "unita_ids": [reparto.pk],
            "cerimonia_ingresso_alta": True,
        },
        "application/json",
    )
    assert risposta.status_code == 400


# --- The yearly lists become periods ---------------------------------------------------------


@pytest.mark.django_db(transaction=True)
def test_migrazione_a_periodi(reparto, ragazza, csq, luca):
    corrente = OGGI.year + 1 if OGGI.month >= 10 else OGGI.year
    prima = [("eventi", "0014_partecipanti_selezionati")]
    executor = MigrationExecutor(connection)
    executor.migrate(prima)
    Vecchio = executor.loader.project_state(prima).apps.get_model("eventi", "MembroAltaSquadriglia")
    # Two years in a row up to this one; one year long ago; two separate years.
    for persona, anni in (
        (ragazza, [corrente - 1, corrente]),
        (csq, [corrente - 4]),
        (luca, [corrente - 3, corrente - 1]),
    ):
        for anno in anni:
            Vecchio.objects.create(reparto_id=reparto.pk, persona_id=persona.pk, anno=anno)
    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())
    periodi = {
        (m.persona_id, m.data_inizio, m.data_fine) for m in MembroAltaSquadriglia.objects.all()
    }
    assert periodi == {
        (ragazza.pk, date(corrente - 2, 10, 1), None),
        (csq.pk, date(corrente - 5, 10, 1), date(corrente - 4, 10, 1)),
        (luca.pk, date(corrente - 4, 10, 1), date(corrente - 3, 10, 1)),
        (luca.pk, date(corrente - 2, 10, 1), date(corrente - 1, 10, 1)),
    }
