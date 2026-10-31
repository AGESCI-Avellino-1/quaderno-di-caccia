"""Payments the family reports (DEC-255) and their check by a capo.

The family pays outside the app (PayPal, bank transfer) and reports it: its fees are
"in verifica". Who may record payments for that member checks it, from the proof or
from the PayPal or bank statement, and confirms it (the payment is recorded with its
receipt, PayPal's extra goes to the cash book as "Quota PayPal", DEC-254) or refuses it
with a reason the family receives. The proof is deleted at the check (as DEC-200).
"""

from datetime import date
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from apps.cassa.catalogo import QUOTA_PAYPAL, TRATTENUTA_PAYPAL
from apps.core.euro import euro
from apps.impostazioni.email import invia
from apps.organizzazione.models import Gruppo

from . import servizi
from .models import (
    METODI_SEGNALABILI,
    MetodoPagamento,
    Quota,
    SegnalazionePagamento,
    StatoSegnalazione,
)
from .modi_pagamento import maggiorazione_paypal

ZERO = Decimal("0.00")


def in_verifica(quote) -> set[int]:
    """The fees of `quote` reported and waiting for the check."""
    return set(
        Quota.objects.filter(
            pk__in=[q.pk for q in quote],
            segnalazioni__stato=StatoSegnalazione.IN_VERIFICA,
        ).values_list("pk", flat=True)
    )


@transaction.atomic
def segnala(utente, metodo: str, quote: list[Quota], data: date) -> SegnalazionePagamento:
    if metodo not in METODI_SEGNALABILI:
        raise ValidationError("Si segnalano solo i pagamenti con PayPal o con bonifico.")
    dovute = [q for q in quote if q.annullata_il is None and q.residuo > 0]
    if not dovute:
        raise ValidationError("Non c'è niente da pagare su queste quote.")
    if in_verifica(dovute):
        raise ValidationError("Una di queste quote ha già un pagamento in verifica.")
    if data > timezone.localdate():
        raise ValidationError("La data del pagamento non può essere nel futuro.")
    importo = sum((q.residuo for q in dovute), ZERO)
    maggiorazione = ZERO
    gruppo = Gruppo.objects.first()
    if metodo == MetodoPagamento.PAYPAL and gruppo is not None:
        maggiorazione = maggiorazione_paypal(gruppo, importo)
    segnalazione = SegnalazionePagamento.objects.create(
        metodo=metodo,
        importo=importo,
        maggiorazione=maggiorazione,
        data=data,
        segnalata_da=utente,
    )
    segnalazione.quote.set(dovute)
    return segnalazione


def _aperta(segnalazione: SegnalazionePagamento) -> None:
    if segnalazione.stato != StatoSegnalazione.IN_VERIFICA:
        raise ValidationError("Il pagamento è già stato verificato.")


def carica_ricevuta(segnalazione: SegnalazionePagamento, contenuto: bytes, tipo: str) -> None:
    import secrets

    _aperta(segnalazione)
    estensione = {"application/pdf": "pdf", "image/jpeg": "jpg", "image/png": "png"}[tipo]
    if segnalazione.ricevuta:
        segnalazione.ricevuta.delete(save=False)
    segnalazione.ricevuta.save(
        f"{secrets.token_hex(16)}.{estensione}", ContentFile(contenuto), save=False
    )
    segnalazione.ricevuta_tipo = tipo
    segnalazione.save(update_fields=["ricevuta", "ricevuta_tipo", "aggiornato_il"])


def _togli_ricevuta(segnalazione: SegnalazionePagamento) -> None:
    if segnalazione.ricevuta:
        segnalazione.ricevuta.delete(save=False)
    segnalazione.ricevuta = ""
    segnalazione.ricevuta_tipo = ""


@transaction.atomic
def annulla(segnalazione: SegnalazionePagamento) -> None:
    _aperta(segnalazione)
    _togli_ricevuta(segnalazione)
    segnalazione.stato = StatoSegnalazione.ANNULLATA
    segnalazione.save()


def _nome(utente) -> str:
    from apps.permessi.policy import persona_di

    persona = persona_di(utente)
    return f"{persona.nome} {persona.cognome}" if persona else utente.email


@transaction.atomic
def conferma(
    segnalazione: SegnalazionePagamento,
    utente,
    *,
    data: date | None = None,
    accreditato: Decimal | None = None,
):
    """The payment, with its receipt; for PayPal the extra as "Quota PayPal" and, when
    the amount PayPal credited is given, the difference as "Trattenuta PayPal"
    (DEC-254). Fees already paid meanwhile are left out."""
    from apps.cassa.models import TipoMovimento
    from apps.cassa.servizi import registra

    _aperta(segnalazione)
    righe = [
        servizi.Riga(q, q.residuo)
        for q in segnalazione.quote.select_related("tipo", "persona")
        if q.annullata_il is None and q.residuo > 0
    ]
    if not righe:
        raise ValidationError("Queste quote risultano già pagate: rifiuta la segnalazione.")
    pagamento = servizi.registra_pagamento(
        data=data or segnalazione.data,
        metodo=MetodoPagamento(segnalazione.metodo),
        versato_da=_nome(segnalazione.segnalata_da),
        righe=righe,
        utente=utente,
    )
    movimento = pagamento.movimenti.first()
    if segnalazione.metodo == MetodoPagamento.PAYPAL and movimento is not None:
        quota_paypal = segnalazione.maggiorazione
        trattenuta = ZERO
        if accreditato is not None:
            differenza = pagamento.importo + segnalazione.maggiorazione - accreditato
            if differenza > 0:
                trattenuta = differenza
            else:
                quota_paypal -= differenza  # PayPal credited more: it is income too
        comuni = {
            "cassa": movimento.cassa,
            "data": pagamento.data,
            "utente": utente,
            "pagamento": pagamento,
        }
        if quota_paypal > 0:
            registra(
                tipo=TipoMovimento.ENTRATA,
                importo=quota_paypal,
                descrizione=f"Quota PayPal, ricevuta n. {pagamento.numero}",
                voce_id=QUOTA_PAYPAL,
                **comuni,
            )
        if trattenuta > 0:
            registra(
                tipo=TipoMovimento.USCITA,
                importo=trattenuta,
                descrizione=f"Trattenuta PayPal, ricevuta n. {pagamento.numero}",
                voce_id=TRATTENUTA_PAYPAL,
                **comuni,
            )
    _togli_ricevuta(segnalazione)
    segnalazione.stato = StatoSegnalazione.CONFERMATA
    segnalazione.pagamento = pagamento
    segnalazione.verificata_da = utente
    segnalazione.verificata_il = timezone.now()
    segnalazione.save()
    transaction.on_commit(lambda: servizi.invia_ricevuta(pagamento))
    return pagamento


@transaction.atomic
def rifiuta(segnalazione: SegnalazionePagamento, utente, motivo: str) -> None:
    _aperta(segnalazione)
    if not motivo.strip():
        raise ValidationError("Scrivi il motivo: lo legge chi ha segnalato il pagamento.")
    _togli_ricevuta(segnalazione)
    segnalazione.stato = StatoSegnalazione.RIFIUTATA
    segnalazione.motivo_rifiuto = motivo.strip()
    segnalazione.verificata_da = utente
    segnalazione.verificata_il = timezone.now()
    segnalazione.save()
    valori = {
        "Importo": euro(segnalazione.importo + segnalazione.maggiorazione),
        "Data": segnalazione.data.strftime("%d/%m/%Y"),
        "Motivo": segnalazione.motivo_rifiuto,
        "Link": f"{settings.FRONTEND_URL}/mie-quote",
    }
    indirizzo = segnalazione.segnalata_da.email
    transaction.on_commit(lambda: invia("pagamento_non_confermato", valori, [indirizzo]))
