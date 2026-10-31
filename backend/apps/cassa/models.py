"""Cash book by cash box (DEC-85…DEC-88).

- one bank account for the group, every movement says which unit it belongs to (the
  units' debit cards included); a cash box for each unit's cash (DEC-150);
- fee payments enter by themselves (cash in the member's unit box, transfers in the
  bank); cancelling a payment reverses its movements (DEC-152);
- a movement is never edited: a mistake is reversed (storno) with a reason, and a
  new one recorded; records made offline never conflict (DEC-96, DEC-153);
- an initial balance per box, then cash checks: a difference becomes an adjustment
  (DEC-154);
- a capo records an expense paid out of pocket, which becomes an outflow when the
  treasurer refunds it (DEC-86, DEC-155);
- the receipt photo is optional; outflows without it are flagged (DEC-155).
"""

from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, Sum

from apps.core.models import ModelloTracciato

ZERO = Decimal("0.00")


def _euro(**campi) -> models.DecimalField:
    return models.DecimalField(max_digits=10, decimal_places=2, **campi)


class TipoCassa(models.TextChoices):
    BANCA = "BANCA", "Conto bancario"
    CONTANTI = "CONTANTI", "Contanti"
    # The group's PayPal account (DEC-254): like the bank account, of the whole group;
    # its transfers to the bank are giroconti.
    PAYPAL = "PAYPAL", "Conto PayPal"


# Accounts of the whole group: no unit on the box, the unit is on each movement.
CASSE_DI_GRUPPO = (TipoCassa.BANCA, TipoCassa.PAYPAL)


class Cassa(ModelloTracciato):
    nome = models.CharField(max_length=120)
    tipo = models.CharField(max_length=10, choices=TipoCassa.choices)
    # Cash belongs to a unit (or to the group when empty); the bank account is shared.
    unita = models.ForeignKey(
        "organizzazione.Unita",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="casse",
    )
    saldo_iniziale = _euro(default=ZERO)
    data_saldo_iniziale = models.DateField()
    attiva = models.BooleanField(default=True)

    class Meta:
        verbose_name = "cassa"
        verbose_name_plural = "casse"
        ordering = ["tipo", "nome"]

    def __str__(self) -> str:
        return self.nome

    def clean(self) -> None:
        if self.tipo in CASSE_DI_GRUPPO and self.unita_id:
            raise ValidationError(
                f"Il {self.get_tipo_display().lower()} è del gruppo: le unità si indicano sui "
                "movimenti."
            )

    def saldo(self, al_giorno=None) -> Decimal:
        """Initial balance plus every movement from its date on (outflows, transfers out
        and reversals carry their sign in `effetto`)."""
        movimenti = Movimento.objects.filter(data__gte=self.data_saldo_iniziale)
        if al_giorno is not None:
            movimenti = movimenti.filter(data__lte=al_giorno)
        entrate = movimenti.filter(cassa=self).aggregate(t=Sum("effetto"))["t"] or ZERO
        giroconti = (
            movimenti.filter(cassa_destinazione=self).aggregate(t=Sum("importo"))["t"] or ZERO
        )
        return self.saldo_iniziale + entrate + giroconti


class TipoMovimento(models.TextChoices):
    ENTRATA = "ENTRATA", "Entrata"
    USCITA = "USCITA", "Uscita"
    GIROCONTO = "GIROCONTO", "Giroconto"  # DEC-88: neither income nor expense
    RETTIFICA = "RETTIFICA", "Rettifica dopo verifica di cassa"


class Movimento(ModelloTracciato):
    """One line of the cash book. Never edited: reversed by a movement with
    `storno_di` and the opposite amount."""

    cassa = models.ForeignKey(Cassa, on_delete=models.PROTECT, related_name="movimenti")
    data = models.DateField()
    tipo = models.CharField(max_length=10, choices=TipoMovimento.choices)
    # Positive for a movement, negative for its reversal and for a cash shortfall.
    importo = _euro()
    # The change on `cassa`: +importo for an income, −importo for an outflow or a
    # transfer out. Stored so balances are one SUM.
    effetto = _euro(editable=False)
    descrizione = models.CharField(max_length=300)
    # Modello D category (DEC-87), copied: the catalog may change in later years.
    voce_id = models.CharField(max_length=20, blank=True)
    voce_riga = models.CharField(max_length=6, blank=True)
    voce_nome = models.CharField(max_length=300, blank=True)
    unita = models.ForeignKey(
        "organizzazione.Unita",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="movimenti",
    )
    cassa_destinazione = models.ForeignKey(
        Cassa, null=True, blank=True, on_delete=models.PROTECT, related_name="giroconti_ricevuti"
    )
    giustificativo = models.FileField(upload_to="giustificativi/%Y/", blank=True)
    storno_di = models.OneToOneField(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="storno"
    )
    motivo_storno = models.CharField(max_length=300, blank=True)
    # The event it belongs to: a fundraising's income and costs (DEC-90), a camp's
    # expenses and fees (DEC-91).
    evento = models.ForeignKey(
        "eventi.Evento",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="movimenti",
    )
    pagamento = models.ForeignKey(
        "quote.Pagamento",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="movimenti",
    )
    registrato_da = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        verbose_name = "movimento"
        verbose_name_plural = "movimenti"
        ordering = ["-data", "-pk"]
        constraints = [
            models.CheckConstraint(
                condition=~Q(cassa=models.F("cassa_destinazione")), name="giroconto_tra_casse"
            )
        ]

    def __str__(self) -> str:
        return f"{self.get_tipo_display()} {self.importo} € — {self.descrizione}"

    def save(self, *args, **kwargs) -> None:
        segno = 1 if self.tipo in (TipoMovimento.ENTRATA, TipoMovimento.RETTIFICA) else -1
        self.effetto = segno * self.importo
        super().save(*args, **kwargs)

    def clean(self) -> None:
        errori = []
        if self.importo == 0:
            errori.append("L'importo non può essere zero.")
        storno = self.storno_di_id is not None
        if (
            self.importo is not None
            and self.importo < 0
            and not storno
            and self.tipo != TipoMovimento.RETTIFICA
        ):
            errori.append("L'importo deve essere positivo.")
        if self.tipo == TipoMovimento.GIROCONTO:
            if self.cassa_destinazione_id is None:
                errori.append("Indica la cassa che riceve il giroconto.")
        elif self.cassa_destinazione_id is not None:
            errori.append("Solo un giroconto ha una cassa che lo riceve.")
        if self.tipo in (TipoMovimento.ENTRATA, TipoMovimento.USCITA) and not self.voce_id:
            errori.append("Scegli la voce del Modello D.")
        if errori:
            raise ValidationError(errori)

    @property
    def senza_giustificativo(self) -> bool:
        """An outflow without the receipt photo: allowed, flagged."""
        return (
            self.tipo == TipoMovimento.USCITA
            and self.storno_di_id is None
            and not self.giustificativo
        )


class VerificaCassa(ModelloTracciato):
    """The cash counted by the treasurer or the capo unità, who have the last word on
    the balance (DEC-11). A difference is recorded as an adjustment."""

    cassa = models.ForeignKey(Cassa, on_delete=models.PROTECT, related_name="verifiche")
    data = models.DateField()
    saldo_contato = _euro()
    saldo_app = _euro()
    motivo = models.CharField(max_length=300, blank=True)
    rettifica = models.OneToOneField(
        Movimento, null=True, blank=True, on_delete=models.PROTECT, related_name="verifica"
    )
    registrata_da = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        verbose_name = "verifica di cassa"
        verbose_name_plural = "verifiche di cassa"
        ordering = ["-data", "-pk"]

    def __str__(self) -> str:
        return f"Verifica di {self.cassa} del {self.data}"

    @property
    def differenza(self) -> Decimal:
        return self.saldo_contato - self.saldo_app


class SpesaAnticipata(ModelloTracciato):
    """An expense a capo paid out of pocket (DEC-86). It touches no cash box until it is
    refunded: then it becomes an outflow under "Rimborsi spese volontari"."""

    capo = models.ForeignKey(
        "anagrafica.Persona", on_delete=models.PROTECT, related_name="spese_anticipate"
    )
    data = models.DateField()
    importo = _euro()
    descrizione = models.CharField(max_length=300)
    unita = models.ForeignKey(
        "organizzazione.Unita", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    giustificativo = models.FileField(upload_to="giustificativi/%Y/", blank=True)
    registrata_da = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    rimborso = models.OneToOneField(
        Movimento, null=True, blank=True, on_delete=models.PROTECT, related_name="spesa_anticipata"
    )
    respinta_il = models.DateTimeField(null=True, blank=True)
    motivo_rifiuto = models.CharField(max_length=300, blank=True)

    class Meta:
        verbose_name = "spesa anticipata"
        verbose_name_plural = "spese anticipate"
        ordering = ["-data", "-pk"]

    def __str__(self) -> str:
        return f"Spesa di {self.importo} € anticipata da {self.capo}"
