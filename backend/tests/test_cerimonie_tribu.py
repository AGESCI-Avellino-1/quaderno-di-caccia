"""The tribe lived the totem ceremony (DEC-438): who has a totem name or «Modifica totem» on is
in its register by themselves, «nella tribù» with no day, and reads it; who is marked by hand
with no totem name writes their own, once."""

import pytest

from apps.cerimonie.models import PartecipazioneVoce, VoceLibro
from apps.tribu import servizi as tribu
from tests.test_cerimonie import URL, _accendi, _client, _titoli

pytestmark = pytest.mark.django_db


@pytest.fixture
def totem():
    _accendi()
    return VoceLibro.objects.create(
        titolo="Cerimonia del totem", cerimonia_del_totem=True, testo="<p>Il fuoco</p>"
    )


@pytest.fixture
def altra(totem):
    """An entry read by who lived the totem ceremony."""
    return VoceLibro.objects.create(
        titolo="Dopo il totem", condizioni=[[{"tipo": "partecipazione", "voce": totem.pk}]]
    )


def test_chi_ha_il_totem_l_ha_vissuta(capo, capogruppo, ragazza, csq, totem, altra):
    assert _titoli(ragazza) == set()
    tribu.assegna(ragazza, "Castoro Operoso")
    # In the register by themselves, with no day; the condition holds too.
    assert _titoli(ragazza) == {"Cerimonia del totem", "Dopo il totem"}
    registro = _client(capo).get(f"{URL}/{totem.pk}").json()["partecipanti"]
    assert [(p["id"], p["data"], p["tribu"]) for p in registro] == [(ragazza.pk, None, True)]
    # The participant sees the others of the register, never anyone else.
    tribu.assegna(csq, "Volpe Astuta")
    voce = _client(ragazza).get(f"{URL}/{totem.pk}").json()
    assert voce["vede_registro"] and {p["id"] for p in voce["partecipanti"]} == {
        ragazza.pk,
        csq.pk,
    }
    # A capogruppo marks someone with a day: that day is shown, once.
    _client(capogruppo).post(
        f"{URL}/{totem.pk}/partecipanti",
        {"persone": [ragazza.pk], "data": "2024-05-10"},
        "application/json",
    )
    registro = _client(capo).get(f"{URL}/{totem.pk}").json()["partecipanti"]
    assert [(p["id"], p["data"]) for p in registro] == [(ragazza.pk, "2024-05-10"), (csq.pk, None)]
    # Without the name, out by themselves; who was marked stays.
    tribu.assegna(csq, "")
    tribu.assegna(ragazza, "")
    registro = _client(capo).get(f"{URL}/{totem.pk}").json()["partecipanti"]
    assert [p["id"] for p in registro] == [ragazza.pk]
    assert _titoli(csq) == set()


def test_modifica_totem_accesa(capo, ragazza, totem, altra):
    tribu.attiva_modifica(ragazza, True)
    assert _titoli(ragazza) == {"Cerimonia del totem", "Dopo il totem"}
    tribu.attiva_modifica(ragazza, False)
    assert _titoli(ragazza) == set()


def test_solo_la_cerimonia_del_totem(capo, ragazza, totem):
    """Another entry of the book does not take in the tribe."""
    altra = VoceLibro.objects.create(titolo="Promessa")
    tribu.assegna(ragazza, "Castoro Operoso")
    assert _client(capo).get(f"{URL}/{altra.pk}").json()["partecipanti"] == []
    assert "Promessa" not in _titoli(ragazza)


def test_segnato_senza_totem_se_lo_scrive(capo, ragazza, totem):
    url = f"/api/v1/persone/{ragazza.pk}/totem"
    assert _client(ragazza).get(url).status_code == 404
    PartecipazioneVoce.objects.create(voce=totem, persona=ragazza, data="2025-05-10")
    dati = _client(ragazza).get(url).json()
    assert dati["puo_scrivere"] and not dati["id"]
    assert _client(ragazza).get("/api/v1/tribu").status_code == 200
    risposta = _client(ragazza).put(url, {"nome": "Castoro Operoso"}, "application/json")
    assert risposta.status_code == 200 and risposta.json()["nome"] == "Castoro Operoso"
    # Once: changing it again needs the switch.
    assert not risposta.json()["puo_scrivere"]
    risposta = _client(ragazza).put(url, {"nome": "Castoro Pigro"}, "application/json")
    assert risposta.status_code == 403


def test_libro_spento(capo, ragazza, totem):
    from apps.impostazioni import funzioni

    PartecipazioneVoce.objects.create(voce=totem, persona=ragazza, data="2025-05-10")
    funzioni.imposta(funzioni.CERIMONIE, False)
    assert _client(ragazza).get(f"/api/v1/persone/{ragazza.pk}/totem").status_code == 404
