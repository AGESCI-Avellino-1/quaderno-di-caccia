"""The bank statement (DEC-93, DEC-221…DEC-224).

The capigruppo and the group treasurer load the movements exported from the bank; each
line of the bank becomes, once confirmed, one or more movements of the cash book on the
bank account: linked to a movement already recorded by hand, a fee payment (with its
receipt), a new income or outflow, or a transfer to a unit's cash. Nothing enters the
cash book without a confirmation. The unit of a card is recognised by the last digits
of the card written in the bank's text.

The bank's text of a line holds personal data (who paid, the reason): it is kept for
matching, never logged, and stays out of the audit log. It is an accounting record of
the group: archiving or erasing a person leaves it (DEC-226).
"""

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models

from apps.cassa.models import Cassa, Movimento
from apps.core.models import ModelloTracciato
from apps.organizzazione.models import Unita


def _euro(**campi):
    return models.DecimalField(max_digits=10, decimal_places=2, **campi)


class CartaUnita(ModelloTracciato):
    """The debit card of a unit on the group's account (DEC-85, DEC-224)."""

    unita = models.ForeignKey(Unita, on_delete=models.CASCADE, related_name="carte")
    ultime_cifre = models.CharField(
        max_length=4,
        unique=True,
        validators=[RegexValidator(r"^\d{4}$", "Le ultime quattro cifre della carta.")],
    )

    class Meta:
        verbose_name = "carta di unità"
        verbose_name_plural = "carte di unità"
        ordering = ["unita__tipo", "unita__nome"]

    def __str__(self) -> str:
        return f"Carta {self.ultime_cifre} ({self.unita})"


class EstrattoConto(ModelloTracciato):
    """One file loaded: its balances check that nothing is missing."""

    cassa = models.ForeignKey(Cassa, on_delete=models.PROTECT, related_name="estratti")
    data_iniziale = models.DateField(null=True, blank=True)
    saldo_iniziale = _euro()
    data_finale = models.DateField(null=True, blank=True)
    saldo_finale = _euro()
    righe_nuove = models.PositiveIntegerField(default=0)
    righe_gia_presenti = models.PositiveIntegerField(default=0)
    caricato_da = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        verbose_name = "estratto conto"
        verbose_name_plural = "estratti conto"
        ordering = ["-creato_il"]

    def __str__(self) -> str:
        return f"Estratto conto del {self.creato_il:%d/%m/%Y}"


class RigaBanca(ModelloTracciato):
    estratto = models.ForeignKey(EstrattoConto, on_delete=models.PROTECT, related_name="righe")
    cassa = models.ForeignKey(Cassa, on_delete=models.PROTECT, related_name="righe_banca")
    data = models.DateField()  # data contabile
    data_valuta = models.DateField(null=True, blank=True)
    # The bank's type of operation ("ACCREDITO BEU CON CONTABILE", "PAGAMENTO POS"…).
    operazione = models.CharField(max_length=200)
    # The bank's long text: personal data, see the module docstring.
    dettaglio = models.TextField(blank=True)
    # Positive for money in, negative for money out.
    importo = _euro()
    # Date, amount and long text (which carries the bank's code of the operation):
    # a line loaded twice is recognised.
    impronta = models.CharField(max_length=64, unique=True)
    movimenti = models.ManyToManyField(Movimento, blank=True, related_name="righe_banca")
    confermata_il = models.DateTimeField(null=True, blank=True)
    confermata_da = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        verbose_name = "riga dell'estratto conto"
        verbose_name_plural = "righe dell'estratto conto"
        ordering = ["-data", "-pk"]

    def __str__(self) -> str:
        return f"{self.data:%d/%m/%Y} {self.operazione} {self.importo}"
