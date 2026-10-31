"""Email templates the group personalises (DEC-250)."""

import pytest
from django.core import mail
from django.test import Client

from apps.accounts.adapters import EMAIL_ALLAUTH, AccountAdapter
from apps.accounts.models import User
from apps.impostazioni import email
from apps.impostazioni.catalogo_email import TIPI
from apps.impostazioni.html import in_testo, pulisci
from apps.impostazioni.models import ModelloEmail

URL = "/api/v1/impostazioni/email"


def _client(utente) -> Client:
    client = Client()
    client.force_login(utente)
    return client


def _put(utente, chiave, oggetto, corpo):
    return _client(utente).put(
        f"{URL}/{chiave}", {"oggetto": oggetto, "corpo": corpo}, content_type="application/json"
    )


@pytest.fixture
def amministratore(db) -> User:
    return User.objects.create_user(email="admin@example.invalid", amministratore_tecnico=True)


INVITO = (
    "<p>Benvenuti in [Gruppo]!</p><p>L'account per [Persona] si crea qui: [Link]</p>"
    "<p>Entro il [Scadenza].</p>"
)
VALORI_INVITO = {
    "Persona": "Giulia Rossi",
    "Link": "https://qdc.example/invito/abc",
    "Scadenza": "15/11/2026",
}


def test_i_testi_di_base_sono_tutti_validi(db):
    for t in TIPI.values():
        assert email.problemi(t, t.oggetto, t.corpo) == [], t.chiave
        assert pulisci(t.corpo) == t.corpo, t.chiave


def test_ogni_email_di_allauth_ha_il_suo_modello():
    for modello, campi in EMAIL_ALLAUTH.values():
        nomi = {s.nome for s in email.segnaposto_di(TIPI[modello])}
        assert set(campi) <= nomi


def test_html_ripulito_e_testo_ricavato():
    html = pulisci(
        '<p>Ciao <b>Giulia</b></p><script>x()</script><a href="javascript:x()">no</a>'
        '<ul><li>uno</li><li><a href="https://a.it">due</a></li></ul><img src="x">'
    )
    assert "script" not in html and "javascript" not in html and "img" not in html
    assert in_testo(html) == "Ciao Giulia\n\nno\n\n- uno\n- due (https://a.it)\n"


def test_valori_sicuri_e_link_cliccabili(db):
    composta = email.componi(
        "iscrizione_rifiutata",
        {"Nome": "Giulia", "Unità": "Reparto", "Motivo": "<b>posti</b>\nfiniti"},
    )
    assert "&lt;b&gt;posti&lt;/b&gt;<br>finiti" in composta.html
    assert "<b>posti</b>\nfiniti" in composta.testo
    invito = email.componi("invito", VALORI_INVITO)
    assert '<a href="https://qdc.example/invito/abc">' in invito.html
    assert "https://qdc.example/invito/abc" in invito.testo


def test_chi_cambia_i_modelli(
    gruppo, capo, capogruppo, ragazza, genitore, estraneo, amministratore
):
    for chi in (capo, ragazza, genitore, estraneo):
        assert _client(chi.utente).get(URL).status_code == 403
        assert _put(chi.utente, "invito", "Invito", INVITO).status_code == 403
    elenco = _client(capogruppo.utente).get(URL).json()
    assert {m["chiave"] for m in elenco} == set(TIPI)
    assert _put(amministratore, "invito", "Invito a [Nome sito]", INVITO).status_code == 200
    assert _client(capogruppo.utente).get(f"{URL}/inesistente").status_code == 404


def test_segnaposto_indispensabili_e_sconosciuti(gruppo, capogruppo):
    senza_link = "<p>Ciao [Persona], entro il [Scadenza].</p>"
    risposta = _put(capogruppo.utente, "invito", "Invito", senza_link)
    assert risposta.status_code == 400 and "[Link]" in risposta.json()["detail"]
    ignoto = INVITO + "<p>[Firma]</p>"
    assert "[Firma]" in _put(capogruppo.utente, "invito", "Invito", ignoto).json()["detail"]
    # A placeholder is text, never the address of a link.
    nel_link = INVITO.replace("[Link]", '<a href="https://x.it/[Link]">qui</a> [Link]')
    assert _put(capogruppo.utente, "invito", "Invito", nel_link).status_code == 400
    assert not ModelloEmail.objects.exists()


def test_il_modello_salvato_si_usa_e_si_ripristina(gruppo, capogruppo):
    risposta = _put(capogruppo.utente, "invito", "Invito a [Gruppo]", INVITO + "<script>x</script>")
    assert risposta.status_code == 200
    assert "script" not in ModelloEmail.objects.get().corpo
    email.invia("invito", VALORI_INVITO, ["giulia@example.invalid"])
    [inviata] = mail.outbox
    assert inviata.subject == "Invito a AGESCI Prova 1"
    assert "Benvenuti in AGESCI Prova 1!" in inviata.body
    assert inviata.alternatives[0].mimetype == "text/html"
    # Back to the default.
    tornato = _client(capogruppo.utente).delete(f"{URL}/invito").json()
    assert tornato["personalizzato"] is False and not ModelloEmail.objects.exists()
    email.invia("invito", VALORI_INVITO, ["giulia@example.invalid"])
    assert mail.outbox[1].subject == "Invito al Quaderno di Caccia"


def test_un_modello_da_correggere_usa_la_base_e_avvisa_una_volta(gruppo, capogruppo):
    # Saved before [Link] became indispensable (as after an update of the app).
    ModelloEmail.objects.create(chiave="invito", oggetto="Invito", corpo="<p>Ciao</p>")
    email.invia("invito", VALORI_INVITO, ["giulia@example.invalid"])
    email.invia("invito", VALORI_INVITO, ["giulia@example.invalid"])
    avvisi = [m for m in mail.outbox if m.subject == "Un modello di email da correggere"]
    inviti = [m for m in mail.outbox if m.to == ["giulia@example.invalid"]]
    assert [m.to for m in avvisi] == [[capogruppo.utente.email]]
    assert all("https://qdc.example/invito/abc" in m.body for m in inviti) and len(inviti) == 2
    elenco = _client(capogruppo.utente).get(URL).json()
    assert next(m for m in elenco if m["chiave"] == "invito")["da_correggere"] is True


def test_le_email_facoltative_dicono_come_smettere(db):
    [facoltativa] = [
        email.messaggio("promemoria_quote", {"Elenco": "- x", "Link": "https://q"}, "a@x.it")
    ]
    assert "Per scegliere quali email ricevere" in facoltativa.body
    obbligatoria = email.messaggio("invito", VALORI_INVITO, "a@x.it")
    assert "Per scegliere quali email ricevere" not in obbligatoria.body


def test_anteprima_con_dati_di_esempio(gruppo, capogruppo):
    risposta = _client(capogruppo.utente).post(
        f"{URL}/invito/anteprima",
        {"oggetto": "Per [Persona]", "corpo": INVITO},
        content_type="application/json",
    )
    dati = risposta.json()
    assert dati["oggetto"] == "Per Giulia Rossi" and "Giulia Rossi" in dati["testo"]
    assert not ModelloEmail.objects.exists()


def test_le_email_di_allauth_dal_modello(gruppo, capogruppo):
    corpo = "<p>Il codice: [Codice]</p>"
    assert _put(capogruppo.utente, "codice_accesso", "Entra", corpo).status_code == 200
    AccountAdapter().send_mail("account/email/login_code", "a@x.it", {"code": "ABCD-EFGH"})
    [inviata] = mail.outbox
    assert inviata.subject == "Entra" and "Il codice: ABCD-EFGH" in inviata.body
