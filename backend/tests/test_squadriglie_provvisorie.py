"""A patrol created without an animal, which its CSQ chooses (DEC-409)."""

from datetime import date, timedelta

import pytest
from django.core import mail
from django.test import Client
from django.utils import timezone

from apps.anagrafica.models import AppartenenzaSquadriglia
from apps.organizzazione.models import AnimaleSquadriglia, Incarico, RuoloIncarico, Squadriglia
from tests.conftest import INIZIO_ANNO

pytestmark = pytest.mark.django_db


def _client(chi) -> Client:
    client = Client()
    client.force_login(chi.utente)
    return client


def _json(chi, metodo, url, dati):
    return getattr(_client(chi), metodo)(url, dati, content_type="application/json")


def _animale(nome="Pantera", plurale="Pantere") -> AnimaleSquadriglia:
    return AnimaleSquadriglia.objects.get_or_create(nome=nome, defaults={"plurale": plurale})[0]


@pytest.fixture
def nuova(capo, reparto) -> Squadriglia:
    risposta = _json(capo, "post", f"/api/v1/unita/{reparto.pk}/squadriglie", {"sesso": "F"})
    return Squadriglia.objects.get(pk=risposta.json()["id"])


@pytest.fixture
def capo_sq(nuova, ragazza):
    # The ragazza moves into the new patrol and becomes its CSQ.
    AppartenenzaSquadriglia.objects.filter(persona=ragazza).delete()
    AppartenenzaSquadriglia.objects.create(
        persona=ragazza, squadriglia=nuova, data_inizio=INIZIO_ANNO
    )
    Incarico.objects.create(
        persona=ragazza, ruolo=RuoloIncarico.CSQ, squadriglia=nuova, data_inizio=INIZIO_ANNO
    )
    return ragazza


def _scegli(chi, squadriglia, animale):
    return _json(
        chi, "post", f"/api/v1/squadriglie/{squadriglia.pk}/animale", {"animale_id": animale.pk}
    )


def test_il_capo_squadriglia_sceglie_una_volta(
    capo, nuova, capo_sq, settings, django_capture_on_commit_callbacks
):
    settings.FRONTEND_URL = "https://qdc.example"
    with django_capture_on_commit_callbacks(execute=True):
        risposta = _scegli(capo_sq, nuova, _animale())
    assert risposta.status_code == 200, risposta.content
    nuova.refresh_from_db()
    assert (nuova.nome, nuova.provvisoria) == ("Pantere", False)
    assert nuova.animale_scelto_il == timezone.localdate()
    # The provisional name is forgotten.
    assert not Squadriglia.objects.filter(nome__startswith="Nuova Squadriglia").exists()
    # The staff is told by email.
    [email] = mail.outbox
    assert email.to == [capo.utente.email]
    assert "Pantere" in email.body
    # A second choice by the CSQ is refused.
    assert _scegli(capo_sq, nuova, _animale("Lupo", "Lupi")).status_code == 403
    # The same again (an offline replay) answers as done.
    assert _scegli(capo_sq, nuova, _animale()).status_code == 200


def test_lo_staff_corregge_entro_un_mese(capo, nuova, capo_sq):
    _scegli(capo_sq, nuova, _animale())
    nuova.refresh_from_db()
    lupi = {"animale_id": _animale("Lupo", "Lupi").pk, "sesso": "F"}
    url = f"/api/v1/squadriglie/{nuova.pk}"
    dettaglio = _client(capo).get(f"/api/v1/unita/{nuova.unita_id}").json()
    [sq] = [s for s in dettaglio["squadriglie"] if s["id"] == nuova.pk]
    assert sq["correggibile_fino"] == nuova.correggibile_fino().isoformat()
    assert _json(capo, "put", url, lupi).json()["nome"] == "Lupi"
    # A month later: no more (DEC-403).
    Squadriglia.objects.filter(pk=nuova.pk).update(
        animale_scelto_il=timezone.localdate() - timedelta(days=40)
    )
    orsi = {"animale_id": _animale("Orso", "Orsi").pk, "sesso": "F"}
    assert _json(capo, "put", url, orsi).status_code == 400


def test_un_mese_di_calendario():
    sq = Squadriglia(animale_scelto_il=date(2027, 1, 31))
    assert sq.correggibile_fino() == date(2027, 2, 28)
    sq.animale_scelto_il = date(2026, 12, 14)
    assert sq.correggibile_fino() == date(2027, 1, 14)


def test_scelta_dallo_staff_senza_avviso_ne_mese(capo, nuova):
    assert _scegli(capo, nuova, _animale()).status_code == 200
    nuova.refresh_from_db()
    assert nuova.animale_scelto_il is None
    assert mail.outbox == []


@pytest.mark.parametrize("ruolo", ["csq", "genitore", "estraneo"])
def test_gli_altri_non_scelgono(request, ruolo, nuova):
    # The CSQ of another patrol either.
    assert _scegli(request.getfixturevalue(ruolo), nuova, _animale()).status_code == 403


def test_il_capo_squadriglia_vede_che_e_provvisoria(nuova, capo_sq):
    [mia] = _client(capo_sq).get("/api/v1/mia-squadriglia").json()
    assert mia["provvisoria"] is True
    assert mia["sono_capo"] is True
