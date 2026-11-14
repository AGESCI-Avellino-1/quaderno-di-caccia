"""Archived patrols (DEC-403): only when empty, for good, on a page of their own."""

import pytest
from django.db import IntegrityError, transaction
from django.test import Client
from django.utils import timezone

from apps.organizzazione.models import AnimaleSquadriglia, Squadriglia
from tests.conftest import INIZIO_ANNO

pytestmark = pytest.mark.django_db


def _client(chi) -> Client:
    client = Client()
    client.force_login(chi.utente)
    return client


def _post(chi, url, dati=None):
    return _client(chi).post(url, dati or {}, content_type="application/json")


def _put(chi, url, dati):
    return _client(chi).put(url, dati, content_type="application/json")


@pytest.fixture
def pantere(reparto) -> Squadriglia:
    animale = AnimaleSquadriglia.objects.get_or_create(
        nome="Pantera", defaults={"plurale": "Pantere"}
    )[0]
    return Squadriglia.objects.create(unita=reparto, nome="Pantere", animale=animale, sesso="F")


def _archivia(chi, squadriglia):
    return _post(chi, f"/api/v1/squadriglie/{squadriglia.pk}/archivia")


def test_si_archivia_solo_vuota(capo, ragazza, squadriglia):
    risposta = _archivia(capo, squadriglia)
    assert risposta.status_code == 400
    assert "ha ancora dei membri" in risposta.json()["detail"]
    membro = ragazza.appartenenze_squadriglia.get()
    _post(capo, f"/api/v1/membri-squadriglia/{membro.pk}/termina")
    risposta = _archivia(capo, squadriglia)
    assert risposta.status_code == 200
    squadriglia.refresh_from_db()
    assert squadriglia.attiva is False
    assert squadriglia.archiviata_il == timezone.localdate()


def test_archiviare_di_nuovo_non_cambia_nulla(capo, pantere):
    # An offline replay answers as done.
    assert _archivia(capo, pantere).status_code == 200
    assert _archivia(capo, pantere).status_code == 200


def test_un_archiviata_non_si_modifica_ne_si_riapre(capo, pantere):
    _archivia(capo, pantere)
    risposta = _put(capo, f"/api/v1/squadriglie/{pantere.pk}", {"sesso": "F"})
    assert risposta.status_code == 400
    assert "archiviata" in risposta.json()["detail"]
    # The field of before is ignored: no way back.
    _put(capo, f"/api/v1/squadriglie/{pantere.pk}", {"sesso": "F", "attiva": True})
    pantere.refresh_from_db()
    assert pantere.attiva is False


def test_in_un_archiviata_non_entra_nessuno(capo, reparto, pantere, ragazza):
    _archivia(capo, pantere)
    risposta = _post(capo, f"/api/v1/squadriglie/{pantere.pk}/membri", {"persona_id": ragazza.pk})
    assert risposta.status_code == 400


def test_l_animale_non_si_cambia(capo, pantere):
    lupo = AnimaleSquadriglia.objects.get_or_create(nome="Lupo", defaults={"plurale": "Lupi"})[0]
    risposta = _put(
        capo, f"/api/v1/squadriglie/{pantere.pk}", {"animale_id": lupo.pk, "sesso": "F"}
    )
    assert risposta.status_code == 400
    assert "aprine una nuova" in risposta.json()["detail"]
    # The same animal again changes nothing.
    stesso = {"animale_id": pantere.animale_id, "sesso": "F"}
    assert _put(capo, f"/api/v1/squadriglie/{pantere.pk}", stesso).status_code == 200


def test_stesso_nome_dopo_l_archiviazione(capo, reparto, pantere):
    _archivia(capo, pantere)
    nuova = _post(
        capo,
        f"/api/v1/unita/{reparto.pk}/squadriglie",
        {"animale_id": pantere.animale_id, "sesso": "F"},
    )
    assert nuova.status_code == 201
    assert nuova.json()["id"] != pantere.pk
    assert Squadriglia.objects.filter(unita=reparto, nome="Pantere").count() == 2


def test_due_attive_con_lo_stesso_nome_no(reparto, pantere):
    with pytest.raises(IntegrityError), transaction.atomic():
        Squadriglia.objects.create(unita=reparto, nome="Pantere", sesso="F")


def test_la_pagina_dell_unita_e_quella_delle_archiviate(capo, reparto, squadriglia, pantere):
    _archivia(capo, pantere)
    dettaglio = _client(capo).get(f"/api/v1/unita/{reparto.pk}").json()
    assert [s["nome"] for s in dettaglio["squadriglie"]] == ["Aquile"]
    assert dettaglio["squadriglie_archiviate"] == 1
    archiviate = _client(capo).get(f"/api/v1/unita/{reparto.pk}/squadriglie-archiviate")
    assert archiviate.status_code == 200
    [sola] = archiviate.json()
    assert sola["nome"] == "Pantere"
    assert sola["al"] == timezone.localdate().isoformat()
    assert sola["dal"] == pantere.creato_il.date().isoformat()


def test_il_periodo_parte_dal_primo_membro(capo, reparto, ragazza, squadriglia):
    membro = ragazza.appartenenze_squadriglia.get()
    _post(capo, f"/api/v1/membri-squadriglia/{membro.pk}/termina")
    _archivia(capo, squadriglia)
    [sola] = _client(capo).get(f"/api/v1/unita/{reparto.pk}/squadriglie-archiviate").json()
    assert sola["dal"] == min(INIZIO_ANNO, squadriglia.creato_il.date()).isoformat()


@pytest.mark.parametrize("ruolo", ["capogruppo", "capo"])
def test_archiviano_staff_e_capigruppo(request, ruolo, pantere):
    assert _archivia(request.getfixturevalue(ruolo), pantere).status_code == 200


@pytest.mark.parametrize("ruolo", ["csq", "ragazza", "genitore", "estraneo"])
def test_gli_altri_non_archiviano(request, ruolo, pantere):
    assert _archivia(request.getfixturevalue(ruolo), pantere).status_code == 403
    pantere.refresh_from_db()
    assert pantere.attiva is True


@pytest.mark.parametrize("ruolo", ["csq", "ragazza", "genitore", "estraneo"])
def test_le_archiviate_le_vede_chi_vede_l_unita(request, ruolo, capo, reparto, pantere):
    _archivia(capo, pantere)
    chi = request.getfixturevalue(ruolo)
    url = f"/api/v1/unita/{reparto.pk}/squadriglie-archiviate"
    assert _client(chi).get(url).status_code == 403
    assert _client(chi).get(f"/api/v1/unita/{reparto.pk}").status_code == 403


# --- The patrols' history for esploratori and guide (DEC-407) ------------------------------


def test_storia_per_esploratori_e_guide(capo, gruppo, reparto, squadriglia, pantere, ragazza):
    from apps.organizzazione import servizi
    from apps.organizzazione.models import Composizione, TipoUnita, Unita

    _archivia(capo, pantere)
    parallelo = Unita.objects.create(
        gruppo=gruppo, nome="Parallelo", tipo=TipoUnita.REPARTO, composizione=Composizione.MISTA
    )
    servizi.collega(reparto, parallelo, "")
    Squadriglia.objects.create(unita=parallelo, nome="Lupi", sesso="M")
    risposta = _client(ragazza).get("/api/v1/storia-squadriglie")
    assert risposta.status_code == 200
    storia = {r["id"]: r for r in risposta.json()}
    assert set(storia) == {reparto.pk, parallelo.pk}
    nostre = storia[reparto.pk]["squadriglie"]
    # The active ones first, then the archived.
    assert [(s["nome"], s["attiva"]) for s in nostre] == [("Aquile", True), ("Pantere", False)]
    assert nostre[1]["al"] == timezone.localdate().isoformat()
    # No names of people anywhere.
    assert "Giulia" not in risposta.content.decode()
    assert _client(ragazza).get("/api/v1/io").json()["storia_squadriglie"] is True


@pytest.mark.parametrize("ruolo", ["capo", "capogruppo", "genitore", "estraneo"])
def test_storia_non_per_gli_altri(request, ruolo):
    chi = request.getfixturevalue(ruolo)
    assert _client(chi).get("/api/v1/storia-squadriglie").status_code == 403
    assert _client(chi).get("/api/v1/io").json()["storia_squadriglie"] is False
