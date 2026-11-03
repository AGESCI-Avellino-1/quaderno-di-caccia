"""A ragazzo's personal link to create their account (DEC-309)."""

from datetime import timedelta

import pytest
from django.core import mail
from django.test import Client, RequestFactory

from apps.accounts.adapters import CHIAVE_SESSIONE_INVITO, collega_invito
from apps.accounts.models import Invito, LinkAttivazione, User
from apps.anagrafica.models import Appartenenza, RelazioneTutela, RuoloAppartenenza
from apps.permessi import policy
from tests.conftest import INIZIO_ANNO, crea_persona, nato_anni_fa

pytestmark = pytest.mark.django_db


def _client(chi) -> Client:
    client = Client()
    client.force_login(chi.utente)
    return client


@pytest.fixture
def senza_account(reparto, squadriglia):
    """A 15-year-old in the patrol of `csq`, with two parents, no account."""
    from apps.anagrafica.models import AppartenenzaSquadriglia

    persona = crea_persona("Leo", "Lupo", codice_socio="1234567", data_nascita=nato_anni_fa(15))
    Appartenenza.objects.create(
        persona=persona, unita=reparto, ruolo=RuoloAppartenenza.RAGAZZO, data_inizio=INIZIO_ANNO
    )
    AppartenenzaSquadriglia.objects.create(
        persona=persona, squadriglia=squadriglia, data_inizio=INIZIO_ANNO
    )
    for nome, email in (("Pia", "pia@example.invalid"), ("Ugo", "ugo@example.invalid")):
        genitore = crea_persona(nome, "Lupo", email=email)
        RelazioneTutela.objects.create(tutore=genitore, minore=persona, tipo="GENITORE")
    return persona


def _genera(chi, persona):
    return _client(chi).post(f"/api/v1/persone/{persona.pk}/link-attivazione")


def _parti(link: str) -> tuple[str, str]:
    codice, segreto = link.rstrip("/").split("/")[-2:]
    return codice, segreto


def _usa(link, data_nascita, email="leo@example.invalid"):
    codice, segreto = _parti(link)
    return Client().post(
        "/api/v1/attivazione",
        {
            "codice_socio": codice,
            "segreto": segreto,
            "data_nascita": str(data_nascita),
            "email": email,
        },
        content_type="application/json",
    )


def test_chi_genera_il_link(capo, capogruppo, csq, ragazza, genitore, estraneo, senza_account):
    for chi in (capo, capogruppo, csq):
        assert _genera(chi, senza_account).status_code == 200
    for chi in (ragazza, genitore, estraneo):
        assert _genera(chi, senza_account).status_code == 404
    # Not under 14, not to who has an account.
    piccolo = crea_persona("Tito", "Piccolo", codice_socio="7654321", data_nascita=nato_anni_fa(12))
    assert not policy.puo_generare_link_attivazione(capogruppo.utente, piccolo)
    assert not policy.puo_generare_link_attivazione(capogruppo.utente, ragazza)


def test_il_capo_squadriglia_lo_vede_tra_i_suoi(csq, ragazza, senza_account):
    (sq,) = _client(csq).get("/api/v1/mia-squadriglia").json()
    assert {m["nome"]: m["link_attivazione"] for m in sq["membri"]} == {
        "Giulia": False, "Leo": True, "Sara": False,
    }  # fmt: skip
    (sq,) = _client(ragazza).get("/api/v1/mia-squadriglia").json()
    assert not any(m["link_attivazione"] for m in sq["membri"])


def test_un_link_nuovo_annulla_il_vecchio(capo, senza_account):
    vecchio = _genera(capo, senza_account).json()["link"]
    nuovo = _genera(capo, senza_account).json()["link"]
    assert vecchio != nuovo
    assert Client().get(f"/api/v1/attivazione/{'/'.join(_parti(vecchio))}").status_code == 400
    aperto = Client().get(f"/api/v1/attivazione/{'/'.join(_parti(nuovo))}").json()
    assert aperto == {"nome": "Leo"}
    # Only the fingerprint of the secret is kept.
    assert _parti(nuovo)[1] not in LinkAttivazione.objects.values_list("impronta", flat=True)
    stato = _client(capo).get(f"/api/v1/persone/{senza_account.pk}/link-attivazione").json()
    assert stato["attivo_fino_al"]


def test_data_sbagliata_poi_il_link_non_vale_piu(capo, senza_account):
    link = _genera(capo, senza_account).json()["link"]
    sbagliata = senza_account.data_nascita - timedelta(days=1)
    for _ in range(4):
        risposta = _usa(link, sbagliata)
        assert risposta.status_code == 400 and "non corrisponde" in risposta.json()["detail"]
    assert "non vale più" in _usa(link, sbagliata).json()["detail"]
    assert _usa(link, senza_account.data_nascita).status_code == 400
    assert mail.outbox == []


def test_email_gia_usata(capo, senza_account, genitore):
    link = _genera(capo, senza_account).json()["link"]
    assert (
        "già un account"
        in _usa(link, senza_account.data_nascita, genitore.utente.email).json()["detail"]
    )
    assert (
        "un'altra persona"
        in _usa(link, senza_account.data_nascita, "pia@example.invalid").json()["detail"]
    )


def test_dal_link_all_account_e_genitori_avvisati(capo, senza_account):
    link = _genera(capo, senza_account).json()["link"]
    # A mistyped address first: the second replaces it.
    assert _usa(link, senza_account.data_nascita, "sbagliato@example.invalid").status_code == 200
    assert _usa(link, senza_account.data_nascita).json() == {"email": "leo@example.invalid"}
    assert [m.to for m in mail.outbox] == [["sbagliato@example.invalid"], ["leo@example.invalid"]]
    assert "crea il tuo account" in mail.outbox[1].subject
    invito = Invito.objects.get(email="leo@example.invalid")
    assert not Invito.objects.get(email="sbagliato@example.invalid").valido
    mail.outbox.clear()

    # The account is created through the invitation, as always.
    utente = User.objects.create_user(email="leo@example.invalid", password="x")  # noqa: S106
    richiesta = RequestFactory().post("/")
    richiesta.session = {CHIAVE_SESSIONE_INVITO: invito.token}
    collega_invito(richiesta, utente)
    senza_account.refresh_from_db()
    assert senza_account.utente == utente
    assert LinkAttivazione.objects.get().usato_il is not None
    assert sorted(m.to[0] for m in mail.outbox) == ["pia@example.invalid", "ugo@example.invalid"]
    assert "Leo Lupo" in mail.outbox[0].subject
