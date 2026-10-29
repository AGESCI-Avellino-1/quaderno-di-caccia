"""What the parents of an adult member see, and the alerts at 18 (DEC-26).

DEC-119: the R/S chooses by category,
for all parents alike; until then the parents keep seeing everything; alerts one month
before and on the day, to the member and the parents; members without an account are
shown to the capi on the unit page.
"""

from datetime import date, timedelta

import pytest
from django.core import mail
from django.core.management import call_command
from django.test import Client

from apps.anagrafica.models import VisibilitaGenitori
from apps.core.anno import compie_anni
from apps.permessi import policy
from tests.conftest import nato_anni_fa

pytestmark = pytest.mark.django_db


def _client(persona) -> Client:
    client = Client()
    client.force_login(persona.utente)
    return client


@pytest.fixture
def maggiorenne(ragazza):
    ragazza.data_nascita = nato_anni_fa(19)
    ragazza.save()
    return ragazza


def test_compie_anni_il_29_febbraio():
    assert compie_anni(date(2008, 2, 29), 18) == date(2026, 3, 1)
    assert compie_anni(date(2008, 5, 4), 18) == date(2026, 5, 4)


def test_finche_non_sceglie_i_genitori_vedono_tutto(maggiorenne, genitore):
    assert policy.puo_vedere_dati_sensibili(genitore.utente, maggiorenne)
    assert policy.puo_vedere_sanitarie(genitore.utente, maggiorenne)
    assert policy.puo_vedere_scheda(genitore.utente, maggiorenne)


def test_la_scelta_vale_per_categoria(maggiorenne, genitore, capo):
    url = f"/api/v1/persone/{maggiorenne.pk}/visibilita-genitori"
    risposta = _client(maggiorenne).put(
        url, {"contatti": False, "sanitarie": True, "scheda": False}, "application/json"
    )
    assert risposta.status_code == 200
    assert risposta.json()["genitori"] == ["Mario Genitore"]
    assert risposta.json()["decisa_il"] is not None

    assert not policy.puo_vedere_dati_sensibili(genitore.utente, maggiorenne)
    assert policy.puo_vedere_sanitarie(genitore.utente, maggiorenne)
    dettaglio = _client(genitore).get(f"/api/v1/persone/{maggiorenne.pk}").json()
    assert dettaglio["nome"] == "Giulia"
    assert dettaglio["cellulare"] is None and dettaglio["data_nascita"] is None
    assert dettaglio["unita"] == []
    # The capi still see everything; so does she.
    assert policy.puo_vedere_dati_sensibili(capo.utente, maggiorenne)
    assert policy.puo_vedere_dati_sensibili(maggiorenne.utente, maggiorenne)


def test_per_un_minore_la_scelta_non_conta(ragazza, genitore):
    VisibilitaGenitori.objects.create(persona=ragazza, contatti=False, sanitarie=False)
    assert policy.puo_vedere_dati_sensibili(genitore.utente, ragazza)
    assert policy.puo_vedere_sanitarie(genitore.utente, ragazza)


def test_sceglie_solo_l_interessato_maggiorenne(maggiorenne, ragazza, genitore, capo, estraneo):
    url = f"/api/v1/persone/{maggiorenne.pk}/visibilita-genitori"
    for chi in (genitore, capo, estraneo):
        assert _client(chi).get(url).status_code == 404
    assert _client(maggiorenne).get(url).status_code == 200


def test_minorenne_non_sceglie(ragazza):
    url = f"/api/v1/persone/{ragazza.pk}/visibilita-genitori"
    assert _client(ragazza).get(url).status_code == 404


def test_avvisi_un_mese_prima_e_il_giorno(ragazza, genitore, genitrice_senza_account):
    compleanno = compie_anni(ragazza.data_nascita, 18)

    call_command("avvisa_maggiore_eta", oggi=compleanno - timedelta(days=31))
    assert mail.outbox == []

    call_command("avvisa_maggiore_eta", oggi=compleanno - timedelta(days=30))
    destinatari = sorted(m.to[0] for m in mail.outbox)
    # Her, and each parent apart (the second parent has no account but an email).
    assert destinatari == [
        "genitore@example.invalid",
        "giulia@example.invalid",
        "lucia@example.invalid",
    ]
    assert all(len(m.to) == 1 for m in mail.outbox)
    assert f"/persone/{ragazza.pk}" in next(m for m in mail.outbox if "giulia" in m.to[0]).body

    call_command("avvisa_maggiore_eta", oggi=compleanno - timedelta(days=10))
    assert len(mail.outbox) == 3  # once

    call_command("avvisa_maggiore_eta", oggi=compleanno)
    assert len(mail.outbox) == 6
    a_lei = next(m for m in mail.outbox[3:] if m.to == ["giulia@example.invalid"])
    assert "oggi compi 18 anni" in a_lei.body
    call_command("avvisa_maggiore_eta", oggi=compleanno + timedelta(days=1))
    assert len(mail.outbox) == 6


def test_gia_maggiorenni_non_ricevono_avvisi(maggiorenne, genitore):
    call_command("avvisa_maggiore_eta")
    assert mail.outbox == []


def test_avviso_ai_capi_se_manca_l_account(ragazza, genitore, capo, reparto):
    ragazza.data_nascita = date.today() - timedelta(days=round(18 * 365.25) - 10)
    ragazza.save()
    client = Client()
    client.force_login(capo.utente)
    avvisi = client.get(f"/api/v1/unita/{reparto.pk}").json()["avvisi"]
    assert not any("18 anni" in a for a in avvisi)  # she has an account

    utente = ragazza.utente
    ragazza.utente = None
    ragazza.save()
    utente.delete()
    avvisi = client.get(f"/api/v1/unita/{reparto.pk}").json()["avvisi"]
    assert any("compie 18 anni" in a and "invitalo" in a for a in avvisi)
