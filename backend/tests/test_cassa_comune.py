"""Shared cash of two linked units (DEC-288)."""

from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.test import Client

from apps.cassa import servizi
from apps.cassa.models import Cassa, Movimento, TipoCassa, TipoMovimento
from apps.core.anno import AnnoAssociativo
from apps.organizzazione import servizi as organizzazione
from apps.organizzazione.models import Composizione, Incarico, RuoloIncarico, TipoUnita, Unita
from apps.permessi import policy
from tests.conftest import INIZIO_ANNO, crea_capo
from tests.test_cassa import GENNAIO, _uscita

pytestmark = pytest.mark.django_db


def _client(chi) -> Client:
    client = Client()
    client.force_login(chi.utente)
    return client


@pytest.fixture
def gemello(gruppo, reparto):
    """A second reparto linked to `reparto`, with its own cash and treasurer."""
    unita = Unita.objects.create(
        gruppo=gruppo, nome="Stella", tipo=TipoUnita.REPARTO, composizione=Composizione.FEMMINILE
    )
    organizzazione.collega(reparto, unita)
    return unita


@pytest.fixture
def contanti(reparto):
    return Cassa.objects.create(
        nome="Contanti reparto",
        tipo=TipoCassa.CONTANTI,
        unita=reparto,
        saldo_iniziale=Decimal("50"),
        data_saldo_iniziale=INIZIO_ANNO,
    )


@pytest.fixture
def contanti_gemello(gemello):
    return Cassa.objects.create(
        nome="Contanti Stella",
        tipo=TipoCassa.CONTANTI,
        unita=gemello,
        saldo_iniziale=Decimal("30"),
        data_saldo_iniziale=INIZIO_ANNO,
    )


@pytest.fixture
def tesoriere_gemello(gemello, coca):
    persona = crea_capo("Tea", "Tesoriera", "tea@example.invalid")
    Incarico.objects.create(
        persona=persona, ruolo=RuoloIncarico.TESORIERE_UNITA, unita=gemello, data_inizio=INIZIO_ANNO
    )
    return persona


def test_unire_le_casse(
    capo, reparto, gemello, contanti, contanti_gemello, tesoriere_gemello, ragazza, estraneo
):
    _uscita(contanti_gemello, "10")
    url = f"/api/v1/unita/{reparto.pk}/casse-unite"
    for chi in (ragazza, estraneo, tesoriere_gemello):
        assert _client(chi).post(url).status_code == 403
    # Before: the treasurer of the other unit does not keep this cash.
    assert not policy.puo_registrare_movimenti(tesoriere_gemello.utente, reparto.pk)

    risposta = _client(capo).post(url)  # capo unità of `reparto`
    assert risposta.status_code == 200, risposta.content
    assert risposta.json()["cassa_comune_dal"] == date.today().isoformat()
    gemello.refresh_from_db()
    assert gemello.cassa_comune_dal == date.today()
    contanti_gemello.refresh_from_db()
    assert not contanti_gemello.attiva and contanti_gemello.saldo() == 0
    assert contanti.saldo() == Decimal("70")  # 50 + (30 - 10)
    assert Movimento.objects.filter(tipo=TipoMovimento.GIROCONTO).count() == 1
    # Twice: refused.
    assert _client(capo).post(url).status_code == 400

    # The treasurer of either unit counts for both.
    assert policy.puo_registrare_movimenti(tesoriere_gemello.utente, reparto.pk)
    assert reparto.pk in policy._unita_tesoreria(tesoriere_gemello.utente)
    # The pair's movements together in the cash book of either.
    dati = _client(capo).get(f"/api/v1/movimenti?unita={gemello.pk}&anno=2026").json()
    assert {m["descrizione"] for m in dati} == {"Cancelleria"}
    # The link cannot go while the cash is shared.
    reparto.refresh_from_db()
    with pytest.raises(ValidationError):
        organizzazione.collega(reparto, None)


def test_dividere_solo_a_inizio_anno(
    capo, capogruppo, reparto, gemello, contanti, contanti_gemello
):
    servizi.unisci_casse(reparto, capogruppo.utente, oggi=GENNAIO)
    reparto.refresh_from_db()
    # The year of the union has movements (the transfer): not now.
    assert not servizi.puo_dividere(reparto, oggi=date(2026, 5, 1))
    # Today is in a later year with no movement yet: the capo unità divides them.
    risposta = _client(capo).delete(f"/api/v1/unita/{reparto.pk}/casse-unite")
    assert risposta.status_code == 200, risposta.content
    reparto.refresh_from_db()
    gemello.refresh_from_db()
    assert reparto.cassa_comune_dal is None and gemello.cassa_comune_dal is None
    contanti_gemello.refresh_from_db()
    assert contanti_gemello.attiva
    # Separate again: the link may change.
    organizzazione.collega(reparto, None)


def test_pagamento_in_contanti_va_nella_cassa_comune(capogruppo, reparto, gemello, contanti):
    servizi.unisci_casse(gemello, capogruppo.utente, oggi=GENNAIO)
    # The shared box is of `reparto`: a member of `gemello` pays into it.
    assert servizi.coppia(gemello.pk) == {gemello.pk, reparto.pk}
    assert (
        Cassa.objects.filter(
            attiva=True, tipo=TipoCassa.CONTANTI, unita_id__in=servizi.coppia(gemello.pk)
        ).get()
        == contanti
    )


def test_dividere_con_movimenti_dell_anno_rifiutato(capogruppo, reparto, gemello, contanti):
    servizi.unisci_casse(reparto, capogruppo.utente, oggi=GENNAIO)
    reparto.refresh_from_db()
    anno = AnnoAssociativo.da_data(GENNAIO)
    _uscita(contanti, "5", data=anno.fine)
    assert not servizi.puo_dividere(reparto, oggi=anno.fine)
    with pytest.raises(ValidationError):
        servizi.dividi_casse(reparto, oggi=anno.fine)
