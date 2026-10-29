from datetime import date, timedelta

import pytest
from django.test import Client

from apps.accounts.adapters import CHIAVE_SESSIONE_INVITO, AccountAdapter
from apps.accounts.models import Invito, User
from tests.export_sintetico import costruisci_csv, righe_standard

pytestmark = pytest.mark.django_db


def _client(persona) -> Client:
    client = Client()
    client.force_login(persona.utente)
    return client


def test_salute_pubblica(db):
    assert Client().get("/api/v1/salute").json() == {"stato": "ok"}


def test_api_richiede_autenticazione(db):
    assert Client().get("/api/v1/io").status_code == 401


def test_profilo_del_capo(capo):
    dati = _client(capo).get("/api/v1/io").json()
    assert dati["capo"] is True
    assert dati["persona"]["cognome"] == "Capo"
    assert dati["branca"] == "capi"


def test_tema_della_branca_del_ragazzo(ragazza):
    assert _client(ragazza).get("/api/v1/io").json()["branca"] == "eg"


def test_profilo_del_genitore(genitore, ragazza):
    dati = _client(genitore).get("/api/v1/io").json()
    assert dati["capo"] is False
    assert dati["branca"] == "generico"
    assert [t["nome"] for t in dati["tutelati"]] == ["Giulia"]


def test_unita_solo_ai_capi(capo, ragazza):
    assert _client(capo).get("/api/v1/unita").status_code == 200
    assert _client(ragazza).get("/api/v1/unita").status_code == 403


def test_dettaglio_persona_secondo_il_livello(capo, csq, ragazza, estraneo):
    completo = _client(capo).get(f"/api/v1/persone/{ragazza.pk}").json()
    assert completo["cellulare"] == "3330000000"
    squadriglia = _client(csq).get(f"/api/v1/persone/{ragazza.pk}").json()
    assert squadriglia["livello_accesso"] == "squadriglia"
    assert squadriglia["cellulare"] is None
    assert squadriglia["data_nascita"] is None
    assert _client(estraneo).get(f"/api/v1/persone/{ragazza.pk}").status_code == 404


def test_elenco_persone_filtrato(genitore, ragazza, capo):
    nomi = {p["nome"] for p in _client(genitore).get("/api/v1/persone").json()}
    assert nomi == {"Mario", "Giulia"}


def test_importazione_anteprima_e_applica(capogruppo, capo):
    from django.core.files.uploadedfile import SimpleUploadedFile

    def file_csv():
        return SimpleUploadedFile("RicercaSoci.csv", costruisci_csv(righe_standard()))

    assert _client(capo).post("/api/v1/importazioni", {"file": file_csv()}).status_code == 403
    futura = date.today() + timedelta(days=1)
    rifiutata = _client(capogruppo).post(
        "/api/v1/importazioni", {"file": file_csv(), "aggiornato_al": futura.isoformat()}
    )
    assert rifiutata.status_code == 400
    risposta = _client(capogruppo).post("/api/v1/importazioni", {"file": file_csv()})
    assert risposta.status_code == 201, risposta.content
    importazione = risposta.json()
    assert importazione["stato"] == "ANTEPRIMA"
    assert len(importazione["riepilogo"]["persone_create"]) == 4
    assert importazione["dati_aggiornati_al"] == date.today().isoformat()
    url = f"/api/v1/importazioni/{importazione['id']}/applica"
    applicata = _client(capogruppo).post(url, {"scelte": {}}, content_type="application/json")
    assert applicata.json()["stato"] == "APPLICATA"
    again = _client(capogruppo).post(url, {}, content_type="application/json")
    assert again.status_code == 409


def test_flusso_invito(capo, ragazza, genitrice_senza_account):
    risposta = _client(capo).post(
        "/api/v1/inviti",
        {
            "persona_id": genitrice_senza_account.pk,
            "email": "nuovo.genitore@example.invalid",
        },
        content_type="application/json",
    )
    assert risposta.status_code == 201, risposta.content
    token = risposta.json()["token"]

    browser = Client()
    accettato = browser.post(
        "/api/v1/inviti/accetta", {"token": token}, content_type="application/json"
    )
    assert accettato.status_code == 200
    assert browser.session[CHIAVE_SESSIONE_INVITO] == token


def test_registrazione_aperta_solo_con_invito(rf, genitore):
    from django.contrib.sessions.backends.db import SessionStore

    adapter = AccountAdapter()
    richiesta = rf.get("/")
    richiesta.session = SessionStore()
    assert not adapter.is_open_for_signup(richiesta)

    invito = Invito.objects.create(email="g@example.invalid", persona=genitore)
    richiesta.session[CHIAVE_SESSIONE_INVITO] = invito.token
    assert adapter.is_open_for_signup(richiesta)

    from apps.accounts.adapters import collega_invito

    nuovo = User.objects.create_user(email="g@example.invalid")
    genitore.utente = None
    genitore.save()
    collega_invito(richiesta, nuovo)
    genitore.refresh_from_db()
    invito.refresh_from_db()
    assert genitore.utente == nuovo
    assert invito.usato_il is not None
    assert not adapter.is_open_for_signup(richiesta)


def test_documentazione_api_nascosta_in_produzione(db):
    # Test settings run with DEBUG=False, like production.
    assert Client().get("/api/v1/docs").status_code == 404
    assert Client().get("/api/v1/openapi.json").status_code == 404
