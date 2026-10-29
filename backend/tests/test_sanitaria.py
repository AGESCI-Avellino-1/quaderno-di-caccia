import pytest
from django.test import Client

from apps.permessi.models import AccessoDatoSensibile, Azione

pytestmark = pytest.mark.django_db

DATI = {
    "allergie": [
        {
            "tipo": "ALLERGIA",
            "sostanza": "Arachidi",
            "gravita": "GRAVE",
            "reazione": "Shock anafilattico",
            "cosa_fare": "Adrenalina autoiniettabile nella tasca dello zaino",
        },
        {"tipo": "INTOLLERANZA", "sostanza": "Lattosio", "gravita": "LIEVE"},
    ],
    "farmaci": [{"nome": "Ventolin", "posologia": "2 spruzzi al bisogno", "autonomo": True}],
    "esigenze_alimentari": " Vegetariana ",
}


def _client(persona) -> Client:
    client = Client()
    client.force_login(persona.utente)
    return client


def _scrivi(client, persona, dati=DATI):
    return client.put(
        f"/api/v1/persone/{persona.pk}/sanitarie", dati, content_type="application/json"
    )


def test_il_genitore_compila_il_capo_legge(genitore, ragazza, capo):
    risposta = _scrivi(_client(genitore), ragazza)
    assert risposta.status_code == 200, risposta.content
    assert risposta.json()["inserite_da"] == "Genitore"

    letto = _client(capo).get(f"/api/v1/persone/{ragazza.pk}/sanitarie").json()
    assert letto["compilate"] is True
    assert [a["sostanza"] for a in letto["allergie"]] == ["Arachidi", "Lattosio"]
    assert letto["farmaci"][0]["autonomo"] is True
    assert letto["esigenze_alimentari"] == "Vegetariana"
    assert letto["puo_modificare"] is True  # capo unità of her reparto
    assert AccessoDatoSensibile.objects.filter(
        persona=ragazza, azione=Azione.LETTURA, utente=capo.utente
    ).exists()


def test_non_compilate_diverso_da_nessuna(genitore, ragazza):
    client = _client(genitore)
    assert client.get(f"/api/v1/persone/{ragazza.pk}/sanitarie").json()["compilate"] is False
    _scrivi(client, ragazza, {"nessuna_allergia": True, "nessun_farmaco": True})
    letto = client.get(f"/api/v1/persone/{ragazza.pk}/sanitarie").json()
    assert letto["compilate"] is True
    assert letto["nessuna_allergia"] is True


def test_dati_contraddittori_rifiutati(genitore, ragazza):
    risposta = _scrivi(_client(genitore), ragazza, {"nessuna_allergia": True, **DATI})
    assert risposta.status_code == 400
    assert "nessuna allergia" in risposta.json()["detail"]


def test_esigenze_alimentari_brevi(genitore, ragazza):
    risposta = _scrivi(_client(genitore), ragazza, {"esigenze_alimentari": "x" * 301})
    assert risposta.status_code == 400


def test_trascrizione_del_capo(capo, ragazza):
    assert _scrivi(_client(capo), ragazza).json()["inserite_da"].startswith("Capo")


def test_chi_non_deve_non_vede(csq, estraneo, ragazza, genitore):
    _scrivi(_client(genitore), ragazza)
    for persona in (csq, estraneo, ragazza):  # a 12-year-old: her parents decide (DEC-16)
        assert _client(persona).get(f"/api/v1/persone/{ragazza.pk}/sanitarie").status_code == 404
        assert _scrivi(_client(persona), ragazza).status_code == 404


def test_capo_di_altra_unita_legge_ma_non_scrive(capogruppo, capo, ragazza, coca):
    """Every capo reads (DEC-09); writing is for the unit's capi (DEC-55)."""
    from apps.organizzazione.models import Incarico

    Incarico.objects.filter(persona=capo).delete()
    client = _client(capo)
    assert client.get(f"/api/v1/persone/{ragazza.pk}/sanitarie").status_code == 200
    assert _scrivi(client, ragazza).status_code == 403


def test_scarico_per_il_campo_solo_su_dispositivo_registrato(capo, ragazza, genitore, reparto):
    _scrivi(_client(genitore), ragazza)
    client = _client(capo)
    assert client.get(f"/api/v1/campo/{reparto.pk}").status_code == 403

    client.post("/api/v1/dispositivi", {"nome": "Telefono"}, content_type="application/json")
    risposta = client.get(f"/api/v1/campo/{reparto.pk}")
    assert risposta.status_code == 200
    scheda = next(p for p in risposta.json()["persone"] if p["id"] == ragazza.pk)
    assert scheda["sanitarie"]["allergie"][0]["gravita"] == "GRAVE"
    assert scheda["sanitarie"]["esigenze_alimentari"] == "Vegetariana"  # offline at camp
    assert {c["cellulare"] for c in scheda["contatti"]} >= {ragazza.cellulare}
    assert AccessoDatoSensibile.objects.filter(
        persona=ragazza, azione=Azione.SCARICO_OFFLINE
    ).exists()


def test_scarico_per_il_campo_negato_ai_ragazzi(csq, reparto):
    client = _client(csq)
    client.post("/api/v1/dispositivi", {"nome": "Telefono"}, content_type="application/json")
    assert client.get(f"/api/v1/campo/{reparto.pk}").status_code == 403


def test_registro_accessi_solo_ai_capi(capo, genitore, ragazza):
    _client(genitore).get(f"/api/v1/persone/{ragazza.pk}/sanitarie")
    righe = _client(capo).get(f"/api/v1/persone/{ragazza.pk}/accessi-sensibili").json()
    assert righe[0]["chi"] == genitore.utente.email
    assert (
        _client(genitore).get(f"/api/v1/persone/{ragazza.pk}/accessi-sensibili").status_code == 403
    )
