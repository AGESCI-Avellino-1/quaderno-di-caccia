"""Optional emails: who chose not to receive a kind does not get it (GDPR art. 21)."""

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from django.core import mail
from django.core.management import call_command
from django.test import Client

from apps.anagrafica.models import PreferenzeEmail
from apps.eventi import avvisi, servizi
from apps.eventi.models import Evento, Livello, TipoEvento
from apps.quote import servizi as quote
from apps.quote.models import CategoriaQuota, Destinatari, MetodoPagamento, Quota, TipoQuota

pytestmark = pytest.mark.django_db

ROMA = ZoneInfo("Europe/Rome")


def _uscita(reparto):
    giorno = date.today() + timedelta(days=20)
    return servizi.crea(
        Evento(
            titolo="Uscita",
            tipo=TipoEvento.USCITA,
            livello=Livello.UNITA,
            inizio=datetime.combine(giorno, time(9), ROMA),
            fine=datetime.combine(giorno, time(17), ROMA),
        ),
        [reparto],
        None,
    )


def test_api_preferenze(genitore, estraneo):
    client = Client()
    client.force_login(genitore.utente)
    assert client.get("/api/v1/io/email").json() == {
        "eventi": True,
        "promemoria_quote": True,
        "maggiore_eta": True,
        "riepiloghi": True,
        "avvisi": True,
    }
    risposta = client.put(
        "/api/v1/io/email",
        {"eventi": False, "promemoria_quote": True, "maggiore_eta": True, "riepiloghi": True},
        content_type="application/json",
    )
    assert risposta.json()["eventi"] is False
    assert PreferenzeEmail.objects.get(persona=genitore).eventi is False


def test_niente_email_di_eventi_a_chi_non_le_vuole(
    reparto, ragazza, genitore, genitrice_senza_account
):
    evento = _uscita(reparto)
    PreferenzeEmail.objects.create(persona=genitore, eventi=False)
    assert avvisi.nuovo(evento) == 1
    assert mail.outbox[0].to == ["lucia@example.invalid"]
    assert "/email" in mail.outbox[0].body  # how to choose


def test_promemoria_quote_e_ricevute(reparto, ragazza, genitore):
    tipo = TipoQuota.objects.create(
        nome="Quota",
        categoria=CategoriaQuota.GRUPPO,
        anno=2026,
        importo=Decimal("40"),
        destinatari=Destinatari.TUTTI,
        scadenza=date(2025, 11, 30),
    )
    oggi = date.today()
    q = Quota.objects.create(
        tipo=tipo,
        persona=ragazza,
        periodo=oggi,
        scadenza=oggi + timedelta(days=3),
        importo=Decimal("40"),
    )
    PreferenzeEmail.objects.create(persona=genitore, promemoria_quote=False)
    call_command("promemoria_quote")
    assert mail.outbox == []
    # Receipts are always sent.
    pagamento = quote.registra_pagamento(
        data=oggi,
        metodo=MetodoPagamento.CONTANTI,
        versato_da="Mario",
        righe=[quote.Riga(q, Decimal("40"))],
        utente=None,
    )
    assert quote.destinatari_ricevuta(pagamento) == ["genitore@example.invalid"]


def test_riepilogo_correzioni_ai_capigruppo(capogruppo, ragazza, genitore):
    from apps.anagrafica.servizi import correggi_campo

    PreferenzeEmail.objects.create(persona=capogruppo, riepiloghi=False)
    correggi_campo(ragazza, "cellulare", "3331111111", genitore.utente)
    call_command("segnala_correzioni")
    assert mail.outbox == []
