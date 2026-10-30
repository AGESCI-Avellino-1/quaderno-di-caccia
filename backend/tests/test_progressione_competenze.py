"""Specialità, brevetti, specialità di squadriglia, imprese (DEC-62…DEC-65), with the
test cases of the PP specification v1.0 that concern them (§13, §19.3; DEC-73)."""

from datetime import date, timedelta

import pytest
from django.test import Client

from apps.progressione import catalogo
from apps.progressione.models import PercorsoCompetenza, StatoCompetenza, TipoCompetenza
from tests.conftest import crea_capo

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


@pytest.fixture
def sentiero(capo, ragazza):
    risposta = _post(
        capo,
        f"/api/v1/persone/{ragazza.pk}/progressione/sentiero",
        {"data": (OGGI - timedelta(days=400)).isoformat(), "precisione": "GIORNO"},
    )
    assert risposta.status_code == 201
    return ragazza


def _nuova(capo, ragazza, tipo, codice, **altro):
    risposta = _post(
        capo,
        f"/api/v1/persone/{ragazza.pk}/progressione/competenze",
        {"tipo": tipo, "codice": codice, **altro},
    )
    assert risposta.status_code == 201, risposta.content
    return risposta.json()["competenze"][-1]


def test_specialita_con_carta_maestro_e_conquista(capo, csq, sentiero):
    ragazza = sentiero
    voce = _nuova(
        capo,
        ragazza,
        "SPECIALITA",
        "EGSP001",
        carta="Allevare i conigli",
        maestro="Zio Pino (esterno)",
    )
    assert (voce["nome"], voce["stato"], voce["maestro"]) == (
        "Allevatore",
        "PROPOSTO",
        "Zio Pino (esterno)",
    )
    url = f"/api/v1/competenze/{voce['id']}"
    # The ragazzo does not start or recognise; they and the CSQ ask for verification.
    assert _post(ragazza, f"{url}/avvia").status_code == 403
    _post(capo, f"{url}/avvia")
    assert _post(csq, f"{url}/proponi_verifica").status_code == 200
    assert _post(ragazza, f"{url}/riconosci").status_code == 403
    scheda = _post(capo, f"{url}/riconosci").json()
    voce = scheda["competenze"][0]
    assert voce["stato"] == "RICONOSCIUTO" and voce["riconosciuto"]["data"] == OGGI.isoformat()
    assert PercorsoCompetenza.objects.get().sede == "CONSIGLIO_LEGGE"
    # The badge, with its own date.
    scheda = _post(
        capo, f"{url}/distintivo", {"data": OGGI.isoformat(), "precisione": "GIORNO"}
    ).json()
    assert scheda["competenze"][0]["distintivo"]
    # Twice the same step: one effect.
    assert _post(capo, f"{url}/riconosci").status_code == 200


def test_la_ragazza_non_apre_specialita(sentiero):
    risposta = _post(
        sentiero,
        f"/api/v1/persone/{sentiero.pk}/progressione/competenze",
        {"tipo": "SPECIALITA", "codice": "EGSP001"},
    )
    assert risposta.status_code == 403


def test_specialita_importata_con_il_solo_anno(capo, sentiero):
    """§13: a specialità imported with the year known and the day unknown."""
    anno = OGGI.year - 1
    voce = _nuova(
        capo,
        sentiero,
        "SPECIALITA",
        "EGSP002",
        conquistata={"data": f"{anno}-01-01", "precisione": "ANNO"},
    )
    assert voce["stato"] == "RICONOSCIUTO" and voce["storico"]
    assert voce["riconosciuto"] == {"data": f"{anno}-01-01", "precisione": "ANNO"}


def test_brevetto_con_confronto_esterno_e_specialita(capo, sentiero):
    """§13: a comparison outside the Association is not refused (V09)."""
    specialita = _nuova(capo, sentiero, "SPECIALITA", "EGSP002")
    brevetto = _nuova(capo, sentiero, "BREVETTO", "EGBR001", carta="Progetto di animazione")
    scheda = _put(
        capo,
        f"/api/v1/competenze/{brevetto['id']}",
        {
            "carta": "Progetto di animazione",
            "maestro": "Allenatrice della polisportiva",
            "confronto": "Corso di arbitro della federazione",
            "collegati": [specialita["id"]],
        },
    ).json()
    brevetto = next(c for c in scheda["competenze"] if c["tipo"] == "BREVETTO")
    assert brevetto["confronto"] == "Corso di arbitro della federazione"
    assert brevetto["collegati"] == [specialita["id"]]


def test_il_nome_della_conquista_resta_quello_dell_epoca(capo, sentiero, monkeypatch):
    """§19.3: the catalog renames an item; the recognised path keeps its name."""
    voce = _nuova(capo, sentiero, "SPECIALITA", "EGSP001")
    rinominata = tuple(
        catalogo.Voce(v.codice, "Nuovo nome", "2030", v.ritirata) if v.codice == "EGSP001" else v
        for v in catalogo.voci(TipoCompetenza.SPECIALITA)
    )
    monkeypatch.setattr(catalogo, "voci", lambda tipo: rinominata)
    scheda = _client(capo).get(f"/api/v1/persone/{sentiero.pk}/progressione").json()
    assert scheda["competenze"][0]["nome"] == "Allevatore"
    assert PercorsoCompetenza.objects.get(pk=voce["id"]).versione_catalogo == "2026"


def test_voce_ritirata(capo, sentiero, monkeypatch):
    """DEC-63: withdrawn from new choices, kept in history."""
    ritirate = tuple(
        catalogo.Voce(v.codice, v.nome, v.versione, True)
        for v in catalogo.voci(TipoCompetenza.SPECIALITA)
    )
    monkeypatch.setattr(catalogo, "voci", lambda tipo: ritirate)
    risposta = _post(
        capo,
        f"/api/v1/persone/{sentiero.pk}/progressione/competenze",
        {"tipo": "SPECIALITA", "codice": "EGSP001"},
    )
    assert "ritirata" in risposta.json()["detail"]
    _nuova(
        capo,
        sentiero,
        "SPECIALITA",
        "EGSP001",
        conquistata={"data": f"{OGGI.year - 3}-01-01", "precisione": "ANNO"},
    )


def test_specialita_di_squadriglia_non_va_ai_membri(capo, sentiero, squadriglia, reparto):
    """§19.3, V19: conquered by the patrol, no personal specialità for its members;
    the members' specialità born from it are linked (DEC-64)."""
    individuale = _nuova(capo, sentiero, "SPECIALITA", "EGSP001")
    dati = _post(
        capo,
        f"/api/v1/squadriglie/{squadriglia.pk}/competenze",
        {"codice": "EGSQ001", "carta": "Uscita in montagna"},
    ).json()
    (sq,) = [s for s in dati["squadriglie"] if s["id"] == squadriglia.pk]
    percorso = sq["competenze"][0]
    assert any(i["id"] == individuale["id"] for i in sq["individuali"])
    _put(
        capo,
        f"/api/v1/competenze/{percorso['id']}",
        {"carta": "Uscita in montagna", "collegati": [individuale["id"]]},
    )
    _post(capo, f"/api/v1/competenze/{percorso['id']}/avvia")
    _post(capo, f"/api/v1/competenze/{percorso['id']}/proponi_verifica")
    dati = _post(capo, f"/api/v1/competenze/{percorso['id']}/riconosci").json()
    assert dati["squadriglie"][0]["competenze"][0]["stato"] == "RICONOSCIUTO"
    personali = PercorsoCompetenza.objects.filter(periodo__isnull=False)
    assert list(personali.values_list("codice", flat=True)) == ["EGSP001"]
    assert personali.get().stato == StatoCompetenza.PROPOSTO


def test_imprese_e_posti_d_azione(capo, sentiero, squadriglia, reparto, coca):
    altro = crea_capo("Carlo", "Altro", "altro@example.invalid")
    url = f"/api/v1/unita/{reparto.pk}/imprese"
    dati = {
        "livello": "SQUADRIGLIA",
        "squadriglia_id": squadriglia.pk,
        "titolo": "Costruiamo una zattera",
        "dal": OGGI.isoformat(),
    }
    assert _post(altro, url, dati).status_code == 403
    assert _client(altro).get(url).status_code == 200  # any capo reads
    assert _client(sentiero).get(url).status_code == 403
    impresa = _post(capo, url, dati).json()["imprese"][0]
    dati = _post(
        capo,
        f"/api/v1/imprese/{impresa['id']}/posti",
        {"persona_id": sentiero.pk, "ruolo": "Cambusiera"},
    ).json()
    posto = dati["imprese"][0]["posti"][0]
    risposta = _post(
        capo,
        f"/api/v1/posti-azione/{posto['id']}/verifica",
        {"il": OGGI.isoformat(), "sede": "CONSIGLIO_SQ"},
    )
    assert risposta.json()["imprese"][0]["posti"][0]["sede_nome"] == "Consiglio di squadriglia"
    # The ragazza sees her role in her sentiero.
    scheda = _client(sentiero).get(f"/api/v1/persone/{sentiero.pk}/progressione").json()
    assert scheda["posti_azione"][0]["ruolo"] == "Cambusiera"


def test_promemoria_del_brevetto_senza_blocchi(capo, sentiero, reparto):
    """V10: a reminder for the capi; nothing is attributed or blocked."""
    righe = _client(capo).get(f"/api/v1/unita/{reparto.pk}/progressione").json()["ragazzi"]
    assert next(r for r in righe if r["persona_id"] == sentiero.pk)["brevetto"] is None
    _nuova(capo, sentiero, "BREVETTO", "EGBR002")
    righe = _client(capo).get(f"/api/v1/unita/{reparto.pk}/progressione").json()["ragazzi"]
    assert next(r for r in righe if r["persona_id"] == sentiero.pk)["brevetto"] == "in corso"
