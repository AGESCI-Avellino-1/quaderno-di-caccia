import pytest
from django.core import mail
from django.core.management import CommandError, call_command
from django.test import Client

from apps.accounts.models import Invito
from apps.organizzazione.models import Incarico, RuoloIncarico
from apps.permessi import policy

pytestmark = pytest.mark.django_db


def _client(persona) -> Client:
    client = Client()
    client.force_login(persona.utente)
    return client


def _invita(chi, persona, email, **altro):
    return _client(chi).post(
        "/api/v1/inviti",
        {"persona_id": persona.pk, "email": email, **altro},
        content_type="application/json",
    )


def test_invito_dall_app_parte_per_email(capo, genitrice_senza_account):
    risposta = _invita(capo, genitrice_senza_account, "mamma@example.invalid")
    assert risposta.status_code == 201
    [messaggio] = mail.outbox
    assert messaggio.to == ["mamma@example.invalid"]
    assert f"/invito/{risposta.json()['token']}" in messaggio.body
    assert genitrice_senza_account.nome in messaggio.body


def test_niente_invito_a_chi_ha_gia_un_account(capo, genitore, genitrice_senza_account):
    risposta = _invita(capo, genitore, "altra@example.invalid")
    assert risposta.status_code == 400
    assert "ha già un account" in risposta.json()["detail"]
    # The email of an existing account cannot open a second one.
    risposta = _invita(capo, genitrice_senza_account, "GENITORE@example.invalid")
    assert risposta.status_code == 400
    assert "Esiste già un account" in risposta.json()["detail"]
    assert mail.outbox == []


def test_stato_account_per_chi_puo_invitare(
    capo, capogruppo, ragazza, genitore, genitrice_senza_account
):
    for chi in (capo, capogruppo):
        dati = _client(chi).get(f"/api/v1/persone/{ragazza.pk}/account").json()
        assert dati["persona"]["ha_account"] is True
        assert dati["persona"]["richiede_consenso_genitore"] is True  # 12 years old
        genitori = {g["nome"]: g for g in dati["genitori"]}
        assert genitori["Mario"]["ha_account"] is True
        assert genitori["Lucia"]["ha_account"] is False
        assert genitori["Lucia"]["puo_invitare"] is True
        assert genitori["Lucia"]["email"] == "lucia@example.invalid"
        assert {m["valore"] for m in dati["metodi_consenso"]} >= {"IN_PRESENZA"}


def test_niente_email_di_un_altra_persona(capo, ragazza, genitrice_senza_account):
    """Every account has its own email: a child is not invited with a parent's address,
    which the parent needs for their own account (refines DEC-25)."""
    ragazza.utente = None  # not yet invited
    ragazza.save()
    risposta = _invita(capo, ragazza, "LUCIA@example.invalid")
    assert risposta.status_code == 400
    assert "di un'altra persona" in risposta.json()["detail"]
    assert mail.outbox == []


@pytest.mark.parametrize("ruolo", ["csq", "ragazza", "genitore", "estraneo", "capo_semplice"])
def test_stato_account_nascosto_agli_altri(request, ruolo, ragazza, reparto, coca):
    if ruolo == "capo_semplice":
        # A capo of the Co.Ca. without the capo unità role: reads everything (DEC-09)
        # but does not invite (DEC-21).
        from apps.anagrafica.models import Appartenenza, RuoloAppartenenza

        from .conftest import INIZIO_ANNO, crea_persona

        chi = crea_persona("Carlo", "Semplice", "semplice@example.invalid")
        Appartenenza.objects.create(
            persona=chi, unita=coca, ruolo=RuoloAppartenenza.CAPO, data_inizio=INIZIO_ANNO
        )
    else:
        chi = request.getfixturevalue(ruolo)
    assert _client(chi).get(f"/api/v1/persone/{ragazza.pk}/account").status_code == 404


def test_annulla_invito(capo, capogruppo, estraneo, genitrice_senza_account):
    invito_id = _invita(capo, genitrice_senza_account, "sbagliata@example.invalid").json()["id"]
    # Who cannot invite this person cannot withdraw the invitation either.
    assert _client(estraneo).post(f"/api/v1/inviti/{invito_id}/annulla").status_code == 404
    risposta = _client(capogruppo).post(f"/api/v1/inviti/{invito_id}/annulla")
    assert risposta.status_code == 200
    assert risposta.json()["valido"] is False
    assert not Invito.objects.get(pk=invito_id).valido


def test_invito_usato_non_si_annulla(capo, genitrice_senza_account):
    from django.utils import timezone

    invito_id = _invita(capo, genitrice_senza_account, "usata@example.invalid").json()["id"]
    Invito.objects.filter(pk=invito_id).update(usato_il=timezone.now())
    assert _client(capo).post(f"/api/v1/inviti/{invito_id}/annulla").status_code == 409


def test_bootstrap_primo_capogruppo(capo):
    """Fresh install: a capo from the import becomes capogruppo and gets an invite."""
    capo.codice_socio = "1234567"
    capo.save()
    utente = capo.utente
    assert not policy.e_capogruppo(utente)

    call_command("crea_invito", "1234567", "cg@example.invalid", "--capogruppo")

    assert Incarico.objects.attivi().filter(persona=capo, ruolo=RuoloIncarico.CAPOGRUPPO).exists()
    assert policy.e_capogruppo(utente)
    assert Invito.objects.get(email="cg@example.invalid").persona == capo
    assert len(mail.outbox) == 1


def test_bootstrap_codice_sconosciuto(db):
    with pytest.raises(CommandError, match="importa prima"):
        call_command("crea_invito", "0000000", "x@example.invalid")


def test_consenso_dall_account_del_genitore_solo_se_ce_l_ha(capo, ragazza, genitrice_senza_account):
    from django.test import Client

    ragazza.utente = None
    ragazza.save()
    client = Client()
    client.force_login(capo.utente)
    risposta = client.post(
        "/api/v1/inviti",
        {
            "persona_id": ragazza.pk,
            "email": "nuova@example.invalid",
            "consenso_genitore_da_id": genitrice_senza_account.pk,
            "consenso_genitore_metodo": "ACCOUNT_GENITORE",
        },
        content_type="application/json",
    )
    assert risposta.status_code == 400
    assert "non ha un account" in risposta.json()["detail"]
