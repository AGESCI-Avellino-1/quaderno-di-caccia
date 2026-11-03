"""Every account, for the technical administrator (DEC-313)."""

import pytest
from allauth.account.models import EmailAddress
from allauth.mfa.models import Authenticator
from auditlog.models import LogEntry
from django.core import mail
from django.test import Client

from apps.accounts.models import AzioneAccount, User
from apps.anagrafica.models import Persona
from apps.dispositivi.models import Dispositivo
from tests.conftest import crea_capo

pytestmark = pytest.mark.django_db

URL = "/api/v1/amministrazione/account"


@pytest.fixture
def tecnico(coca):
    persona = crea_capo("Tea", "Tecnica", "tecnica@example.invalid")
    persona.utente.amministratore_tecnico = True
    persona.utente.save()
    return persona


def _client(chi) -> Client:
    client = Client()
    client.force_login(chi.utente)
    return client


def _azione(client, account, tipo, motivo="Chiesto dalla persona", **altro):
    return client.post(
        f"{URL}/{account.pk}",
        {"tipo": tipo, "motivo": motivo, **altro},
        content_type="application/json",
    )


def test_solo_l_amministratore_tecnico(tecnico, capo, capogruppo, csq, ragazza, genitore, estraneo):
    for chi in (capo, capogruppo, csq, ragazza, genitore, estraneo):
        assert _client(chi).get(URL).status_code == 403
        assert _azione(_client(chi), genitore.utente, "SBLOCCA").status_code == 403
    elenco = _client(tecnico).get(URL).json()
    giulia = next(a for a in elenco if a["email"] == "giulia@example.invalid")
    assert giulia["persona"] == {"id": ragazza.pk, "nome": "Giulia", "cognome": "Esploratrice"}
    assert giulia["attivo"] and giulia["passkey"] == 0 and not giulia["secondo_fattore"]
    # No data of the personal file.
    assert set(giulia) == {
        "id", "email", "attivo", "persona", "creato_il", "ultimo_accesso", "password",
        "passkey", "secondo_fattore", "accessi_esterni", "dispositivi", "bloccato",
        "amministratore_tecnico",
    }  # fmt: skip
    assert [a["email"] for a in _client(tecnico).get(f"{URL}?cerca=giulia").json()] == [
        "giulia@example.invalid"
    ]


def test_serve_il_motivo_e_resta_nel_registro(tecnico, genitore):
    client = _client(tecnico)
    assert _azione(client, genitore.utente, "DISATTIVA", motivo=" ").status_code == 400
    assert (
        _azione(client, genitore.utente, "DISATTIVA", motivo="Telefono rubato").status_code == 200
    )
    azione = AzioneAccount.objects.get()
    assert (azione.tipo, azione.motivo, azione.fatta_da) == (
        "DISATTIVA",
        "Telefono rubato",
        tecnico.utente,
    )
    assert LogEntry.objects.get_for_object(azione).exists()
    storico = client.get("/api/v1/amministrazione/account-azioni").json()
    assert storico[0]["tipo_nome"] == "Account disattivato"


def test_disattiva_revoca_e_riattiva(tecnico, genitore):
    Dispositivo.objects.create(utente=genitore.utente, nome="Telefono")
    client = _client(tecnico)
    _azione(client, genitore.utente, "DISATTIVA")
    genitore.utente.refresh_from_db()
    assert not genitore.utente.is_active
    assert not Dispositivo.objects.attivi().filter(utente=genitore.utente).exists()
    assert _client(genitore).get("/api/v1/io").status_code == 401
    _azione(client, genitore.utente, "RIATTIVA")
    genitore.utente.refresh_from_db()
    assert genitore.utente.is_active
    assert mail.outbox == []  # neither one is a change to the ways in


def test_cambia_email_e_avvisa_i_due_indirizzi(tecnico, genitore, capo):
    client = _client(tecnico)
    gia_usato = _azione(client, genitore.utente, "CAMBIA_EMAIL", email=capo.utente.email)
    assert gia_usato.status_code == 400
    assert (
        _azione(client, genitore.utente, "CAMBIA_EMAIL", email="nuovo@example.invalid").status_code
        == 200
    )
    genitore.utente.refresh_from_db()
    assert genitore.utente.email == "nuovo@example.invalid"
    indirizzo = EmailAddress.objects.get(user=genitore.utente)
    assert indirizzo.email == "nuovo@example.invalid" and indirizzo.primary and indirizzo.verified
    assert sorted(m.to[0] for m in mail.outbox) == [
        "genitore@example.invalid",
        "nuovo@example.invalid",
    ]
    assert "nuovo@example.invalid" in mail.outbox[0].body


def test_togli_passkey_e_secondo_fattore(tecnico, genitore):
    for tipo in Authenticator.Type.values:
        Authenticator.objects.create(user=genitore.utente, type=tipo, data={})
    client = _client(tecnico)
    _azione(client, genitore.utente, "TOGLI_PASSKEY")
    assert set(Authenticator.objects.filter(user=genitore.utente).values_list("type", flat=True)) == {
        "totp", "recovery_codes"
    }  # fmt: skip
    _azione(client, genitore.utente, "TOGLI_SECONDO_FATTORE")
    assert not Authenticator.objects.filter(user=genitore.utente).exists()
    assert len(mail.outbox) == 2 and all(m.to == ["genitore@example.invalid"] for m in mail.outbox)


def test_cancella_toglie_solo_l_accesso(tecnico, genitore, ragazza):
    client = _client(tecnico)
    assert _azione(client, genitore.utente, "CANCELLA").status_code == 200
    assert not User.objects.filter(email="genitore@example.invalid").exists()
    persona = Persona.objects.get(pk=genitore.pk)
    assert persona.utente_id is None and persona.tutele.filter(minore=ragazza).exists()
    assert mail.outbox[0].to == ["genitore@example.invalid"]
    assert AzioneAccount.objects.get().account_id > 0


def test_non_su_se_stesso(tecnico):
    client = _client(tecnico)
    for tipo in ("DISATTIVA", "CANCELLA"):
        assert _azione(client, tecnico.utente, tipo).status_code == 400
    assert _azione(client, tecnico.utente, "SBLOCCA").status_code == 200


def test_bloccato_mentre_si_usa_l_app_al_posto_di_un_altro(tecnico, capogruppo, genitore):
    client = _client(capogruppo)
    client.post(
        "/api/v1/impersonazione",
        {"persona_id": tecnico.pk, "motivo": "Prova di quello che vede"},
        content_type="application/json",
    )
    for risposta in (client.get(URL), _azione(client, genitore.utente, "SBLOCCA")):
        assert risposta.status_code == 403
        assert risposta.json()["codice"] == "impersonazione"
