"""Phones within the patrol (DEC-13).

Decided with the maintainer on 2026-10-29 (see TODO.md): every member sees the other
members' phone, the CSQ also the parents'; the VCSQ sees like a member; a child without
a phone shares a parent's, chosen by the parents or the capi; the number can be hidden
from the members, never from the CSQ. Phones only, no email.
"""

import pytest
from django.test import Client

from apps.anagrafica.models import AppartenenzaSquadriglia
from apps.organizzazione.models import Incarico, RuoloIncarico, Squadriglia
from tests.conftest import INIZIO_ANNO, crea_capo, crea_persona, nato_anni_fa

pytestmark = pytest.mark.django_db


def _client(persona) -> Client:
    client = Client()
    client.force_login(persona.utente)
    return client


def _put(persona, url, dati):
    return _client(persona).put(url, dati, content_type="application/json")


@pytest.fixture
def vice(reparto, squadriglia):
    from apps.anagrafica.models import Appartenenza, RuoloAppartenenza

    persona = crea_persona(
        "Ada", "Vice", "vice@example.invalid", data_nascita=nato_anni_fa(13), cellulare="3335550000"
    )
    Appartenenza.objects.create(
        persona=persona, unita=reparto, ruolo=RuoloAppartenenza.RAGAZZO, data_inizio=INIZIO_ANNO
    )
    AppartenenzaSquadriglia.objects.create(
        persona=persona, squadriglia=squadriglia, data_inizio=INIZIO_ANNO
    )
    Incarico.objects.create(
        persona=persona, ruolo=RuoloIncarico.VCSQ, squadriglia=squadriglia, data_inizio=INIZIO_ANNO
    )
    return persona


@pytest.fixture
def genitore_con_cellulare(genitore):
    genitore.cellulare = "3471234567"
    genitore.save()
    return genitore


def _mia(persona) -> dict:
    risposta = _client(persona).get("/api/v1/mia-squadriglia")
    assert risposta.status_code == 200
    [squadriglia] = risposta.json()
    return squadriglia


def _telefoni(squadriglia) -> dict[str, str | None]:
    return {m["nome"]: m["telefono"] for m in squadriglia["membri"]}


def test_squadriglieri_vedono_i_telefoni_degli_altri(ragazza, csq, vice, genitore_con_cellulare):
    vista = _mia(vice)
    assert not vista["sono_capo"]
    assert _telefoni(vista) == {"Sara": None, "Ada": "3335550000", "Giulia": "3330000000"}
    assert vista["genitori"] == []  # only the CSQ
    assert {m["nome"]: m["incarico"] for m in vista["membri"]}["Sara"] == "Capo squadriglia"
    assert "email" not in vista["membri"][0]


def test_il_csq_vede_anche_i_genitori(ragazza, csq, genitore_con_cellulare):
    vista = _mia(csq)
    assert vista["sono_capo"]
    assert vista["genitori"] == [
        {"figlio_id": ragazza.pk, "nome": "Mario", "cognome": "Genitore", "telefono": "3471234567"}
    ]


def test_numero_del_genitore_e_numero_nascosto(ragazza, csq, vice, genitore_con_cellulare):
    ragazza.cellulare = ""  # minors need not have one in BuonaStrada
    ragazza.save()
    assert _telefoni(_mia(vice))["Giulia"] is None  # nobody chose one: no number

    url = f"/api/v1/persone/{ragazza.pk}/telefono-squadriglia"
    impostato = _put(genitore_con_cellulare, url, {"genitore_id": genitore_con_cellulare.pk})
    assert impostato.status_code == 200
    giulia = next(m for m in _mia(vice)["membri"] if m["nome"] == "Giulia")
    assert giulia["telefono"] == "3471234567"
    assert giulia["del_genitore"] == "Mario"

    _put(
        genitore_con_cellulare,
        url,
        {"genitore_id": genitore_con_cellulare.pk, "nascosto": True},
    )
    assert _telefoni(_mia(vice))["Giulia"] is None
    assert _telefoni(_mia(csq))["Giulia"] == "3471234567"  # the CSQ sees it anyway


def test_il_cellulare_in_buonastrada_vince(ragazza, vice, genitore_con_cellulare):
    url = f"/api/v1/persone/{ragazza.pk}/telefono-squadriglia"
    _put(genitore_con_cellulare, url, {"genitore_id": genitore_con_cellulare.pk})
    giulia = next(m for m in _mia(vice)["membri"] if m["nome"] == "Giulia")
    assert giulia["telefono"] == "3330000000"
    assert giulia["del_genitore"] is None


def test_numero_di_famiglia_per_i_figli_senza_cellulare(
    ragazza, csq, vice, genitore_con_cellulare, squadriglia
):
    from apps.anagrafica.models import RelazioneTutela

    seconda = crea_persona("Lucia", "Genitore", cellulare="3489999999")
    RelazioneTutela.objects.create(tutore=seconda, minore=ragazza, tipo="GENITORE")
    RelazioneTutela.objects.create(tutore=genitore_con_cellulare, minore=vice, tipo="GENITORE")
    RelazioneTutela.objects.create(tutore=seconda, minore=vice, tipo="GENITORE")
    for figlio in (ragazza, vice):
        figlio.cellulare = ""
        figlio.save()

    url = f"/api/v1/persone/{ragazza.pk}/telefono-squadriglia"
    _put(seconda_login(seconda), url, {"genitore_id": seconda.pk, "per_tutti_i_figli": True})
    telefoni = _telefoni(_mia(csq))
    assert telefoni["Giulia"] == telefoni["Ada"] == "3489999999"  # both children

    # A choice for one child wins over the family number.
    _put(
        genitore_con_cellulare,
        f"/api/v1/persone/{vice.pk}/telefono-squadriglia",
        {"genitore_id": genitore_con_cellulare.pk},
    )
    telefoni = _telefoni(_mia(csq))
    assert telefoni["Ada"] == "3471234567"
    assert telefoni["Giulia"] == "3489999999"
    impostazione = _client(genitore_con_cellulare).get(url).json()
    assert impostazione["famiglia_id"] == seconda.pk


def seconda_login(persona):
    from apps.accounts.models import User

    persona.utente = User.objects.create_user(email="lucia@example.invalid", password="x")
    persona.save()
    return persona


def test_solo_il_cellulare_di_un_genitore(ragazza, genitore, estraneo):
    estraneo.cellulare = "3390000000"
    estraneo.save()
    url = f"/api/v1/persone/{ragazza.pk}/telefono-squadriglia"
    assert _put(genitore, url, {"genitore_id": estraneo.pk}).status_code == 400


def test_chi_imposta_il_telefono(ragazza, genitore, capo, capogruppo, csq, estraneo, coca):
    url = f"/api/v1/persone/{ragazza.pk}/telefono-squadriglia"
    for chi in (genitore, capo, capogruppo):  # capo = capo unità of her reparto
        risposta = _client(chi).get(url)
        assert risposta.status_code == 200, chi
        assert risposta.json()["in_squadriglia"]
    altro_capo = crea_capo("Carlo", "Altro", "altro@example.invalid")
    for chi in (ragazza, csq, estraneo, altro_capo):  # a minor: her parents decide
        assert _client(chi).get(url).status_code == 404, chi


def test_un_maggiorenne_imposta_il_suo(ragazza):
    ragazza.data_nascita = nato_anni_fa(19)
    ragazza.save()
    url = f"/api/v1/persone/{ragazza.pk}/telefono-squadriglia"
    assert _put(ragazza, url, {"nascosto": True}).json()["nascosto"] is True


def test_fuori_dalla_squadriglia_niente(ragazza, estraneo, capo, reparto):
    assert _client(estraneo).get("/api/v1/mia-squadriglia").json() == []
    assert _client(capo).get("/api/v1/mia-squadriglia").json() == []
    altra = Squadriglia.objects.create(unita=reparto, nome="Volpi", sesso="F")
    assert altra.pk not in [s["id"] for s in _client(ragazza).get("/api/v1/mia-squadriglia").json()]


def test_profilo_dice_le_squadriglie(ragazza, squadriglia, estraneo):
    assert _client(ragazza).get("/api/v1/io").json()["squadriglie"] == [squadriglia.pk]
    assert _client(estraneo).get("/api/v1/io").json()["squadriglie"] == []
