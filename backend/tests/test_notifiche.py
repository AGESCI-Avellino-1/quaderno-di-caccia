"""Push notifications (DEC-345). `webpush` is never called for real here."""

import base64
from datetime import date, timedelta
from decimal import Decimal

import pytest
import requests
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from django.core.management import call_command
from django.test import Client
from pywebpush import WebPushException

from apps.bacheca.models import Avviso, Destinatari
from apps.bacheca.servizi import invia as invia_avviso
from apps.impersonazione.middleware import bloccata
from apps.impostazioni.models import Impostazioni
from apps.notifiche import servizi
from apps.notifiche.models import ChiaviPush, IscrizionePush, PreferenzePush, PushInCoda

pytestmark = pytest.mark.django_db

ENDPOINT = "https://fcm.googleapis.com/fcm/send/abc"
CORPO = {"endpoint": ENDPOINT, "p256dh": "chiave", "auth": "segreto"}


def _client(chi) -> Client:
    client = Client()
    client.force_login(chi.utente)
    return client


def _post(client, url, dati):
    return client.post(url, dati, content_type="application/json")


@pytest.fixture(autouse=True)
def email_accese():
    imp = Impostazioni.carica()
    imp.email_capi = imp.email_genitori = imp.email_ragazzi = True
    imp.save()


@pytest.fixture
def spediti(monkeypatch):
    chiamate = []
    monkeypatch.setattr(servizi, "webpush", lambda **k: chiamate.append(k))
    return chiamate


def _iscrivi(chi, corpo=None) -> Client:
    client = _client(chi)
    risposta = _post(client, "/api/v1/push/iscrizioni", corpo or CORPO)
    assert risposta.status_code == 204, risposta.content
    return client


def test_chiavi_create_una_volta_e_cifrate():
    prima = servizi.chiavi()
    assert servizi.chiavi().pk == prima.pk and ChiaviPush.objects.count() == 1
    assert len(prima.pubblica) == 87  # 65 bytes, as the browsers want them
    assert "BEGIN" not in prima.privata_cifrata


def test_senza_chiave_dei_segreti_nessuna_notifica(settings, genitore, spediti):
    settings.QDC_CHIAVE_SEGRETI = ""
    risposta = _client(genitore).get("/api/v1/push").json()
    assert risposta["disponibili"] is False and risposta["chiave_pubblica"] == ""
    assert _post(_client(genitore), "/api/v1/push/iscrizioni", CORPO).status_code == 400
    assert servizi.notifica("avvisi", [genitore], "Titolo", "/") == 0


def test_solo_i_servizi_dei_browser(genitore):
    for cattivo in (
        "http://fcm.googleapis.com/x",
        "https://localhost/x",
        "https://169.254.169.254/latest",
        "https://fcm.googleapis.com.esempio.it/x",
        "https://evilpush.apple.com/x",
    ):
        corpo = {**CORPO, "endpoint": cattivo}
        assert _post(_client(genitore), "/api/v1/push/iscrizioni", corpo).status_code == 400
    for buono in (
        ENDPOINT,
        "https://web.push.apple.com/x",
        "https://updates.push.services.mozilla.com/x",
        "https://wns2-par02p.notify.windows.com/x",
    ):
        assert servizi.endpoint_ammesso(buono)


def test_serve_l_accesso():
    assert Client().get("/api/v1/push").status_code == 401
    assert _post(Client(), "/api/v1/push/iscrizioni", CORPO).status_code == 401


def test_invio_e_contenuto(genitore, spediti):
    _iscrivi(genitore)
    assert servizi.notifica("avvisi", [genitore], "Nuovo avviso: Campo", "/bacheca") == 1
    chiamata = spediti[0]
    assert chiamata["subscription_info"]["endpoint"] == ENDPOINT
    assert '"percorso": "/bacheca"' in chiamata["data"]
    assert chiamata["vapid_claims"]["sub"].startswith("mailto:")


def test_cifratura_e_firma_con_la_libreria_vera(genitore, monkeypatch):
    """Only the network is replaced: the message is really encrypted and signed."""
    privata = ec.generate_private_key(ec.SECP256R1())
    p256dh = privata.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )
    corpo = {
        "endpoint": ENDPOINT,
        "p256dh": base64.urlsafe_b64encode(p256dh).rstrip(b"=").decode(),
        "auth": base64.urlsafe_b64encode(b"0123456789abcdef").rstrip(b"=").decode(),
    }
    _iscrivi(genitore, corpo)
    richieste = []

    class Risposta:
        status_code = 201
        text = ""
        headers: dict = {}

    def posta(url, **opzioni):
        richieste.append((url, opzioni))
        return Risposta()

    monkeypatch.setattr("pywebpush.requests.post", posta)
    assert servizi.notifica("avvisi", [genitore], "Nuovo avviso: Campo", "/bacheca") == 1
    url, opzioni = richieste[0]
    assert url == ENDPOINT
    # Encrypted: the service in the middle cannot read the text.
    assert b"Campo" not in opzioni["data"]
    assert opzioni["headers"]["content-encoding"] == "aes128gcm"
    assert opzioni["headers"]["Authorization"].startswith("vapid t=")
    assert servizi.chiavi().pubblica in opzioni["headers"]["Authorization"]


def test_chi_non_vuole_non_la_riceve(genitore, spediti):
    _iscrivi(genitore)
    PreferenzePush.objects.create(persona=genitore, avvisi=False)
    assert servizi.notifica("avvisi", [genitore], "Titolo", "/") == 0
    assert servizi.notifica("eventi", [genitore], "Titolo", "/") == 1


def test_preferenze_per_persona(genitore):
    client = _client(genitore)
    corpo = {"eventi": False, "promemoria_quote": True, "riepiloghi": True, "avvisi": False}
    risposta = client.put("/api/v1/push/preferenze", corpo, content_type="application/json")
    assert risposta.status_code == 200
    assert client.get("/api/v1/push").json()["preferenze"] == corpo


def test_finisce_con_la_sessione(genitore, spediti):
    client = _iscrivi(genitore)
    client.logout()
    assert servizi.notifica("avvisi", [genitore], "Titolo", "/") == 0
    assert not IscrizionePush.objects.exists()


def test_stesso_browser_altro_account(genitore, capo, spediti):
    _iscrivi(genitore)
    _iscrivi(capo)
    assert IscrizionePush.objects.get().utente == capo.utente
    assert servizi.notifica("avvisi", [genitore], "Titolo", "/") == 0
    assert servizi.notifica("avvisi", [capo], "Titolo", "/") == 1


def test_il_browser_si_disiscrive(genitore, capo):
    client = _iscrivi(genitore)
    assert client.get("/api/v1/push", {"endpoint": ENDPOINT}).json()["questo_browser"] is True
    assert client.get("/api/v1/push").json()["questo_browser"] is False
    altro = _client(capo).get("/api/v1/push", {"endpoint": ENDPOINT}).json()
    assert altro["questo_browser"] is False
    # Someone else's stays.
    risposta = _post(_client(capo), "/api/v1/push/iscrizioni/togli", {"endpoint": ENDPOINT})
    assert risposta.status_code == 204 and IscrizionePush.objects.exists()
    assert _post(client, "/api/v1/push/iscrizioni/togli", {"endpoint": ENDPOINT}).status_code == 204
    assert not IscrizionePush.objects.exists()


@pytest.mark.parametrize("stato,resta", [(410, False), (404, False), (500, True)])
def test_risposte_del_servizio(genitore, monkeypatch, stato, resta):
    _iscrivi(genitore)

    class Risposta:
        status_code = stato
        text = ""

    def rifiuta(**_):
        raise WebPushException("no", response=Risposta())

    monkeypatch.setattr(servizi, "webpush", rifiuta)
    assert servizi.notifica("avvisi", [genitore], "Titolo", "/") == 0
    assert IscrizionePush.objects.exists() is resta


def test_servizio_irraggiungibile_non_ferma_nulla(genitore, monkeypatch):
    _iscrivi(genitore)

    def giu(**_):
        raise requests.ConnectionError

    monkeypatch.setattr(servizi, "webpush", giu)
    assert servizi.notifica("avvisi", [genitore], "Titolo", "/") == 0
    assert IscrizionePush.objects.exists()


def test_in_coda_col_servizio_posta(settings, genitore, spediti):
    settings.QDC_EMAIL_IN_CODA = True
    _iscrivi(genitore)
    assert servizi.notifica("avvisi", [genitore], "Titolo", "/") == 1
    assert spediti == [] and PushInCoda.objects.count() == 1
    call_command("invia_email_in_coda")
    assert len(spediti) == 1 and not PushInCoda.objects.exists()


def test_bloccato_impersonando():
    assert bloccata("POST", "/api/v1/push/iscrizioni")
    assert bloccata("PUT", "/api/v1/push/preferenze")
    assert not bloccata("GET", "/api/v1/push")


# --- From the places that warn ----------------------------------------------------------------


def test_bacheca_quando_chi_pubblica_lo_chiede(genitore, reparto, spediti):
    _iscrivi(genitore)
    avviso = Avviso.objects.create(
        titolo="Campo",
        testo="Dettagli",
        unita=reparto,
        destinatari=Destinatari.GENITORI,
        scade_il=date.today() + timedelta(days=5),
    )
    invia_avviso(avviso)
    assert "Nuovo avviso: Campo" in spediti[0]["data"]
    assert "Dettagli" not in spediti[0]["data"]


def test_email_rifiutata_ma_push_voluta(genitore, reparto, spediti):
    from apps.anagrafica.models import PreferenzeEmail

    _iscrivi(genitore)
    PreferenzeEmail.objects.create(persona=genitore, avvisi=False)
    avviso = Avviso.objects.create(
        titolo="Campo",
        testo="Dettagli",
        unita=reparto,
        destinatari=Destinatari.GENITORI,
        scade_il=date.today() + timedelta(days=5),
    )
    invia_avviso(avviso)
    assert len(spediti) == 1


def test_quota_in_scadenza_senza_nomi_ne_importi(genitore, ragazza, gruppo, spediti):
    from apps.quote.models import CategoriaQuota, Quota, TipoQuota
    from apps.quote.models import Destinatari as DestinatariQuota

    _iscrivi(genitore)
    tipo = TipoQuota.objects.create(
        nome="Censimento",
        anno=date.today().year + 1,
        categoria=CategoriaQuota.CENSIMENTO,
        importo=Decimal("50"),
        destinatari=DestinatariQuota.TUTTI,
    )
    Quota.objects.create(
        tipo=tipo,
        persona=ragazza,
        periodo=date.today(),
        importo=Decimal("50"),
        scadenza=date.today() + timedelta(days=3),
    )
    call_command("promemoria_quote")
    assert len(spediti) == 1
    assert "Hai una quota in scadenza" in spediti[0]["data"]
    assert ragazza.nome not in spediti[0]["data"] and "50" not in spediti[0]["data"]
