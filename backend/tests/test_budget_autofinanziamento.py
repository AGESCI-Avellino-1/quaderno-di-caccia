"""Fundraising events and camp budgets (DEC-90, DEC-91)."""

from datetime import date, datetime, time
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from django.test import Client

from apps.accounts.models import User
from apps.cassa import servizi as cassa
from apps.cassa.catalogo import catalogo
from apps.cassa.models import Cassa, TipoCassa, TipoMovimento
from apps.eventi import servizi
from apps.eventi.models import Evento, Livello, TipoEvento
from apps.organizzazione.models import Incarico, RuoloIncarico
from apps.quote import servizi as quote
from apps.quote.models import (
    Agevolazione,
    CategoriaQuota,
    Destinatari,
    MetodoPagamento,
    Quota,
    TipoQuota,
)
from tests.conftest import INIZIO_ANNO, crea_capo

pytestmark = pytest.mark.django_db

ROMA = ZoneInfo("Europe/Rome")


def _client(chi) -> Client:
    client = Client()
    client.force_login(chi if isinstance(chi, User) else chi.utente)
    return client


@pytest.fixture
def staff(reparto, coca):
    persona = crea_capo("Elena", "Staff", "staff@example.invalid")
    Incarico.objects.create(
        persona=persona, ruolo=RuoloIncarico.STAFF, unita=reparto, data_inizio=INIZIO_ANNO
    )
    return persona


@pytest.fixture
def contanti(reparto):
    return Cassa.objects.create(
        nome="Contanti reparto",
        tipo=TipoCassa.CONTANTI,
        unita=reparto,
        data_saldo_iniziale=INIZIO_ANNO,
    )


def _evento(reparto, staff, tipo=TipoEvento.CAMPO):
    return servizi.crea(
        Evento(
            titolo="Campo" if tipo == TipoEvento.CAMPO else "Vendita torte",
            tipo=tipo,
            livello=Livello.UNITA,
            inizio=datetime.combine(date(2026, 7, 20), time(9), ROMA),
            fine=datetime.combine(date(2026, 7, 30), time(17), ROMA),
        ),
        [reparto],
        staff.utente,
    )


def test_budget_due_valori_su_tre(reparto, staff, ragazza, csq):
    campo = _evento(reparto, staff)  # two participants
    servizi.fissa_budget(campo, quota=Decimal("150"), contributo=Decimal("100"))
    assert servizi.budget(campo)["totale"] == Decimal("400")
    servizi.fissa_budget(campo, quota=Decimal("150"), totale=Decimal("500"))
    assert servizi.budget(campo)["contributo"] == Decimal("200")
    servizi.fissa_budget(campo, contributo=Decimal("100"), totale=Decimal("401"))
    assert servizi.budget(campo)["quota"] == Decimal("150.50")
    with pytest.raises(Exception, match="due valori su tre"):
        servizi.fissa_budget(campo, quota=Decimal("1"))


def test_autofinanziamento_rendiconto(reparto, staff, contanti, ragazza):
    vendita = _evento(reparto, staff, TipoEvento.AUTOFINANZIAMENTO)
    for tipo, importo, lato in (
        (TipoMovimento.ENTRATA, "300", "E"),
        (TipoMovimento.USCITA, "80", "U"),
    ):
        cassa.registra(
            cassa=contanti,
            tipo=tipo,
            data=date(2026, 3, 1),
            importo=Decimal(importo),
            descrizione="Torte",
            voce_id=catalogo().cerca(lato, "C.2").id,
            evento=vendita,
            utente=staff.utente,
        )
    conti = servizi.rendiconto(vendita)
    assert (conti["entrate"], conti["uscite"], conti["saldo"]) == (
        Decimal("300"),
        Decimal("80"),
        Decimal("220"),
    )
    sbagliata = vendita.movimenti.get(tipo=TipoMovimento.USCITA)
    cassa.storna(sbagliata, staff.utente, "Errore")
    assert servizi.rendiconto(vendita)["uscite"] == Decimal("0")


def test_quote_del_campo_entrano_nel_suo_rendiconto(reparto, staff, contanti, ragazza, capogruppo):
    campo = _evento(reparto, staff)
    tipo = TipoQuota.objects.create(
        nome="Campo",
        categoria=CategoriaQuota.EVENTO,
        anno=2026,
        importo=Decimal("150"),
        destinatari=Destinatari.TUTTI,
        evento=campo,
        rate=[{"descrizione": "", "importo": "150", "scadenza": "2026-07-01"}],
    )
    quote.emetti_evento(tipo)
    sua = Quota.objects.get(persona=ragazza)
    Agevolazione.objects.create(quota=sua, importo=Decimal("50"), decisa_il=date(2026, 5, 1))
    quote.registra_pagamento(
        data=date(2026, 6, 1),
        metodo=MetodoPagamento.CONTANTI,
        versato_da="Mario",
        righe=[quote.Riga(sua, Decimal("100"))],
        utente=staff.utente,
    )
    conti = servizi.rendiconto(campo)
    assert conti["entrate"] == Decimal("100")  # the payment, linked by itself
    assert conti["quote_incassate"] == Decimal("100")
    assert conti["agevolazioni"] == Decimal("50")


def test_budget_con_lo_staff(reparto, staff, capo, ragazza, csq):
    campo = _evento(reparto, staff)  # 2 ragazzi; staff: Elena and the capo unità
    assert servizi.staff_al_campo(campo) == 2
    servizi.fissa_budget(
        campo, quota=Decimal("150"), contributo=Decimal("100"), quota_staff=Decimal("50")
    )
    assert servizi.budget(campo)["totale"] == Decimal("500")  # 150×2 + 50×2 + 100
    servizi.fissa_budget(
        campo, contributo=Decimal("100"), totale=Decimal("500"), quota_staff=Decimal("0")
    )
    assert servizi.budget(campo)["quota"] == Decimal("200")


def test_api_rendiconto_e_budget(reparto, staff, ragazza, genitore, capo):
    campo = _evento(reparto, staff)
    url = f"/api/v1/eventi/{campo.pk}"
    assert _client(genitore).get(f"{url}/rendiconto").status_code == 403
    assert _client(capo).get(f"{url}/rendiconto").json()["budget"] is None
    corpo = {"quota": "150", "contributo": "100"}
    assert (
        _client(genitore).put(f"{url}/budget", corpo, content_type="application/json").status_code
        == 403
    )
    risposta = _client(staff).put(f"{url}/budget", corpo, content_type="application/json")
    assert risposta.json()["budget"]["calcolato"] == "totale"


def test_api_movimento_collegato_a_un_evento(reparto, staff, contanti, capo):
    vendita = _evento(reparto, staff, TipoEvento.AUTOFINANZIAMENTO)
    corpo = {
        "cassa_id": contanti.pk,
        "tipo": "ENTRATA",
        "data": "2026-03-01",
        "importo": "120.00",
        "descrizione": "Vendita torte",
        "voce_id": catalogo().cerca("E", "C.2").id,
        "evento_id": vendita.pk,
    }
    risposta = _client(capo).post("/api/v1/movimenti", corpo, content_type="application/json")
    assert risposta.status_code == 201, risposta.content
    assert risposta.json()["evento"] == "Vendita torte"
