"""Settings of the installation: names, titles, footer (DEC-245…DEC-248)."""

from datetime import date

import pytest
from django.test import Client

from apps.accounts.models import User
from apps.impostazioni.models import Impostazioni
from apps.organizzazione.models import Incarico, RuoloIncarico
from apps.permessi import policy
from tests.conftest import crea_capo

URL = "/api/v1/impostazioni"


def _client(utente) -> Client:
    client = Client()
    client.force_login(utente)
    return client


def _put(utente, dati):
    return _client(utente).put(f"{URL}/sito", dati, content_type="application/json")


DATI = {
    "nome_sito": "Quaderno di Caccia",
    "sigla_sito": "QdC",
    "nome_gruppo": "AGESCI Prova 1",
    "sigla_gruppo": "PR1",
    "titolo_completo": "[Nome sito] - [Gruppo]",
    "titolo_breve": "[Pagina corrente] · [Sigla sito] - [Sigla gruppo]",
    "riga_piede": "Anno [Anno]",
}


@pytest.fixture
def amministratore(db) -> User:
    return User.objects.create_user(email="admin@example.invalid", amministratore_tecnico=True)


@pytest.fixture
def tesoriere_gruppo(coca, gruppo):
    persona = crea_capo("Teresa", "Tesoriera", "tg@example.invalid")
    Incarico.objects.create(
        persona=persona,
        ruolo=RuoloIncarico.TESORIERE_GRUPPO,
        gruppo=gruppo,
        data_inizio=date(2025, 10, 1),
    )
    return persona


def test_sito_di_base_anche_senza_accesso(gruppo):
    dati = Client().get("/api/v1/sito").json()
    assert dati["nome_sito"] == "Quaderno di Caccia"
    assert dati["sigla_sito"] == "QdC"
    # The title's group name is not the official one, but starts from it.
    assert dati["gruppo"] == "AGESCI Prova 1"
    assert dati["titolo_completo"] == "[Nome sito] - [Gruppo]"
    assert dati["titolo_breve"] == "[Sigla sito] - [Sigla gruppo]"
    assert "/" in dati["anno"]
    assert dati["banner_installazione_giorni"] == 14


def test_sito_giorni_del_banner_di_installazione(gruppo, settings):
    settings.QDC_BANNER_INSTALLAZIONE_GIORNI = 30
    assert Client().get("/api/v1/sito").json()["banner_installazione_giorni"] == 30


def test_policy_impostazioni(
    capo, capogruppo, ragazza, csq, genitore, estraneo, amministratore, tesoriere_gruppo
):
    assert policy.puo_modificare_impostazioni(capogruppo.utente)
    assert policy.puo_modificare_impostazioni(amministratore)
    for chi in (capo, ragazza, csq, genitore, estraneo, tesoriere_gruppo):
        assert not policy.puo_modificare_impostazioni(chi.utente)
    # The treasurer opens the page for the payment link alone.
    assert policy.vede_impostazioni(tesoriere_gruppo.utente)
    for chi in (capo, ragazza, csq, genitore, estraneo):
        assert not policy.vede_impostazioni(chi.utente)


def test_chi_cambia_le_impostazioni(
    gruppo, capo, capogruppo, ragazza, csq, genitore, estraneo, amministratore, tesoriere_gruppo
):
    for chi in (capo, ragazza, csq, genitore, estraneo, tesoriere_gruppo):
        assert _put(chi.utente, DATI).status_code == 403
    for chi in (capo, ragazza, csq, genitore, estraneo):
        assert _client(chi.utente).get(URL).status_code == 403
    letto = _client(tesoriere_gruppo.utente).get(URL).json()
    assert letto["puo_modificare"] is False and letto["puo_modificare_pagamenti"] is True

    risposta = _put(capogruppo.utente, DATI)
    assert risposta.status_code == 200
    assert risposta.json()["puo_modificare_intestazione"] is True
    assert Impostazioni.carica().sigla_gruppo == "PR1"
    assert _put(amministratore, {**DATI, "sigla_gruppo": "AV1"}).status_code == 200
    letto = _client(amministratore).get(URL).json()
    # The technical administrator does not touch the prints (capigruppo only).
    assert letto["puo_modificare_intestazione"] is False
    assert Client().get("/api/v1/sito").json()["sigla_gruppo"] == "AV1"


def test_segnaposto_sconosciuto_non_si_salva(gruppo, capogruppo):
    risposta = _put(capogruppo.utente, {**DATI, "titolo_breve": "[Sigla] - [Gruppo]"})
    assert risposta.status_code == 400
    assert "[Sigla]" in risposta.json()["detail"]
    # Case does not matter.
    assert _put(capogruppo.utente, {**DATI, "titolo_breve": "[sigla sito]"}).status_code == 200


def test_segnaposto_release_nel_piede_e_non_nelle_pagine(gruppo, capogruppo):
    assert _put(capogruppo.utente, {**DATI, "riga_piede": "Versione [Release]"}).status_code == 200
    # The PWA fills it in: the server keeps it as written, here and in the public answer.
    assert Client().get("/api/v1/sito").json()["riga_piede"] == "Versione [Release]"
    # The pages are filled in by the server, which does not know the device's version.
    for nome in ("Release", "Pagina corrente"):
        risposta = _client(capogruppo.utente).put(
            "/api/v1/impostazioni/pagine/privacy",
            {"testo": f"<p>Versione [{nome}]</p>"},
            content_type="application/json",
        )
        assert risposta.status_code == 400
        assert f"[{nome}]" in risposta.json()["detail"]


def test_nome_del_gruppo_vuoto_torna_quello_di_base(gruppo, capogruppo):
    assert _put(capogruppo.utente, {**DATI, "nome_gruppo": "  "}).status_code == 200
    assert Client().get("/api/v1/sito").json()["gruppo"] == "AGESCI Prova 1"


def test_denominazione_ufficiale_separata(gruppo, capogruppo):
    url = "/api/v1/gruppo/intestazione"
    client = _client(capogruppo.utente)
    risposta = client.put(url, {"denominazione": "Prova Uno"}, content_type="application/json")
    assert risposta.status_code == 200 and risposta.json()["denominazione"] == "Prova Uno"
    vuota = client.put(url, {"denominazione": " "}, content_type="application/json")
    assert vuota.status_code == 400
    # Without the field (older clients) it stays.
    assert client.put(url, {}, content_type="application/json").json()["denominazione"] == (
        "Prova Uno"
    )


# --- Email test mode with Mailpit (DEC-249) ------------------------------------------------

MAILERS_DI_PROVA = {
    "default": {"BACKEND": "apps.impostazioni.posta.PostaQdC"},
    "reale": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"},
    "mailpit": {"BACKEND": "django.core.mail.backends.dummy.EmailBackend"},
}


def _attiva(utente, attiva=True):
    return _client(utente).put(
        f"{URL}/email-di-prova", {"attiva": attiva}, content_type="application/json"
    )


def test_solo_l_amministratore_accende_le_email_di_prova(
    gruppo, capo, capogruppo, ragazza, genitore, estraneo, amministratore, settings
):
    settings.QDC_MAILPIT_CONSENTITO = True
    for chi in (capo, capogruppo, ragazza, genitore, estraneo):
        assert _attiva(chi.utente).status_code == 403
    assert policy.puo_gestire_email_di_prova(amministratore)
    risposta = _attiva(amministratore)
    assert risposta.status_code == 200 and risposta.json()["email_di_prova"] is True
    # Everyone, even before the login, sees that emails are not delivered.
    assert Client().get("/api/v1/sito").json()["email_di_prova"] is True
    assert _client(capogruppo.utente).get(URL).json()["puo_email_di_prova"] is False


def test_email_di_prova_solo_dove_il_server_la_permette(gruppo, amministratore, settings):
    settings.QDC_MAILPIT_CONSENTITO = False
    assert _attiva(amministratore).status_code == 400
    # Switched on where allowed, then the server stops allowing it: off for everyone.
    settings.QDC_MAILPIT_CONSENTITO = True
    assert _attiva(amministratore).status_code == 200
    settings.QDC_MAILPIT_CONSENTITO = False
    assert Client().get("/api/v1/sito").json()["email_di_prova"] is False
    assert _attiva(amministratore, attiva=False).status_code == 200


def test_le_email_vanno_a_mailpit_solo_in_prova(db, settings):
    from django.core import mail
    from django.core.mail import send_mail

    settings.MAILERS = MAILERS_DI_PROVA
    settings.QDC_MAILPIT_CONSENTITO = True
    send_mail("Prova", "Testo", None, ["a@example.invalid"])
    assert len(mail.outbox) == 1
    imp = Impostazioni.carica()
    imp.email_di_prova = True
    imp.save()
    send_mail("Prova", "Testo", None, ["a@example.invalid"])
    assert len(mail.outbox) == 1  # caught by Mailpit (here a dummy), not delivered
    settings.QDC_MAILPIT_CONSENTITO = False
    send_mail("Prova", "Testo", None, ["a@example.invalid"])
    assert len(mail.outbox) == 2


def test_mailpit_solo_per_l_amministratore(gruppo, capogruppo, amministratore, settings):
    from unittest import mock

    settings.QDC_MAILPIT_CONSENTITO = True
    assert Client().get("/mailpit/").status_code == 404
    assert _client(capogruppo.utente).get("/mailpit/").status_code == 404
    risposta = mock.MagicMock(status=200, headers={"Content-Type": "text/html"})
    risposta.read.return_value = b"<html>Mailpit</html>"
    risposta.__enter__.return_value = risposta
    with mock.patch("urllib.request.urlopen", return_value=risposta) as apri:
        pagina = _client(amministratore).get("/mailpit/api/v1/messages?limit=5")
    assert pagina.status_code == 200 and pagina.content == b"<html>Mailpit</html>"
    assert apri.call_args.args[0].full_url == (
        "http://localhost:8025/mailpit/api/v1/messages?limit=5"
    )
    settings.QDC_MAILPIT_CONSENTITO = False
    assert _client(amministratore).get("/mailpit/").status_code == 404


# --- Privacy policy and terms (DEC-266) -----------------------------------------------------


def test_pagine_pubbliche_di_base(gruppo):
    gruppo.email = "gruppo@example.invalid"
    gruppo.save()
    for chiave, titolo in (("privacy", "Privacy policy"), ("termini", "Termini e condizioni")):
        pagina = Client().get(f"/api/v1/pagine/{chiave}").json()
        assert pagina["titolo"] == titolo and pagina["aggiornata_il"] is None
        assert "AGESCI Prova 1" in pagina["html"] and "gruppo@example.invalid" in pagina["html"]
        assert "[" not in pagina["html"]
    assert Client().get("/api/v1/pagine/altro").status_code == 404


def test_chi_cambia_privacy_e_termini(gruppo, capo, capogruppo, genitore, amministratore):
    url = "/api/v1/impostazioni/pagine/privacy"
    nuovo = {"testo": "<p>Titolare: AGESCI. [Gruppo]</p><script>x</script>"}
    for chi in (capo, genitore):
        assert (
            _client(chi.utente).put(url, nuovo, content_type="application/json").status_code == 403
        )
    salvata = _client(capogruppo.utente).put(url, nuovo, content_type="application/json").json()
    assert salvata["personalizzata"] and "script" not in salvata["testo"]
    pubblica = Client().get("/api/v1/pagine/privacy").json()
    assert pubblica["html"] == "<p>Titolare: AGESCI. AGESCI Prova 1</p>"
    # The cookie banner shows again after a change.
    assert Client().get("/api/v1/sito").json()["privacy_aggiornata_il"]
    ignoto = {"testo": "<p>[Firma]</p>"}
    assert (
        _client(amministratore).put(url, ignoto, content_type="application/json").status_code == 400
    )
    assert _client(amministratore).delete(url).json()["personalizzata"] is False


# --- Who receives the emails (DEC-276) -------------------------------------------------------

MAILERS_VERI = {
    "default": {"BACKEND": "apps.impostazioni.posta.PostaQdC"},
    "reale": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"},
    "mailpit": {"BACKEND": "django.core.mail.backends.dummy.EmailBackend"},
}


def _manda(tipo: str | None, *indirizzi: str) -> list[str]:
    """Send one email per address; return the addresses that got one."""
    from django.core import mail
    from django.core.mail import EmailMessage, mailers

    from apps.impostazioni.posta import INTESTAZIONE_TIPO

    mail.outbox = []
    intestazioni = {INTESTAZIONE_TIPO: tipo} if tipo else {}
    mailers.default.send_messages(
        [EmailMessage("Prova", "Testo", to=[a], headers=dict(intestazioni)) for a in indirizzi]
    )
    for email in mail.outbox:
        assert INTESTAZIONE_TIPO not in email.extra_headers  # never leaves the server
    return sorted(a for email in mail.outbox for a in email.to)


def _accendi(**gruppi):
    imp = Impostazioni.carica()
    for gruppo in ("capi", "genitori", "ragazzi"):
        setattr(imp, f"email_{gruppo}", gruppi.get(gruppo, False))
    imp.save()


def test_email_solo_ai_gruppi_accesi(capo, ragazza, genitore, settings):
    settings.MAILERS = MAILERS_VERI
    tutti = (capo.utente.email, ragazza.utente.email, genitore.utente.email, "x@example.invalid")
    # All off at first: only who is not in the registry gets it; the rest is counted.
    assert _manda("evento_nuovo", *tutti) == ["x@example.invalid"]
    assert Impostazioni.carica().email_scartate == {"capi": 1, "ragazzi": 1, "genitori": 1}
    _accendi(capi=True)
    assert _manda("evento_nuovo", *tutti) == ["capo@example.invalid", "x@example.invalid"]
    _accendi(capi=True, genitori=True, ragazzi=True)
    assert len(_manda(None, *tutti)) == 4  # an email without a type follows the switches too


def test_alcune_email_partono_sempre(capo, genitore, settings):
    settings.MAILERS = MAILERS_VERI
    for tipo in ("codice_accesso", "invito", "iscrizione_accolta", "attesa_conferma", "account"):
        assert _manda(tipo, capo.utente.email, genitore.utente.email) == [
            "capo@example.invalid",
            "genitore@example.invalid",
        ]
    assert Impostazioni.carica().email_scartate == {}


def test_capo_che_e_anche_genitore(capo, ragazza, settings):
    from apps.anagrafica.models import RelazioneTutela, TipoTutela

    settings.MAILERS = MAILERS_VERI
    RelazioneTutela.objects.create(tutore=capo, minore=ragazza, tipo=TipoTutela.GENITORE)
    _accendi(genitori=True)
    assert _manda("promemoria_quote", capo.utente.email) == ["capo@example.invalid"]


def test_chi_sceglie_chi_riceve_le_email(
    gruppo, capo, capogruppo, ragazza, genitore, estraneo, amministratore
):
    def scegli(utente):
        return _client(utente).put(
            f"{URL}/destinatari-email",
            {"capi": True, "genitori": False, "ragazzi": False},
            content_type="application/json",
        )

    for chi in (capo, ragazza, genitore, estraneo):
        assert not policy.puo_scegliere_destinatari_email(chi.utente)
        assert scegli(chi.utente).status_code == 403
    for utente in (capogruppo.utente, amministratore):
        risposta = scegli(utente)
        assert risposta.status_code == 200 and risposta.json()["email_capi"] is True
    assert Impostazioni.carica().email_accese() == {"capi"}


# --- The SMTP server from the settings (DEC-277) ----------------------------------------------

SMTP = {
    "host": "smtp.gmail.com",
    "porta": 587,
    "sicurezza": "STARTTLS",
    "utente": "gruppo@example.invalid",
    "password": "abcd efgh ijkl mnop",
    "mittente": "AGESCI Prova 1 <gruppo@example.invalid>",
}


def _smtp(utente, dati):
    return _client(utente).put(f"{URL}/smtp", dati, content_type="application/json")


def test_solo_l_amministratore_imposta_il_server_di_posta(
    gruppo, capo, capogruppo, ragazza, genitore, estraneo, amministratore
):
    for chi in (capo, capogruppo, ragazza, genitore, estraneo):
        assert not policy.puo_configurare_smtp(chi.utente)
        assert _smtp(chi.utente, SMTP).status_code == 403
        assert _client(chi.utente).post(f"{URL}/smtp/prova").status_code in (403,)
    # The capigruppo do not even see the server.
    assert _client(capogruppo.utente).get(URL).json()["smtp_host"] == ""
    assert policy.puo_configurare_smtp(amministratore)


def test_password_cifrata_e_mai_restituita(gruppo, amministratore):
    from apps.impostazioni import segreti

    risposta = _smtp(amministratore, SMTP)
    assert risposta.status_code == 200
    dati = risposta.json()
    assert dati["smtp_password_salvata"] is True and "password" not in dati
    assert SMTP["password"] not in risposta.content.decode()
    imp = Impostazioni.carica()
    assert imp.smtp_password != SMTP["password"]
    assert segreti.decifra(imp.smtp_password) == SMTP["password"]
    # Saved again without a password: the old one stays.
    assert _smtp(amministratore, SMTP | {"password": "", "porta": 465}).status_code == 200
    assert segreti.decifra(Impostazioni.carica().smtp_password) == SMTP["password"]
    # No server: back to the server's configuration, the password goes.
    _smtp(amministratore, SMTP | {"host": "", "password": ""})
    assert Impostazioni.carica().smtp_password == ""


def test_server_di_posta_dati_non_validi(gruppo, amministratore, settings):
    assert _smtp(amministratore, SMTP | {"mittente": "non un indirizzo"}).status_code == 400
    assert _smtp(amministratore, SMTP | {"porta": 0}).status_code == 400
    assert _smtp(amministratore, SMTP | {"host": "https://smtp.gmail.com"}).status_code == 400
    settings.QDC_CHIAVE_SEGRETI = ""
    risposta = _smtp(amministratore, SMTP)
    assert risposta.status_code == 400 and "QDC_CHIAVE_SEGRETI" in risposta.json()["detail"]


def test_le_email_passano_dal_server_delle_impostazioni(gruppo, amministratore, settings):
    from unittest import mock

    from django.core.mail import EmailMessage, mailers

    settings.MAILERS = MAILERS_VERI
    _smtp(amministratore, SMTP)
    with mock.patch("apps.impostazioni.posta.SmtpBackend") as smtp:
        mailers.default.send_messages([EmailMessage("Prova", "Testo", to=["x@example.invalid"])])
    opzioni = smtp.call_args.kwargs
    assert opzioni["host"] == "smtp.gmail.com" and opzioni["password"] == SMTP["password"]
    assert opzioni["use_tls"] is True and opzioni["use_ssl"] is False
    email = smtp.return_value.send_messages.call_args.args[0][0]
    assert email.from_email == SMTP["mittente"]


def test_email_di_prova_del_server(gruppo, amministratore):
    import smtplib
    from unittest import mock

    _smtp(amministratore, SMTP)
    url = f"{URL}/smtp/prova"
    with mock.patch("apps.impostazioni.posta.SmtpBackend") as smtp:
        risposta = _client(amministratore).post(url)
    assert risposta.status_code == 200 and risposta.json()["inviata_a"] == "admin@example.invalid"
    assert smtp.return_value.send_messages.call_args.args[0][0].to == ["admin@example.invalid"]
    with mock.patch("apps.impostazioni.posta.SmtpBackend") as smtp:
        smtp.return_value.send_messages.side_effect = smtplib.SMTPAuthenticationError(535, b"no")
        risposta = _client(amministratore).post(url)
    assert risposta.status_code == 400 and "password per le app" in risposta.json()["detail"]


# --- Gmail with a Google login (DEC-278) -------------------------------------------------------


def _risposta(status=200, **json):
    from unittest import mock

    return mock.MagicMock(status_code=status, json=mock.MagicMock(return_value=json))


def _client_oauth(amministratore):
    return _smtp(
        amministratore,
        SMTP
        | {
            "host": "",
            "password": "",
            "modo": "GMAIL",
            "gmail_client_id": "123.apps.googleusercontent.com",
            "gmail_client_secret": "GOCSPX-segreto",
        },
    )


def _collega(client):
    """Start the link and come back from Google with a code; returns the redirect."""
    from unittest import mock

    import jwt as pyjwt

    url = client.post(f"{URL}/gmail/collega").json()["url"]
    stato = url.split("state=")[1].split("&")[0]
    identita = pyjwt.encode({"email": "gruppo@example.invalid"}, "x" * 32, algorithm="HS256")
    with mock.patch("apps.impostazioni.gmail.requests.post") as post:
        post.return_value = _risposta(refresh_token="1//rinnovo", id_token=identita)
        risposta = client.get(f"{URL}/gmail/ritorno", {"state": stato, "code": "4/codice"})
    return url, risposta


def test_gmail_collegato_con_accesso_google(gruppo, amministratore):
    from apps.impostazioni import segreti

    dati = _client_oauth(amministratore).json()
    assert dati["gmail_secret_salvato"] is True and "GOCSPX" not in str(dati)
    assert dati["gmail_redirect_uri"].endswith("/api/v1/impostazioni/gmail/ritorno")
    url, risposta = _collega(_client(amministratore))
    assert url.startswith("https://accounts.google.com/o/oauth2/v2/auth?")
    assert "gmail.send" in url and "access_type=offline" in url
    assert risposta.status_code == 302 and risposta.url.endswith("/impostazioni?gmail=collegato")
    imp = Impostazioni.carica()
    assert imp.modo_invio == "GMAIL" and imp.gmail_indirizzo == "gruppo@example.invalid"
    assert segreti.decifra(imp.gmail_refresh_token) == "1//rinnovo"
    assert _client(amministratore).get(URL).json()["gmail_indirizzo"] == "gruppo@example.invalid"


def test_gmail_ritorno_con_stato_sbagliato(gruppo, amministratore):
    _client_oauth(amministratore)
    client = _client(amministratore)
    client.post(f"{URL}/gmail/collega")
    risposta = client.get(f"{URL}/gmail/ritorno", {"state": "altro", "code": "4/codice"})
    assert "gmail=errore" in risposta.url
    assert Impostazioni.carica().gmail_refresh_token == ""


def test_solo_l_amministratore_collega_gmail(gruppo, capogruppo, amministratore):
    _client_oauth(amministratore)
    for percorso in ("collega", "scollega"):
        assert _client(capogruppo.utente).post(f"{URL}/gmail/{percorso}").status_code == 403
    assert _client(capogruppo.utente).get(f"{URL}/gmail/ritorno").status_code == 403


def test_le_email_partono_con_l_api_di_gmail(gruppo, amministratore, settings):
    from unittest import mock

    from django.core.mail import EmailMessage, mailers

    settings.MAILERS = MAILERS_VERI
    settings.DEFAULT_FROM_EMAIL = "Quaderno di Caccia <noreply@example.invalid>"
    _client_oauth(amministratore)
    _collega(_client(amministratore))
    Impostazioni.objects.update(mittente="")
    with mock.patch("apps.impostazioni.gmail.requests.post") as post:
        post.side_effect = [_risposta(access_token="ya29.accesso", expires_in=3600), _risposta()]
        mailers.default.send_messages([EmailMessage("Prova", "Testo", to=["x@example.invalid"])])
    invio = post.call_args_list[1]
    assert invio.args[0].startswith("https://gmail.googleapis.com/upload/gmail/v1/users/me/")
    assert invio.kwargs["headers"]["Authorization"] == "Bearer ya29.accesso"
    grezza = invio.kwargs["data"].decode()
    # With no sender written, the linked address with the configured name.
    assert "From: Quaderno di Caccia <gruppo@example.invalid>" in grezza


def test_gmail_revocato_detto_in_parole_semplici(gruppo, amministratore):
    from unittest import mock

    from apps.impostazioni import gmail

    _client_oauth(amministratore)
    _collega(_client(amministratore))
    gmail._cache.clear()
    with mock.patch("apps.impostazioni.gmail.requests.post") as post:
        post.return_value = _risposta(400, error="invalid_grant")
        risposta = _client(amministratore).post(f"{URL}/smtp/prova")
    assert risposta.status_code == 400 and "collega di nuovo" in risposta.json()["detail"]


def test_gmail_scollegato(gruppo, amministratore):
    from unittest import mock

    _client_oauth(amministratore)
    _collega(_client(amministratore))
    with mock.patch("apps.impostazioni.gmail.requests.post") as post:
        dati = _client(amministratore).post(f"{URL}/gmail/scollega").json()
    assert post.call_args.args[0] == "https://oauth2.googleapis.com/revoke"
    assert dati["modo_invio"] == "SMTP" and dati["gmail_indirizzo"] == ""
    assert Impostazioni.carica().gmail_refresh_token == ""
