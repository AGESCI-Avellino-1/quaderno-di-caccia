"""Several invitations at once (DEC-308): parents and adults with an email of their own,
no account, no invitation still valid; the others are skipped with the reason."""

import pytest
from django.core import mail
from django.test import Client

from apps.accounts.models import Invito
from apps.anagrafica.models import Appartenenza, RuoloAppartenenza
from tests.conftest import INIZIO_ANNO, crea_capo, crea_persona, nato_anni_fa

pytestmark = pytest.mark.django_db


def _client(chi) -> Client:
    client = Client()
    client.force_login(chi.utente)
    return client


@pytest.fixture
def capo_senza_account(coca):
    persona = crea_capo("Nina", "Nuova")
    persona.email = "nina@example.invalid"
    persona.save()
    return persona


@pytest.fixture
def rover(gruppo):
    from apps.organizzazione.models import TipoUnita, Unita

    clan = Unita.objects.create(gruppo=gruppo, tipo=TipoUnita.CLAN_FUOCO, nome="Clan")
    persona = crea_persona(
        "Rino", "Rover", email="rino@example.invalid", data_nascita=nato_anni_fa(19)
    )
    Appartenenza.objects.create(
        persona=persona, unita=clan, ruolo=RuoloAppartenenza.RAGAZZO, data_inizio=INIZIO_ANNO
    )
    return persona


@pytest.fixture
def esploratore(reparto):
    persona = crea_persona(
        "Ezio", "Esploratore", email="ezio@example.invalid", data_nascita=nato_anni_fa(15)
    )
    Appartenenza.objects.create(
        persona=persona, unita=reparto, ruolo=RuoloAppartenenza.RAGAZZO, data_inizio=INIZIO_ANNO
    )
    return persona


def test_candidati_solo_chi_si_puo_invitare(
    capogruppo, genitrice_senza_account, capo_senza_account, rover, esploratore, genitore
):
    soci = _client(capogruppo).get("/api/v1/inviti/candidati?tipo=soci").json()
    assert {p["email"] for p in soci} == set()  # members here have no codice socio
    tutti = _client(capogruppo).get("/api/v1/inviti/candidati").json()
    assert {p["email"] for p in tutti} == {
        "lucia@example.invalid",  # a parent without an account
        "nina@example.invalid",  # a capo
        "rino@example.invalid",  # an adult rover
    }
    genitori = _client(capogruppo).get("/api/v1/inviti/candidati?tipo=genitori").json()
    assert [p["email"] for p in genitori] == ["lucia@example.invalid"]


def test_invia_e_salta_con_il_motivo(
    capogruppo, genitrice_senza_account, capo_senza_account, esploratore, genitore
):
    risposta = (
        _client(capogruppo)
        .post(
            "/api/v1/inviti/molti",
            {
                "persone": [
                    genitrice_senza_account.pk,
                    capo_senza_account.pk,
                    esploratore.pk,
                    genitore.pk,
                ]
            },
            content_type="application/json",
        )
        .json()
    )
    assert risposta["invitati"] == 2
    assert {(s["nome"], s["motivo"]) for s in risposta["saltati"]} == {
        ("Ezio", "è minorenne: mandale il link personale"),
        ("Mario", "ha già un account"),
    }
    assert sorted(m.to[0] for m in mail.outbox) == ["lucia@example.invalid", "nina@example.invalid"]
    # Once invited, not again while the invitation is valid.
    di_nuovo = (
        _client(capogruppo)
        .post(
            "/api/v1/inviti/molti",
            {"persone": [capo_senza_account.pk]},
            content_type="application/json",
        )
        .json()
    )
    assert di_nuovo["saltati"][0]["motivo"] == "ha già un invito valido"
    assert Invito.objects.count() == 2


def test_chi_non_puo_invitare(capo, csq, ragazza, genitore, estraneo, genitrice_senza_account):
    for chi in (csq, ragazza, genitore, estraneo):
        risposta = (
            _client(chi)
            .post(
                "/api/v1/inviti/molti",
                {"persone": [genitrice_senza_account.pk]},
                content_type="application/json",
            )
            .json()
        )
        assert risposta == {
            "invitati": 0,
            "saltati": [
                {"id": genitrice_senza_account.pk, "nome": "Lucia", "cognome": "Genitore",
                 "motivo": "non puoi invitarla"}
            ],
        }  # fmt: skip
        assert _client(chi).get("/api/v1/inviti/candidati").json() == []
    # The capo unità of the child's reparto may.
    assert [p["id"] for p in _client(capo).get("/api/v1/inviti/candidati").json()] == [
        genitrice_senza_account.pk
    ]


def test_email_di_un_altra_persona(capogruppo, capo_senza_account):
    gemello = crea_persona("Nino", "Nuovo", email="nina@example.invalid")
    assert gemello
    risposta = (
        _client(capogruppo)
        .post(
            "/api/v1/inviti/molti",
            {"persone": [capo_senza_account.pk]},
            content_type="application/json",
        )
        .json()
    )
    assert risposta["saltati"][0]["motivo"] == "la sua email è anche di un'altra persona"
