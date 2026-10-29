"""Corrections to BuonaStrada data (DEC-31).

Who corrects what, forwarding by the capigruppo, discarding with the previous value
back and the daily summary: DEC-129.
"""

from datetime import date

import pytest
from django.core import mail
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import Client

from apps.accounts.models import User
from apps.anagrafica.models import (
    CAMPI_BUONASTRADA,
    CAMPI_CONTATTO,
    CAMPI_IDENTITA,
    CorrezioneAnagrafica,
    StatoCorrezione,
)
from apps.anagrafica.servizi import correggi_campo, scarta_correzione
from apps.organizzazione.models import Incarico, RuoloIncarico
from apps.permessi import policy
from tests.conftest import INIZIO_ANNO, crea_capo

pytestmark = pytest.mark.django_db

TUTTI = set(CAMPI_BUONASTRADA)
SENZA_IDENTITA = TUTTI - set(CAMPI_IDENTITA)
# The unit staff also corrects sex and place of birth (DEC-129).
STAFF = SENZA_IDENTITA | {"sesso", "luogo_nascita"}
CONTATTI_E_CONSENSI = set(CAMPI_CONTATTO) | {
    "consenso_iscrizione",
    "consenso_foto",
    "consenso_commerciale",
    "consenso_riviste",
}


def _client(chi) -> Client:
    client = Client()
    client.force_login(chi if isinstance(chi, User) else chi.utente)
    return client


def _post(chi, url, dati=None):
    return _client(chi).post(url, dati or {}, content_type="application/json")


@pytest.fixture
def staff(reparto, coca):
    persona = crea_capo("Elena", "Staff", "staff@example.invalid")
    Incarico.objects.create(
        persona=persona, ruolo=RuoloIncarico.STAFF, unita=reparto, data_inizio=INIZIO_ANNO
    )
    return persona


@pytest.fixture
def capo_semplice(coca):
    return crea_capo("Carlo", "Semplice", "semplice@example.invalid")


@pytest.fixture
def amministratore(db) -> User:
    return User.objects.create_user(email="admin@example.invalid", amministratore_tecnico=True)


# --- Who corrects what ----------------------------------------------------------------


def test_chi_corregge_i_dati_di_una_ragazza(
    ragazza, capo, staff, capogruppo, csq, genitore, estraneo, capo_semplice, amministratore
):
    campi = policy.campi_correggibili
    assert campi(capogruppo.utente, ragazza) == TUTTI
    assert campi(amministratore, ragazza) == TUTTI
    assert campi(capo.utente, ragazza) == STAFF  # capo unità of her reparto
    assert campi(staff.utente, ragazza) == STAFF
    assert campi(genitore.utente, ragazza) == SENZA_IDENTITA
    assert campi(ragazza.utente, ragazza) == set()  # a minor: her parents do it
    assert campi(csq.utente, ragazza) == set()
    assert campi(capo_semplice.utente, ragazza) == set()  # not her unit's staff
    assert campi(estraneo.utente, ragazza) == set()


def test_un_adulto_corregge_i_suoi_contatti_e_consensi(capo, genitore, ragazza):
    assert policy.campi_correggibili(capo.utente, capo) == CONTATTI_E_CONSENSI
    assert policy.campi_correggibili(genitore.utente, genitore) == CONTATTI_E_CONSENSI
    assert policy.campi_correggibili(ragazza.utente, genitore) == set()


def test_genitore_di_un_maggiorenne_non_corregge(genitore, ragazza):
    ragazza.data_nascita = date(2000, 1, 1)
    ragazza.save()
    assert policy.campi_correggibili(genitore.utente, ragazza) == set()
    assert policy.campi_correggibili(ragazza.utente, ragazza) == CONTATTI_E_CONSENSI


def test_capigruppo_e_amministratore_gestiscono_le_correzioni(
    capogruppo, capo, genitore, amministratore
):
    assert policy.puo_gestire_correzioni(capogruppo.utente)
    assert not policy.puo_gestire_correzioni(capo.utente)
    assert not policy.puo_gestire_correzioni(genitore.utente)
    assert policy.puo_gestire_correzioni(amministratore)


# --- Service ------------------------------------------------------------------------------


def test_correzione_vale_subito_e_tiene_il_valore_di_buonastrada(ragazza, genitore):
    correzione = correggi_campo(ragazza, "cellulare", "3331111111", genitore.utente)
    correggi_campo(ragazza, "cellulare", "3332222222", genitore.utente)
    ragazza.refresh_from_db()
    correzione.refresh_from_db()
    assert ragazza.cellulare == "3332222222"
    assert correzione.valore_precedente == "3330000000"  # still BuonaStrada's value
    assert correzione.valore_corretto == "3332222222"
    assert CorrezioneAnagrafica.objects.count() == 1


def test_tornare_al_valore_di_buonastrada_ritira_la_correzione(ragazza, genitore):
    correggi_campo(ragazza, "cellulare", "3331111111", genitore.utente)
    assert correggi_campo(ragazza, "cellulare", "3330000000", genitore.utente) is None
    assert not CorrezioneAnagrafica.objects.exists()


def test_correzione_inoltrata_e_corretta_di_nuovo_va_reinoltrata(ragazza, genitore, capogruppo):
    correzione = correggi_campo(ragazza, "cellulare", "3331111111", genitore.utente)
    _post(capogruppo, f"/api/v1/correzioni/{correzione.pk}/inoltra")
    correggi_campo(ragazza, "cellulare", "3332222222", genitore.utente)
    correzione.refresh_from_db()
    assert correzione.stato == StatoCorrezione.IN_ATTESA
    assert correzione.inoltrata_il is None


def test_valori_non_validi(ragazza, genitore):
    with pytest.raises(ValidationError):
        correggi_campo(ragazza, "email", "non è un'email", genitore.utente)
    with pytest.raises(ValidationError):
        correggi_campo(ragazza, "data_nascita", "31/02/2014", genitore.utente)
    with pytest.raises(ValidationError):
        correggi_campo(ragazza, "cellulare", "3330000000", genitore.utente)  # unchanged
    assert not CorrezioneAnagrafica.objects.exists()


def test_tipi_convertiti(ragazza, capogruppo):
    correggi_campo(ragazza, "data_nascita", "2013-05-04", capogruppo.utente)
    correggi_campo(ragazza, "consenso_foto", "False", capogruppo.utente)
    ragazza.refresh_from_db()
    assert ragazza.data_nascita == date(2013, 5, 4)
    assert ragazza.consenso_foto is False


def test_scarto_rimette_il_valore_precedente(ragazza, genitore, capogruppo):
    correzione = correggi_campo(ragazza, "cellulare", "3331111111", genitore.utente)
    with pytest.raises(ValidationError):
        scarta_correzione(correzione, capogruppo.utente, " ")  # a reason is needed
    correzione.refresh_from_db()
    scarta_correzione(correzione, capogruppo.utente, "Numero sbagliato")
    ragazza.refresh_from_db()
    assert ragazza.cellulare == "3330000000"
    assert correzione.stato == StatoCorrezione.SCARTATA
    assert correzione.chiusa_da == capogruppo.utente


def test_scarto_di_un_campo_vuoto_nullable(ragazza, capogruppo):
    ragazza.consenso_foto = None
    ragazza.save()
    correzione = correggi_campo(ragazza, "consenso_foto", "True", capogruppo.utente)
    scarta_correzione(correzione, capogruppo.utente, "Non risulta firmato")
    ragazza.refresh_from_db()
    assert ragazza.consenso_foto is None


# --- API ------------------------------------------------------------------------------------


def test_scheda_mostra_solo_i_campi_correggibili(ragazza, genitore, csq):
    risposta = _client(genitore).get(f"/api/v1/persone/{ragazza.pk}/correzioni")
    assert risposta.status_code == 200
    campi = {c["campo"]: c for c in risposta.json()["campi"]}
    assert set(campi) == SENZA_IDENTITA
    assert campi["cellulare"]["valore"] == "3330000000"
    assert campi["consenso_foto"]["tipo"] == "si_no"
    assert campi["stato_socio"]["tipo"] == "scelta"
    assert _client(csq).get(f"/api/v1/persone/{ragazza.pk}/correzioni").status_code == 404


def test_correggere_dall_api(ragazza, genitore):
    url = f"/api/v1/persone/{ragazza.pk}/correzioni"
    risposta = _post(genitore, url, {"campo": "cellulare", "valore": "3331111111"})
    assert risposta.status_code == 200
    campo = next(c for c in risposta.json()["campi"] if c["campo"] == "cellulare")
    assert campo["valore"] == "3331111111"
    assert campo["correzione"]["stato"] == "IN_ATTESA"
    assert campo["correzione"]["richiesta_da"] == "Mario Genitore"

    vietato = _post(genitore, url, {"campo": "codice_fiscale", "valore": "AAAAAA00A00A000A"})
    assert vietato.status_code == 403
    sbagliato = _post(genitore, url, {"campo": "email", "valore": "x"})
    assert sbagliato.status_code == 400
    assert _post(genitore, url, {"campo": "utente", "valore": "1"}).status_code == 403


def test_estraneo_non_sa_che_la_persona_esiste(ragazza, estraneo):
    url = f"/api/v1/persone/{ragazza.pk}/correzioni"
    assert _post(estraneo, url, {"campo": "cellulare", "valore": "1"}).status_code == 404


def test_capigruppo_inoltrano_e_scartano(ragazza, genitore, capogruppo, capo):
    correzione = correggi_campo(ragazza, "cellulare", "3331111111", genitore.utente)
    assert _client(capo).get("/api/v1/correzioni").status_code == 403
    assert _post(capo, f"/api/v1/correzioni/{correzione.pk}/inoltra").status_code == 403

    [voce] = _client(capogruppo).get("/api/v1/correzioni").json()
    assert voce["persona"]["id"] == ragazza.pk
    assert voce["etichetta"] == "Cellulare"

    inoltrata = _post(capogruppo, f"/api/v1/correzioni/{correzione.pk}/inoltra")
    assert inoltrata.json()["stato"] == "INOLTRATA"
    assert _post(capogruppo, f"/api/v1/correzioni/{correzione.pk}/inoltra").status_code == 409

    url_scarto = f"/api/v1/correzioni/{correzione.pk}/scarta"
    assert _post(capogruppo, url_scarto, {"motivo": ""}).status_code == 400
    scartata = _post(capogruppo, url_scarto, {"motivo": "Numero sbagliato"})
    assert scartata.json()["stato"] == "SCARTATA"
    assert _client(capogruppo).get("/api/v1/correzioni").json() == []
    [chiusa] = _client(capogruppo).get("/api/v1/correzioni?aperte=false").json()
    assert chiusa["motivo_scarto"] == "Numero sbagliato"

    # Who asked for it sees why it was discarded.
    scheda = _client(genitore).get(f"/api/v1/persone/{ragazza.pk}/correzioni").json()
    assert scheda["chiuse"][0]["motivo_scarto"] == "Numero sbagliato"


# --- Daily summary ------------------------------------------------------------------------


def test_riepilogo_ai_capigruppo_una_volta_sola(ragazza, genitore, capogruppo):
    call_command("segnala_correzioni")
    assert mail.outbox == []  # nothing to say

    correggi_campo(ragazza, "cellulare", "3331111111", genitore.utente)
    call_command("segnala_correzioni")
    [messaggio] = mail.outbox
    assert messaggio.to == ["cg@example.invalid"]
    assert "1 nuove correzioni" in messaggio.body
    assert "/correzioni" in messaggio.body
    assert "Giulia" not in messaggio.body and "3331111111" not in messaggio.body

    call_command("segnala_correzioni")
    assert len(mail.outbox) == 1  # already mentioned
