"""Joining from the app with a registration code (maintainer, 2026-10-29).

Codes reusable for a unit or personal; the parent registers a minor; the account waits
until the unit staff (capigruppo for the Co.Ca.) approves; the member gets a provisional
codice socio 9 + 9 digits; a capo not yet in BuonaStrada sees no sensitive data.
"""

from datetime import date, timedelta

import pytest
from django.contrib.sessions.backends.db import SessionStore
from django.core import mail
from django.test import Client

from apps.accounts.models import User
from apps.anagrafica.models import Appartenenza, Persona, RelazioneTutela, RuoloAppartenenza
from apps.anagrafica.servizi import (
    codice_fiscale_valido,
    e_codice_provvisorio,
    nuovo_codice_provvisorio,
)
from apps.core.models import FonteDato
from apps.iscrizioni import servizi
from apps.iscrizioni.models import CodiceIscrizione, StatoIscrizione, TipoCodice
from apps.organizzazione.models import Incarico, RuoloIncarico
from apps.permessi import policy
from tests.conftest import INIZIO_ANNO, crea_capo, nato_anni_fa

pytestmark = pytest.mark.django_db

CF_FIGLIO = "BNCMRA14A41A509Q"
CF_GENITORE = "BNCLGU80A01A509Z"
CF_CAPO = "VRDNNA90A41A509K"
DOMANI = date.today() + timedelta(days=1)
TRA_UN_MESE = date.today() + timedelta(days=30)


def _client(chi) -> Client:
    client = Client()
    client.force_login(chi if isinstance(chi, User) else chi.utente)
    return client


def _post(client, url, dati=None):
    return client.post(url, dati or {}, content_type="application/json")


def _dati_figlio(**altri) -> dict:
    return {
        "nome": "Marta",
        "cognome": "Bianco",
        "data_nascita": nato_anni_fa(11).isoformat(),
        "codice_fiscale": CF_FIGLIO.lower(),
        "genitore_nome": "Luigi",
        "genitore_cognome": "Bianco",
        "genitore_codice_fiscale": CF_GENITORE,
        **altri,
    }


@pytest.fixture
def codice_reparto(reparto, capo):
    return CodiceIscrizione.objects.create(
        unita=reparto, tipo=TipoCodice.UNITA, scadenza=TRA_UN_MESE, creato_da=capo.utente
    )


@pytest.fixture
def genitore_nuovo(db) -> User:
    return User.objects.create_user(email="luigi.bianco@example.invalid", password="x")


@pytest.fixture
def richiesta(codice_reparto, genitore_nuovo):
    dati = servizi.DatiIscrizione(**{**_dati_figlio(), "data_nascita": nato_anni_fa(11)})
    return servizi.crea_richiesta(codice_reparto, dati, genitore_nuovo)


# --- Provisional codice socio ---------------------------------------------------------


def test_codice_provvisorio(db):
    primo, secondo = nuovo_codice_provvisorio(), nuovo_codice_provvisorio()
    assert (primo, secondo) == ("9000000001", "9000000002")
    assert e_codice_provvisorio(primo)
    assert not e_codice_provvisorio("9000001")  # a real BuonaStrada code
    assert not e_codice_provvisorio(None)


def test_formato_codice_fiscale():
    assert codice_fiscale_valido(CF_FIGLIO)
    assert not codice_fiscale_valido("RSSMRA")
    assert not codice_fiscale_valido(CF_FIGLIO.lower())


# --- Codes ----------------------------------------------------------------------------


def test_chi_crea_i_codici(reparto, coca, capo, capogruppo, ragazza, genitore, estraneo):
    staff = crea_capo("Elena", "Staff", "staff@example.invalid")
    Incarico.objects.create(
        persona=staff, ruolo=RuoloIncarico.STAFF, unita=reparto, data_inizio=INIZIO_ANNO
    )
    semplice = crea_capo("Carlo", "Semplice", "semplice@example.invalid")
    for chi in (capo, staff, capogruppo):
        assert policy.puo_creare_codici(chi.utente, reparto), chi
    for chi in (semplice, ragazza, genitore, estraneo):
        assert not policy.puo_creare_codici(chi.utente, reparto), chi
    assert policy.puo_creare_codici(capogruppo.utente, coca)
    assert not policy.puo_creare_codici(capo.utente, coca)  # capi: only capigruppo


def test_crea_codice_e_qr(reparto, capo, genitore):
    url = f"/api/v1/unita/{reparto.pk}/codici-iscrizione"
    creato = _post(_client(capo), url, {"tipo": "UNITA", "scadenza": TRA_UN_MESE.isoformat()})
    assert creato.status_code == 201
    codice = creato.json()
    assert len(codice["codice"]) == 8 and codice["link"].endswith(f"/iscrizione/{codice['codice']}")
    qr = _client(capo).get(f"/api/v1/codici-iscrizione/{codice['id']}/qr.svg")
    assert qr["Content-Type"] == "image/svg+xml" and b"<svg" in qr.content
    assert (
        _client(genitore).get(f"/api/v1/codici-iscrizione/{codice['id']}/qr.svg").status_code == 404
    )
    assert _client(genitore).get(url).json() == {"puo_creare": False, "codici": []}


def test_codici_non_validi(codice_reparto, reparto):
    client = Client()
    assert client.get(f"/api/v1/iscrizione/{codice_reparto.codice.lower()}").status_code == 200
    codice_reparto.attivo = False
    codice_reparto.save()
    assert client.get(f"/api/v1/iscrizione/{codice_reparto.codice}").status_code == 404
    personale = CodiceIscrizione.objects.create(
        unita=reparto, tipo=TipoCodice.PERSONALE, scadenza=TRA_UN_MESE, usi=1
    )
    assert not personale.valido  # already used
    scaduto = CodiceIscrizione.objects.create(
        unita=reparto, tipo=TipoCodice.UNITA, scadenza=date.today() - timedelta(days=1)
    )
    assert not scaduto.valido


# --- Asking -----------------------------------------------------------------------------


def test_senza_account_la_richiesta_aspetta_la_registrazione(codice_reparto, rf):
    client = Client()
    risposta = _post(client, f"/api/v1/iscrizione/{codice_reparto.codice}", _dati_figlio())
    assert risposta.json() == {"serve_account": True, "richiesta_id": None}

    # The sign-up (allauth) runs in the same session: the adapter turns it into a request.
    from apps.accounts.adapters import AccountAdapter

    richiesta_http = rf.post("/")
    richiesta_http.session = SessionStore(session_key=client.session.session_key)
    adapter = AccountAdapter()
    assert adapter.is_open_for_signup(richiesta_http)
    utente = User.objects.create_user(email="luigi.bianco@example.invalid")
    creata = servizi.richiesta_da_sessione(richiesta_http, utente)
    assert creata.codice_fiscale == CF_FIGLIO  # normalised
    assert creata.stato == StatoIscrizione.IN_ATTESA and creata.per_minore
    codice_reparto.refresh_from_db()
    assert codice_reparto.usi == 1


def test_con_account_il_genitore_iscrive_un_altro_figlio(codice_reparto, genitore):
    risposta = _post(
        _client(genitore), f"/api/v1/iscrizione/{codice_reparto.codice}", _dati_figlio()
    )
    assert risposta.json()["serve_account"] is False
    [mia] = _client(genitore).get("/api/v1/mie-iscrizioni").json()
    assert mia["stato"] == "IN_ATTESA" and mia["genitore"] == "Luigi Bianco"
    assert mia["email"] == ""  # never the parent's address


def test_dati_non_validi(codice_reparto, coca, capogruppo, ragazza):
    url = f"/api/v1/iscrizione/{codice_reparto.codice}"
    client = Client()
    assert _post(client, url, _dati_figlio(codice_fiscale="X")).status_code == 400
    assert _post(client, url, _dati_figlio(genitore_codice_fiscale="")).status_code == 400
    gia = _dati_figlio(codice_fiscale="RSSGLI13E50A509A")
    ragazza.codice_fiscale = "RSSGLI13E50A509A"
    ragazza.save()
    assert "già" in _post(client, url, gia).json()["detail"]
    in_coca = CodiceIscrizione.objects.create(unita=coca, tipo="UNITA", scadenza=TRA_UN_MESE)
    minore = _post(client, f"/api/v1/iscrizione/{in_coca.codice}", _dati_figlio())
    assert minore.status_code == 400  # only adults in the Co.Ca.


# --- Approval ----------------------------------------------------------------------------


def test_lo_staff_approva_e_nasce_il_socio_provvisorio(richiesta, capo, reparto):
    url = f"/api/v1/iscrizioni/{richiesta.pk}/approva"
    assert _post(_client(capo), url).status_code == 400  # a deadline is needed
    approvata = _post(_client(capo), url, {"scadenza_completamento": TRA_UN_MESE.isoformat()})
    assert approvata.status_code == 200
    assert approvata.json()["stato"] == "APPROVATA"

    figlia = Persona.objects.get(codice_fiscale=CF_FIGLIO)
    assert e_codice_provvisorio(figlia.codice_socio)
    appartenenza = Appartenenza.objects.attive().get(persona=figlia)
    assert (appartenenza.unita, appartenenza.ruolo, appartenenza.fonte) == (
        reparto,
        RuoloAppartenenza.RAGAZZO,
        FonteDato.APP,
    )
    genitore = Persona.objects.get(codice_fiscale=CF_GENITORE)
    assert genitore.utente == richiesta.utente and not genitore.codice_socio
    assert RelazioneTutela.objects.filter(tutore=genitore, minore=figlia).exists()
    assert policy.tutelati(richiesta.utente).filter(pk=figlia.pk).exists()
    [email] = mail.outbox
    assert email.to == ["luigi.bianco@example.invalid"] and "accolta" in email.subject


def test_rifiuto_con_motivo(richiesta, capo):
    url = f"/api/v1/iscrizioni/{richiesta.pk}/rifiuta"
    assert _post(_client(capo), url, {"motivo": " "}).status_code == 400
    assert _post(_client(capo), url, {"motivo": "Reparto al completo"}).json()["stato"] == (
        "RIFIUTATA"
    )
    assert "Reparto al completo" in mail.outbox[0].body
    assert not Persona.objects.filter(codice_fiscale=CF_FIGLIO).exists()


def test_chi_approva(richiesta, capo, capogruppo, coca, genitore, estraneo):
    altro = crea_capo("Carlo", "Altro", "altro@example.invalid")
    url = f"/api/v1/iscrizioni/{richiesta.pk}/approva"
    for chi in (altro, genitore, estraneo):
        assert (
            _post(_client(chi), url, {"scadenza_completamento": DOMANI.isoformat()}).status_code
            == 404
        )
    assert [r["id"] for r in _client(capo).get("/api/v1/iscrizioni").json()] == [richiesta.pk]
    assert _client(altro).get("/api/v1/iscrizioni").json() == []
    assert _client(capogruppo).get("/api/v1/io").json()["iscrizioni_da_decidere"] == 1


# --- A capo not yet in BuonaStrada ------------------------------------------------------


@pytest.fixture
def capo_nuovo(coca, capogruppo):
    """A capo who joined the Co.Ca. from the app, approved by a capogruppo."""
    codice = CodiceIscrizione.objects.create(unita=coca, tipo="PERSONALE", scadenza=TRA_UN_MESE)
    utente = User.objects.create_user(email="anna.verdi@example.invalid", password="x")
    dati = servizi.DatiIscrizione(
        nome="Anna", cognome="Verdi", data_nascita=date(1990, 1, 1), codice_fiscale=CF_CAPO
    )
    richiesta = servizi.crea_richiesta(codice, dati, utente)
    assert not policy.puo_approvare_iscrizione(
        crea_capo("Carlo", "Staff", "c@example.invalid").utente, coca
    )
    servizi.approva(richiesta, capogruppo.utente, TRA_UN_MESE)
    return Persona.objects.get(codice_fiscale=CF_CAPO)


def test_capo_in_attesa_senza_dati_delicati(capo_nuovo, ragazza, reparto, genitore):
    utente = capo_nuovo.utente
    assert policy.e_capo(utente) and policy.e_capo_in_attesa(utente)
    client = _client(utente)
    assert client.get(f"/api/v1/unita/{reparto.pk}").status_code == 200  # organisation: yes
    dettaglio = client.get(f"/api/v1/persone/{ragazza.pk}").json()
    assert dettaglio["nome"] == "Giulia" and dettaglio["cellulare"] is None
    assert client.get(f"/api/v1/persone/{ragazza.pk}/sanitarie").status_code == 404
    assert not policy.puo_scaricare_campo(utente)
    assert not policy.puo_vedere_deroghe_squadriglia(utente)
    assert not policy.puo_vedere_registro_accessi(utente)
    # Their own data: yes, flagged as provisional.
    proprio = client.get(f"/api/v1/persone/{capo_nuovo.pk}").json()
    assert proprio["codice_provvisorio"] is True
    assert client.get("/api/v1/io").json()["capo_in_attesa"] is True


def test_capo_in_attesa_anche_se_staff(capo_nuovo, ragazza, reparto):
    Incarico.objects.create(
        persona=capo_nuovo, ruolo=RuoloIncarico.STAFF, unita=reparto, data_inizio=INIZIO_ANNO
    )
    assert not policy.puo_modificare_sanitarie(capo_nuovo.utente, ragazza)
    assert policy.campi_correggibili(capo_nuovo.utente, ragazza) == set()
    assert not policy.puo_creare_codici(capo_nuovo.utente, reparto)


def test_con_il_codice_vero_vede_tutto(capo_nuovo, ragazza):
    capo_nuovo.codice_socio = "9000123"  # from BuonaStrada
    capo_nuovo.save()
    assert policy.e_capo_censito(capo_nuovo.utente)
    assert policy.puo_vedere_dati_sensibili(capo_nuovo.utente, ragazza)


def test_un_adulto_con_account_si_iscrive_con_la_sua_email(coca, capogruppo, genitore):
    codice = CodiceIscrizione.objects.create(unita=coca, tipo="UNITA", scadenza=TRA_UN_MESE)
    dati = {
        "nome": "Mario",
        "cognome": "Genitore",
        "data_nascita": "1980-01-01",
        "codice_fiscale": "GNTMRA80A01A509X",
    }
    risposta = _post(_client(genitore), f"/api/v1/iscrizione/{codice.codice}", dati)
    assert risposta.json()["serve_account"] is False
    [mia] = _client(genitore).get("/api/v1/mie-iscrizioni").json()
    assert mia["email"] == "genitore@example.invalid"


# --- Completion, reminders, suspension (step 2) ----------------------------------------


@pytest.fixture
def approvata(richiesta, capo):
    servizi.approva(richiesta, capo.utente, TRA_UN_MESE)
    richiesta.refresh_from_db()
    mail.outbox.clear()
    return richiesta


DATI_COMPLETI = {
    "sesso": "F",
    "luogo_nascita": "Avellino",
    "indirizzo": "Via Roma",
    "civico": "1",
    "comune": "Avellino",
    "provincia": "av",
    "cap": "83100",
    "cellulare_genitore": "3471112222",
}


def _put(client, url, dati):
    return client.put(url, dati, content_type="application/json")


def test_la_famiglia_completa_i_dati(approvata, genitore_nuovo):
    client = _client(genitore_nuovo)
    url = f"/api/v1/iscrizioni/{approvata.pk}/completamento"
    stato = client.get(url).json()
    assert "Sesso" in stato["richiesta"]["mancanti"]
    assert "Cellulare del genitore" in stato["richiesta"]["mancanti"]

    assert _put(client, url, {**DATI_COMPLETI, "cap": "831"}).status_code == 400
    completo = _put(client, url, DATI_COMPLETI).json()
    assert completo["provincia"] == "AV"
    assert completo["richiesta"]["stato"] == "COMPLETATA"
    assert completo["richiesta"]["mancanti"] == []
    assert Persona.objects.get(codice_fiscale=CF_GENITORE).cellulare == "3471112222"


def test_chi_completa(approvata, capo, estraneo, genitore):
    url = f"/api/v1/iscrizioni/{approvata.pk}/completamento"
    assert _client(capo).get(url).status_code == 200  # who approves may help
    for chi in (estraneo, genitore):
        assert _client(chi).get(url).status_code == 404


def test_promemoria_e_sospensione(approvata, genitore_nuovo):
    from django.core.management import call_command

    scadenza = approvata.scadenza_completamento
    call_command("promemoria_iscrizioni", oggi=scadenza - timedelta(days=8))
    assert mail.outbox == []
    call_command("promemoria_iscrizioni", oggi=scadenza - timedelta(days=7))
    [promemoria] = mail.outbox
    assert "completa" in promemoria.subject and promemoria.to == ["luigi.bianco@example.invalid"]
    call_command("promemoria_iscrizioni", oggi=scadenza - timedelta(days=3))
    assert len(mail.outbox) == 1  # once

    assert policy.persona_di(genitore_nuovo) is not None
    call_command("promemoria_iscrizioni", oggi=scadenza)
    approvata.refresh_from_db()
    assert approvata.stato == StatoIscrizione.SOSPESA
    assert "sospesa" in mail.outbox[-1].subject
    # The account waits again: nothing but its registration.
    assert policy.persona_di(genitore_nuovo) is None
    client = _client(genitore_nuovo)
    figlia = approvata.persona
    assert client.get(f"/api/v1/persone/{figlia.pk}").status_code == 404
    assert client.get("/api/v1/mie-iscrizioni").json()[0]["stato"] == "SOSPESA"

    # Completing late gives everything back.
    url = f"/api/v1/iscrizioni/{approvata.pk}/completamento"
    assert _put(client, url, DATI_COMPLETI).json()["richiesta"]["stato"] == "COMPLETATA"
    assert client.get(f"/api/v1/persone/{figlia.pk}").status_code == 200


def test_completa_non_sospende(approvata, genitore_nuovo):
    from django.core.management import call_command

    servizi.completa(approvata, DATI_COMPLETI)
    call_command("promemoria_iscrizioni", oggi=approvata.scadenza_completamento)
    approvata.refresh_from_db()
    assert approvata.stato == StatoIscrizione.COMPLETATA
    assert mail.outbox == []


def test_avviso_agli_approvatori(richiesta, capo, capogruppo):
    from django.core.management import call_command

    call_command("promemoria_iscrizioni")
    destinatari = sorted(m.to[0] for m in mail.outbox)
    assert destinatari == ["capo@example.invalid", "cg@example.invalid"]
    assert all("Marta" not in m.body for m in mail.outbox)  # no names by email
    call_command("promemoria_iscrizioni")
    assert len(mail.outbox) == 2  # once
